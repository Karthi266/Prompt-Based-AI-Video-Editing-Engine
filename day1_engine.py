
import os
import re
import subprocess
from typing import Literal, Optional

import ffmpeg
from pydantic import BaseModel, Field


# ============================================================
# 1. VIDEO EDIT PLAN SCHEMAS
# ============================================================

class TrimOperation(BaseModel):
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., gt=0)


class SpeedOperation(BaseModel):
    factor: float = Field(..., gt=0)


class VolumeOperation(BaseModel):
    level: float = Field(..., ge=0)
    fade_in: float = Field(default=0.0, ge=0)
    fade_out: float = Field(default=0.0, ge=0)


class CropOperation(BaseModel):
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:5"]


class AddTextOverlay(BaseModel):
    text: str
    position: Literal["top", "center", "bottom"] = "bottom"


class ColorGradingOperation(BaseModel):
    brightness: float = Field(default=0.0, ge=-1.0, le=1.0)
    contrast: float = Field(default=1.0, ge=0.0, le=2.0)
    saturation: float = Field(default=1.0, ge=0.0, le=3.0)


class FadeEffectOperation(BaseModel):
    fade_in_sec: float = Field(default=0.0, ge=0)
    fade_out_sec: float = Field(default=0.0, ge=0)


class VideoEditPlan(BaseModel):
    summary: str
    trim: Optional[TrimOperation] = None
    speed: Optional[SpeedOperation] = None
    volume: Optional[VolumeOperation] = None
    crop: Optional[CropOperation] = None
    text_overlay: Optional[AddTextOverlay] = None
    color_grading: Optional[ColorGradingOperation] = None
    fade_effects: Optional[FadeEffectOperation] = None


# ============================================================
# 2. GEMINI INTENT PARSER
# ============================================================

