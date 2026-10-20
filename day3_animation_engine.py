"""Day 3: reusable motion graphics, clip merging, transitions and image overlays.
This module uses FFmpeg filters; it does not pretend that FFmpeg alone can perform
semantic object replacement (e.g. apple -> dog). That requires a generative video
inpainting model and is documented in README.md.
"""
from __future__ import annotations
import subprocess
from pathlib import Path


def _run(cmd):
    res=subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode: raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n{res.stderr[-2500:]}")
    return res


def merge_clips(input_paths: list[str], output_path: str) -> str:
    """Merge clips sequentially. Re-encodes for consistent dimensions/codecs."""
    if len(input_paths) < 2: raise ValueError("Provide at least two clips to merge.")
    import ffmpeg
    streams=[ffmpeg.input(p) for p in input_paths]
    # Normalize every clip to 1280x720. This simple merge uses hard cuts.
    pairs=[]
    for s in streams:
        v=s.video.filter("scale", 1280, 720, force_original_aspect_ratio="decrease").filter("pad",1280,720,"(ow-iw)/2","(oh-ih)/2").filter("setsar",1).filter("setpts","PTS-STARTPTS")
        # This initial helper expects every clip to have audio. For mixed audio/no-audio sources, use a future audio-normalization pass.
        a=s.audio.filter("asetpts","PTS-STARTPTS")
        pairs.extend([v,a])
    joined=ffmpeg.concat(*pairs, v=1, a=1).node
    out=ffmpeg.output(joined[0], joined[1], output_path, vcodec="libx264", acodec="aac", pix_fmt="yuv420p", movflags="+faststart").overwrite_output()
    try: out.run(capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        details=e.stderr.decode("utf-8", errors="replace") if e.stderr else str(e)
        raise RuntimeError(f"Clip merge failed: {details[-2500:]}") from e
    return output_path


def add_image_overlay(video_path: str, image_path: str, output_path: str,
                      position: str="top_right", start: float=0, duration: float=5,
                      width: int=220, animation: str="fade") -> str:
    """Overlay a PNG/JPG/logo. Coordinates stay inside the final frame."""
    positions={"top_left":"20:20", "top_right":"main_w-overlay_w-20:20",
               "bottom_left":"20:main_h-overlay_h-20", "bottom_right":"main_w-overlay_w-20:main_h-overlay_h-20",
               "center":"(main_w-overlay_w)/2:(main_h-overlay_h)/2"}
    if position not in positions: raise ValueError(f"Unsupported position: {position}")
    if not Path(image_path).is_file(): raise FileNotFoundError(image_path)
    inp=__import__("ffmpeg").input(video_path); image=__import__("ffmpeg").input(image_path, loop=1, framerate=30)
    overlay=image.video.filter("scale", width, -1).filter("format", "rgba")
    if animation == "fade": overlay=overlay.filter("fade", type="in", start_time=0, duration=min(0.8,duration), alpha=1)
    enable=f"between(t,{start},{start+duration})"
    v=__import__("ffmpeg").overlay(inp.video, overlay, x=positions[position].split(":")[0], y=positions[position].split(":",1)[1], enable=enable, eof_action="pass", shortest=1)
    opts={"vcodec":"libx264","pix_fmt":"yuv420p","movflags":"+faststart"}
    probe=_run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=codec_type","-of","csv=p=0",video_path])
    if "audio" in (probe.stdout or ""): out=__import__("ffmpeg").output(v,inp.audio,output_path,acodec="aac",**opts).overwrite_output()
    else: out=__import__("ffmpeg").output(v,output_path,**opts).overwrite_output()
    try: out.run(capture_stdout=True,capture_stderr=True)
    except Exception as e: raise RuntimeError(f"Image overlay render failed: {e}") from e
    return output_path


def replace_object_with_model(input_path: str, prompt: str, output_path: str, model_slug: str, extra_input_json: str = "{}") -> str:
    """Call a configured hosted video model; the selected model must support localized video inpainting."""
    from advanced_features import replicate_video_task
    if not prompt.strip(): raise ValueError("Describe the object replacement/edit you want.")
    return replicate_video_task(input_path, prompt, output_path, model_slug, extra_input_json, task="video")
