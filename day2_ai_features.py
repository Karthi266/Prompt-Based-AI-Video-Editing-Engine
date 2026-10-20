"""Speech transcription, subtitle rendering, and silence removal."""
from __future__ import annotations
import re, subprocess, textwrap
from pathlib import Path
from typing import List, Tuple

class AutoSubtitleGenerator:
    def __init__(self, model_size: str = "base", language: str | None = None):
        import whisper
        self.model = whisper.load_model(model_size)
        self.language = language

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        ms = max(0, round(seconds * 1000))
        hrs, ms = divmod(ms, 3_600_000); mins, ms = divmod(ms, 60_000); secs, ms = divmod(ms, 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

    def generate_srt(self, video_path: str, output_srt_path: str) -> str:
        # Whisper can transcribe silent/no-audio videos poorly; detect audio stream first.
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path], capture_output=True, text=True)
        if probe.returncode != 0: raise RuntimeError("Could not inspect input video with ffprobe.")
        if not probe.stdout.strip():
            Path(output_srt_path).write_text("", encoding="utf-8")
            return output_srt_path
        options = {"word_timestamps": False, "verbose": False}
        if self.language: options["language"] = self.language
        result = self.model.transcribe(video_path, **options)
        blocks = []
        for i, seg in enumerate(result.get("segments", []), 1):
            raw = " ".join(seg.get("text", "").split()).strip()
            if not raw: continue
            wrapped = "\n".join(textwrap.wrap(raw, width=34, break_long_words=False, break_on_hyphens=False))
            blocks.append(f"{i}\n{self._format_timestamp(float(seg['start']))} --> {self._format_timestamp(float(seg['end']))}\n{wrapped}")
        Path(output_srt_path).write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
        return output_srt_path

class SilenceJumpCutter:
    def __init__(self, noise_db: int = -35, min_duration: float = 0.5):
        self.noise_db = noise_db; self.min_duration = min_duration

    @staticmethod
    def _run(cmd):
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    def get_total_duration(self, video_path: str) -> float:
        res = self._run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path])
        if res.returncode != 0 or not res.stdout.strip(): raise RuntimeError("Unable to read video duration.")
        return float(res.stdout.strip())

    def get_speech_intervals(self, video_path: str) -> List[Tuple[float, float]]:
        total = self.get_total_duration(video_path)
        res = self._run(["ffmpeg", "-hide_banner", "-i", video_path, "-af", f"silencedetect=noise={self.noise_db}dB:d={self.min_duration}", "-f", "null", "-"])
        log = res.stderr or ""
        starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", log)]
        ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
        # Pair events in order and handle silence at the beginning/end explicitly.
        silences = []
        pending = None
        for line in log.splitlines():
            m = re.search(r"silence_start:\s*([\d.]+)", line)
            if m: pending = float(m.group(1)); continue
            m = re.search(r"silence_end:\s*([\d.]+)", line)
            if m and pending is not None:
                silences.append((max(0, pending), min(total, float(m.group(1)))))
                pending = None
        if pending is not None: silences.append((max(0, pending), total))
        speech, cursor = [], 0.0
        for a,b in silences:
            if a > cursor + 0.03: speech.append((cursor, a))
            cursor = max(cursor, b)
        if cursor < total - 0.03: speech.append((cursor, total))
        return [(a,b) for a,b in speech if b-a >= 0.04]

    def remove_silence(self, input_video: str, output_video: str) -> str:
        intervals = self.get_speech_intervals(input_video)
        if not intervals:
            # Avoid replacing a valid source with an empty output when no speech is detected.
            import shutil; shutil.copy2(input_video, output_video); return output_video
        import ffmpeg
        probe = self._run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", input_video])
        has_audio = "audio" in (probe.stdout or "")
        src = ffmpeg.input(input_video)
        vparts=[]; aparts=[]
        for start,end in intervals:
            vparts.append(src.video.filter("trim", start=start, end=end).filter("setpts", "PTS-STARTPTS"))
            if has_audio: aparts.append(src.audio.filter("atrim", start=start, end=end).filter("asetpts", "PTS-STARTPTS"))
        if has_audio:
            joined = ffmpeg.concat(*[x for pair in zip(vparts, aparts) for x in pair], v=1, a=1).node
            out = ffmpeg.output(joined[0], joined[1], output_video, vcodec="libx264", acodec="aac", pix_fmt="yuv420p", movflags="+faststart").overwrite_output()
        else:
            joined = ffmpeg.concat(*vparts, v=1, a=0).node[0]
            out = ffmpeg.output(joined, output_video, vcodec="libx264", pix_fmt="yuv420p", movflags="+faststart").overwrite_output()
        try: out.run(capture_stdout=True, capture_stderr=True)
        except ffmpeg.Error as e:
            details=e.stderr.decode("utf-8", errors="replace") if e.stderr else str(e)
            raise RuntimeError(f"Silence removal failed: {details[-2000:]}") from e
        return output_video

def burn_subtitles(input_video: str, srt_path: str, output_video: str, font_size: int = 22, margin_v: int = 55) -> str:
    """Burn SRT subtitles with libass. Subtitles are rendered AFTER crop/scale so they fit the final frame."""
    srt = Path(srt_path)
    if not srt.is_file(): raise FileNotFoundError(f"Subtitle file not found: {srt}")
    if not srt.read_text(encoding="utf-8").strip():
        # No subtitles: re-encode/copy streams without adding a filter.
        cmd=["ffmpeg", "-y", "-i", input_video, "-c", "copy", output_video]
    else:
        # libass handles wrapping and subtitle timing much more robustly than chained drawtext filters.
        escaped = str(srt.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        style=f"FontName=Arial,FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV={margin_v},WrapStyle=2"
        cmd=["ffmpeg", "-y", "-i", input_video, "-vf", f"subtitles='{escaped}':force_style='{style}'", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", output_video]
    res=subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0: raise RuntimeError(f"Subtitle rendering failed. Ensure FFmpeg includes libass.\n{res.stderr[-2500:]}")
    return output_video