class IntentParser:
    def __init__(self, provider: Literal["gemini"] = "gemini"):
        if provider != "gemini":
            raise ValueError("Only the Gemini provider is implemented.")

        from google import genai

        self.client = genai.Client()
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    @staticmethod
    def _detect_first_n_seconds(prompt: str):
        """
        Interpret requests such as:
        - Trim the first 5 seconds.
        - Keep only the first 5 seconds.
        - Use the first 5 seconds of the video.

        These mean keep the interval from 0 to N seconds.
        """
        patterns = [
            r"\b(?:trim|keep|retain|save|use|cut)"
            r"\s+(?:only\s+)?(?:the\s+)?first\s+"
            r"(\d+(?:\.\d+)?)\s*(?:seconds?|secs?)\b",

            r"\bfirst\s+(\d+(?:\.\d+)?)\s*"
            r"(?:seconds?|secs?)\s+of\s+the\s+video\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None

    def parse_prompt(
        self, user_prompt: str, video_duration: float
    ) -> VideoEditPlan:
        from google.genai import types

        if not user_prompt.strip():
            raise ValueError("Please enter a video-editing prompt.")

        if video_duration <= 0:
            raise ValueError("Video duration must be greater than zero.")

        instructions = f"""
You are an expert video-editing assistant.

Convert the user's request into a JSON object matching this schema:
{VideoEditPlan.model_json_schema()}

Source video duration: {video_duration:.6f} seconds.

Rules:
- Return only a valid JSON object.
- Include the required summary field.
- Set operations not requested by the user to null.
- Do not invent file paths or unsupported operations.
- All trim times must be within the source video duration.
- Trim end_time must be greater than start_time.
- For "trim the first N seconds", use start_time=0 and end_time=N.
- For "keep the first N seconds", use start_time=0 and end_time=N.
- Do not use the full video duration as the trim end unless requested.
- Speed factor must be greater than zero.
- Use only supported crop ratios and text positions.
- Use volume level 1.0 for unchanged volume.
- Use speed factor 1.0 for unchanged speed.
- Do not add edits that the user did not request.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=(
                f"{instructions}\n\n"
                f"User editing request:\n{user_prompt}"
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        plan = VideoEditPlan.model_validate_json(response.text)

        # Deterministic handling for "first N seconds" requests.
        # This prevents Gemini from accidentally choosing the
        # entire video duration as the trim endpoint.
        first_n = self._detect_first_n_seconds(user_prompt)

        if first_n is not None:
            if first_n <= 0:
                raise ValueError("Trim duration must be greater than zero.")

            if first_n > video_duration + 0.05:
                raise ValueError(
                    f"You requested the first {first_n:g} seconds, "
                    f"but the video is only {video_duration:.2f} seconds."
                )

            first_n = min(first_n, video_duration)

            plan = plan.model_copy(
                update={
                    "trim": TrimOperation(
                        start_time=0.0,
                        end_time=first_n,
                    )
                }
            )

        # Normalize small floating-point duration differences.
        if plan.trim:
            start = plan.trim.start_time
            end = plan.trim.end_time

            if start >= video_duration:
                raise ValueError(
                    "Trim start must be shorter than the video duration."
                )

            if end <= start:
                raise ValueError(
                    "Trim end must be greater than trim start."
                )

            # For example, 10.0100001 vs 10.0099999.
            # Accept tiny probe/rounding differences safely.
            if end > video_duration:
                if end - video_duration <= 0.05:
                    plan = plan.model_copy(
                        update={
                            "trim": TrimOperation(
                                start_time=start,
                                end_time=video_duration,
                            )
                        }
                    )
                else:
                    raise ValueError(
                        f"Trim end ({end:.6f}s) exceeds "
                        f"video duration ({video_duration:.6f}s)."
                    )

        return plan


# ============================================================
# 3. FFMPEG VIDEO EDITING ENGINE
# ============================================================

class FFmpegVideoEngine:
    def __init__(self, input_path: str):
        if not os.path.isfile(input_path):
            raise FileNotFoundError(
                f"Input video file not found: {input_path}"
            )

        self.input_path = input_path

    def get_video_duration(self) -> float:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.input_path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Could not read video duration: {result.stderr}"
            )

        try:
            duration = float(result.stdout.strip())
        except ValueError as exc:
            raise RuntimeError(
                "Could not determine the video duration."
            ) from exc

        if duration <= 0:
            raise ValueError("The input video has an invalid duration.")

        return duration

    def _has_audio(self) -> bool:
        probe = ffmpeg.probe(self.input_path)
        return any(
            item.get("codec_type") == "audio"
            for item in probe.get("streams", [])
        )

    @staticmethod
    def _apply_speed_to_audio(audio, factor: float):
        """Apply a positive speed factor using valid atempo stages."""
        remaining = factor

        while remaining > 2.0:
            audio = audio.filter("atempo", 2.0)
            remaining /= 2.0

        while remaining < 0.5:
            audio = audio.filter("atempo", 0.5)
            remaining /= 0.5

        if abs(remaining - 1.0) > 0.000001:
            audio = audio.filter("atempo", remaining)

        return audio

    @staticmethod
    def _escape_drawtext(text: str) -> str:
        """Escape common FFmpeg drawtext special characters."""
        replacements = {
            "\\": "\\\\",
            "'": "\\'",
            ":": "\\:",
            "%": "\\%",
            ",": "\\,",
            "[": "\\[",
            "]": "\\]",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def execute_plan(
        self, plan: VideoEditPlan, output_path: str
    ) -> str:
        has_audio = self._has_audio()
        source_duration = self.get_video_duration()

        if plan.volume and not has_audio:
            raise ValueError(
                "This video has no audio track, so volume and audio "
                "fade operations cannot be applied."
            )

        # ----------------------------------------------------
        # 1. TRIM VALIDATION
        # ----------------------------------------------------
        if plan.trim:
            start = plan.trim.start_time
            end = plan.trim.end_time

            if start >= source_duration:
                raise ValueError(
                    "Trim start must be shorter than video duration."
                )

            if end > source_duration:
                if end - source_duration <= 0.05:
                    end = source_duration
                else:
                    raise ValueError(
                        f"Trim end ({end:.6f}s) exceeds video "
                        f"duration ({source_duration:.6f}s)."
                    )

            if end <= start:
                raise ValueError(
                    "Trim end must be greater than trim start."
                )

            effective_duration = end - start
        else:
            start = 0.0
            end = source_duration
            effective_duration = source_duration

        speed_factor = plan.speed.factor if plan.speed else 1.0

        if speed_factor <= 0:
            raise ValueError("Speed factor must be greater than zero.")

        output_duration = effective_duration / speed_factor

        # ----------------------------------------------------
        # 2. FADE VALIDATION
        # ----------------------------------------------------
        if plan.fade_effects:
            fades = plan.fade_effects

            if fades.fade_in_sec > output_duration:
                raise ValueError(
                    "Video fade-in cannot exceed output duration."
                )

            if fades.fade_out_sec > output_duration:
                raise ValueError(
                    "Video fade-out cannot exceed output duration."
                )

        if plan.volume:
            if plan.volume.fade_in > output_duration:
                raise ValueError(
                    "Audio fade-in cannot exceed output duration."
                )

            if plan.volume.fade_out > output_duration:
                raise ValueError(
                    "Audio fade-out cannot exceed output duration."
                )

        # ----------------------------------------------------
        # 3. OPEN INPUT STREAMS
        # ----------------------------------------------------
        stream = ffmpeg.input(self.input_path)
        video = stream.video
        audio = stream.audio if has_audio else None

        # ----------------------------------------------------
        # 4. TRIM
        # ----------------------------------------------------
        if plan.trim:
            video = (
                video
                .trim(start=start, end=end)
                .filter("setpts", "PTS-STARTPTS")
            )

            if audio is not None:
                audio = (
                    audio
                    .filter("atrim", start=start, end=end)
                    .filter("asetpts", "PTS-STARTPTS")
                )

        # ----------------------------------------------------
        # 5. SPEED
        # ----------------------------------------------------
        if abs(speed_factor - 1.0) > 0.000001:
            video = video.filter(
                "setpts", f"PTS/{speed_factor}"
            )

            if audio is not None:
                audio = self._apply_speed_to_audio(
                    audio, speed_factor
                )

        # ----------------------------------------------------
        # 6. VOLUME AND AUDIO FADES
        # ----------------------------------------------------
        if plan.volume and audio is not None:
            volume = plan.volume
            audio = audio.filter("volume", volume.level)

            if volume.fade_in > 0:
                audio = audio.filter(
                    "afade",
                    type="in",
                    start_time=0,
                    duration=volume.fade_in,
                )

            if volume.fade_out > 0:
                audio = audio.filter(
                    "afade",
                    type="out",
                    start_time=output_duration - volume.fade_out,
                    duration=volume.fade_out,
                )

        # ----------------------------------------------------
        # 7. CROP / ASPECT RATIO
        # ----------------------------------------------------
        if plan.crop:
            ratios = {
                "16:9": 16 / 9,
                "9:16": 9 / 16,
                "1:1": 1.0,
                "4:5": 4 / 5,
            }

            ratio = ratios[plan.crop.aspect_ratio]

            video = video.filter(
                "crop",
                f"min(iw,ih*{ratio:.8f})",
                f"min(ih,iw/{ratio:.8f})",
            )

        # ----------------------------------------------------
        # 8. COLOR GRADING
        # ----------------------------------------------------
        if plan.color_grading:
            grading = plan.color_grading

            video = video.filter(
                "eq",
                brightness=grading.brightness,
                contrast=grading.contrast,
                saturation=grading.saturation,
            )

        # ----------------------------------------------------
        # 9. VIDEO FADE EFFECTS
        # ----------------------------------------------------
        if plan.fade_effects:
            fades = plan.fade_effects

            if fades.fade_in_sec > 0:
                video = video.filter(
                    "fade",
                    type="in",
                    start_time=0,
                    duration=fades.fade_in_sec,
                )

            if fades.fade_out_sec > 0:
                video = video.filter(
                    "fade",
                    type="out",
                    start_time=output_duration - fades.fade_out_sec,
                    duration=fades.fade_out_sec,
                )

        # ----------------------------------------------------
        # 10. TEXT OVERLAY
        # ----------------------------------------------------
        if plan.text_overlay:
            overlay = plan.text_overlay

            positions = {
                "top": "50",
                "center": "(h-text_h)/2",
                "bottom": "h-text_h-50",
            }

            font_path = "C:/Windows/Fonts/arial.ttf"

            drawtext_options = {
                "text": self._escape_drawtext(overlay.text),
                "x": "(w-text_w)/2",
                "y": positions[overlay.position],
                "fontsize": 30,
                "fontcolor": "white",
                "box": 1,
                "boxcolor": "black@0.6",
                "boxborderw": 10,
            }

            if os.path.isfile(font_path):
                drawtext_options["fontfile"] = font_path

            video = video.filter("drawtext", **drawtext_options)

        # ----------------------------------------------------
        # 11. RENDER OUTPUT
        # ----------------------------------------------------
        output_directory = os.path.dirname(
            os.path.abspath(output_path)
        )
        os.makedirs(output_directory, exist_ok=True)

        output_options = {
            "vcodec": "libx264",
            "pix_fmt": "yuv420p",
            "movflags": "+faststart",
        }

        if audio is not None:
            output_options["acodec"] = "aac"
            output_stream = ffmpeg.output(
                video, audio, output_path, **output_options
            )
        else:
            output_stream = ffmpeg.output(
                video, output_path, **output_options
            )

        try:
            output_stream.overwrite_output().run(
                capture_stdout=True,
                capture_stderr=True,
            )
        except ffmpeg.Error as exc:
            error_details = (
                exc.stderr.decode("utf-8", errors="replace")
                if exc.stderr
                else str(exc)
            )

            raise RuntimeError(
                f"FFmpeg rendering failed:\n{error_details}"
            ) from exc

        return output_path
