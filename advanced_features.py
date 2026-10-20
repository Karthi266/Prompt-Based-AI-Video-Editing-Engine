"""Advanced video operations: transitions, speed ramps, TTS, voiceover, AI provider adapters.

AI video endpoints are provider/model dependent. The Replicate adapter deliberately accepts
model-specific extra JSON input rather than assuming every model has identical parameters.
"""
from __future__ import annotations
import asyncio, json, os, shutil, subprocess, time
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr[-3000:]}")


def probe_duration(path: str) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr)
    return float(p.stdout.strip())


def speed_ramp(input_path: str, output_path: str, segments: list[dict[str, float]]) -> str:
    """Apply piecewise constant speed factors. Each segment is {start,end,speed}; intervals must cover timeline in order."""
    import ffmpeg
    duration = probe_duration(input_path)
    if not segments: raise ValueError("Add at least one speed segment.")
    clean=[]; cursor=0.0
    for seg in segments:
        start=float(seg['start']); end=float(seg['end']); speed=float(seg['speed'])
        if abs(start-cursor) > 0.02 or end <= start or end > duration + 0.02 or not 0.25 <= speed <= 4:
            raise ValueError("Speed-ramp segments must be contiguous, ordered, inside the clip, and use speeds from 0.25x to 4x.")
        clean.append((start,min(end,duration),speed)); cursor=end
    if abs(cursor-duration) > 0.1: raise ValueError(f"Segments must cover the full {duration:.2f}s source (currently cover {cursor:.2f}s).")
    src=ffmpeg.input(input_path); has_audio = subprocess.run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=index","-of","csv=p=0",input_path],capture_output=True,text=True).stdout.strip() != ''
    vp=[]; ap=[]
    for start,end,factor in clean:
        vp.append(src.video.filter('trim',start=start,end=end).filter('setpts',f'(PTS-STARTPTS)/{factor}'))
        if has_audio:
            a=src.audio.filter('atrim',start=start,end=end).filter('asetpts','PTS-STARTPTS')
            remaining=factor
            while remaining > 2: a=a.filter('atempo',2); remaining/=2
            while remaining < .5: a=a.filter('atempo',.5); remaining/=.5
            ap.append(a.filter('atempo',remaining))
    if has_audio:
        joined=ffmpeg.concat(*[z for pair in zip(vp,ap) for z in pair],v=1,a=1).node
        out=ffmpeg.output(joined[0],joined[1],output_path,vcodec='libx264',acodec='aac',pix_fmt='yuv420p',movflags='+faststart').overwrite_output()
    else:
        joined=ffmpeg.concat(*vp,v=1,a=0).node[0]
        out=ffmpeg.output(joined,output_path,vcodec='libx264',pix_fmt='yuv420p',movflags='+faststart').overwrite_output()
    try: out.run(capture_stdout=True,capture_stderr=True)
    except ffmpeg.Error as e: raise RuntimeError((e.stderr or b'').decode(errors='replace')[-3000:])
    return output_path


def merge_with_transition(input_paths: list[str], output_path: str, transition: str='fade', duration: float=0.7, width: int=1280, height: int=720) -> str:
    """Merge 2+ clips using xfade and acrossfade. Supports FFmpeg xfade transitions."""
    allowed={'fade','wipeleft','wiperight','wipeup','wipedown','slideleft','slideright','circleopen','circleclose','dissolve','pixelize','smoothleft','smoothright'}
    if len(input_paths)<2: raise ValueError('Choose at least two clips.')
    if transition not in allowed: raise ValueError(f"Choose one of: {', '.join(sorted(allowed))}")
    if duration <= 0 or duration > 3: raise ValueError('Transition duration must be between 0 and 3 seconds.')
    import ffmpeg
    ins=[ffmpeg.input(p) for p in input_paths]
    durations=[probe_duration(p) for p in input_paths]
    videos=[]; audios=[]; audio_flags=[]
    for inp,path in zip(ins,input_paths):
        videos.append(inp.video.filter('scale',width,height,force_original_aspect_ratio='decrease').filter('pad',width,height,'(ow-iw)/2','(oh-ih)/2').filter('setsar',1).filter('setpts','PTS-STARTPTS').filter('fps',30).filter('format','yuv420p').filter('settb','1/30'))
        has=subprocess.run(['ffprobe','-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',path],capture_output=True,text=True).stdout.strip()!=''
        audio_flags.append(has)
        if has: audios.append(inp.audio.filter('aresample',48000).filter('aformat',sample_fmts='fltp',channel_layouts='stereo').filter('asetpts','PTS-STARTPTS'))
        else: audios.append(ffmpeg.input('anullsrc=r=48000:cl=stereo',f='lavfi',t=durations[len(audios)]).audio)
    v=videos[0]; cumulative=durations[0]
    a=audios[0]
    for i in range(1,len(videos)):
        td=min(duration, max(0.1, durations[i-1]*0.4), max(0.1,durations[i]*0.4))
        offset=max(0,cumulative-td)
        v=ffmpeg.filter([v,videos[i]],'xfade',transition=transition,duration=td,offset=offset)
        a=ffmpeg.filter([a,audios[i]],'acrossfade',d=td,c1='tri',c2='tri')
        cumulative += durations[i]-td
    out=ffmpeg.output(v,a,output_path,vcodec='libx264',acodec='aac',pix_fmt='yuv420p',movflags='+faststart').overwrite_output()
    try: out.run(capture_stdout=True,capture_stderr=True)
    except ffmpeg.Error as e: raise RuntimeError((e.stderr or b'').decode(errors='replace')[-3000:])
    return output_path


def generate_tts(text: str, output_audio: str, voice: str='en-US-AriaNeural', rate: str='+0%') -> str:
    """Generate speech with edge-tts. Internet is required; available voices can change."""
    if not text.strip(): raise ValueError('Enter voiceover text.')
    try: import edge_tts
    except ImportError as e: raise RuntimeError('Install edge-tts with: pip install edge-tts') from e
    async def _make():
        communicate=edge_tts.Communicate(text,voice,rate=rate)
        await communicate.save(output_audio)
    asyncio.run(_make())
    return output_audio


def add_voiceover(video_path: str, voice_path: str, output_path: str, voice_volume: float=1.0, original_volume: float=0.35, duck_original: bool=True) -> str:
    import ffmpeg
    inp=ffmpeg.input(video_path); voice=ffmpeg.input(voice_path)
    has=subprocess.run(['ffprobe','-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',video_path],capture_output=True,text=True).stdout.strip()!=''
    voice_audio=voice.audio.filter('volume',voice_volume)
    if has:
        original=inp.audio.filter('volume',original_volume)
        voice_mix=voice_audio
        if duck_original:
            # Split narration: one copy controls sidechain compression, the other remains audible in the final mix.
            voice_split=voice_audio.filter_multi_output('asplit',2)
            voice_control=voice_split[0]; voice_mix=voice_split[1]
            original=ffmpeg.filter([original,voice_control],'sidechaincompress',threshold=0.025,ratio=10,attack=15,release=400,makeup=1)
        mixed=ffmpeg.filter([original,voice_mix],'amix',inputs=2,duration='first',dropout_transition=2)
    else: mixed=voice_audio
    out=ffmpeg.output(inp.video,mixed,output_path,vcodec='libx264',acodec='aac',pix_fmt='yuv420p',movflags='+faststart').overwrite_output()
    try: out.run(capture_stdout=True,capture_stderr=True)
    except ffmpeg.Error as e: raise RuntimeError((e.stderr or b'').decode(errors='replace')[-2500:])
    return output_path


def remove_video_background(input_path: str, output_path: str, background_color: str='#202020', max_width: int=960) -> str:
    """Frame-by-frame rembg segmentation and solid-color compositing. Slow and may flicker; not a temporal matting model."""
    try:
        from rembg import remove, new_session
        from PIL import Image
    except ImportError as e: raise RuntimeError('Install optional dependencies: pip install rembg onnxruntime pillow') from e
    import tempfile
    work=Path(tempfile.mkdtemp(prefix='rembg_video_')); frames=work/'frames'; cutouts=work/'cutouts'; frames.mkdir(); cutouts.mkdir()
    try:
        run_cmd(['ffmpeg','-y','-i', input_path,'-vf', f'scale={max_width}:-2','-fps_mode', 'passthrough',str(frames / 'frame_%06d.png')])
        files=sorted(frames.glob('frame_*.png'))
        if not files: raise RuntimeError('No frames extracted from the source video.')
        session=new_session('u2net')
        bg=background_color.lstrip('#')
        if len(bg)!=6: raise ValueError('Background color must be a hex color like #202020.')
        rgb=tuple(int(bg[i:i+2],16) for i in (0,2,4))
        for i,fp in enumerate(files):
            cut=remove(Image.open(fp).convert('RGBA'),session=session)
            base=Image.new('RGBA',cut.size,rgb+(255,)); base.alpha_composite(cut)
            base.convert('RGB').save(cutouts/f'frame_{i+1:06d}.jpg',quality=94)
        fps_out=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=r_frame_rate','-of','csv=p=0',input_path],capture_output=True,text=True).stdout.strip() or '30/1'
        video_only=work/'background_removed.mp4'
        run_cmd(['ffmpeg','-y','-framerate',fps_out,'-i',str(cutouts/'frame_%06d.jpg'),'-i',input_path,'-map','0:v:0','-map','1:a?','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',str(video_only)])
        shutil.copy2(video_only,output_path)
        return output_path
    finally: shutil.rmtree(work,ignore_errors=True)


def replicate_video_task(input_path: str | None, prompt: str, output_path: str, model_slug: str, extra_input_json: str='{}', task: str='video') -> str:
    """Call a configured Replicate model. Model input keys vary; extra_input_json overrides defaults.
    Requires REPLICATE_API_TOKEN and a model slug such as owner/model. Review model-specific schema first.
    """
    import requests
    token=os.getenv('REPLICATE_API_TOKEN')
    if not token: raise RuntimeError('Set REPLICATE_API_TOKEN before using hosted AI video features.')
    if not model_slug or '/' not in model_slug: raise ValueError('Enter the model slug as owner/model.')
    try: extra=json.loads(extra_input_json or '{}')
    except json.JSONDecodeError as e: raise ValueError(f'Extra model input must be valid JSON: {e}')
    if not isinstance(extra,dict): raise ValueError('Extra model input JSON must be an object.')
    video_input_key=extra.pop('__video_input_key','video')
    if not isinstance(video_input_key,str) or not video_input_key.strip(): raise ValueError('__video_input_key must be a non-empty model input field name.')
    headers={'Authorization':f'Token {token}','Prefer':'wait=5'}
    input_data={'prompt':prompt,**extra}
    if input_path:
        with open(input_path,'rb') as f:
            up=requests.post('https://api.replicate.com/v1/files',headers={'Authorization':f'Token {token}'},files={'content':(Path(input_path).name,f,'application/octet-stream')},timeout=180)
        if up.status_code>=300: raise RuntimeError(f'Replicate upload failed ({up.status_code}): {up.text[:1200]}')
        # Model input names differ. Set __video_input_key in extra_input_json to the exact field name.
        input_data.setdefault(video_input_key,up.json().get('urls',{}).get('get'))
    url=f'https://api.replicate.com/v1/models/{model_slug}/predictions'
    res=requests.post(url,headers=headers,json={'input':input_data},timeout=180)
    if res.status_code>=300: raise RuntimeError(f'Replicate prediction request failed ({res.status_code}): {res.text[:2000]}')
    data=res.json(); get_url=data.get('urls',{}).get('get')
    deadline=time.time()+3600
    while get_url and data.get('status') not in ('succeeded','failed','canceled') and time.time()<deadline:
        time.sleep(3); poll=requests.get(get_url,headers={'Authorization':f'Token {token}'},timeout=60)
        if poll.status_code>=300: raise RuntimeError(f'Could not check prediction: {poll.text[:1000]}')
        data=poll.json()
    if data.get('status')!='succeeded': raise RuntimeError(f"AI model status: {data.get('status')}. {data.get('error') or ''}")
    result=data.get('output')
    if isinstance(result,list): result=result[0] if result else None
    if isinstance(result,dict): result=result.get('video') or result.get('url') or result.get('output')
    if not isinstance(result,str) or not result.startswith('http'): raise RuntimeError(f'Could not identify a downloadable output URL in model result: {str(result)[:500]}')
    download=requests.get(result,timeout=300); download.raise_for_status(); Path(output_path).write_bytes(download.content)
    return output_path


def split_video_at(input_path: str, split_times: list[float], output_dir: str) -> list[str]:
    """Split a video at timestamps (seconds), writing sequential MP4 segments."""
    import ffmpeg
    duration=probe_duration(input_path)
    cuts=sorted(float(x) for x in split_times)
    if any(x<=0 or x>=duration for x in cuts) or len(set(cuts))!=len(cuts):
        raise ValueError(f"Split points must be unique timestamps strictly between 0 and {duration:.2f}s.")
    points=[0.0,*cuts,duration]; outdir=Path(output_dir); outdir.mkdir(parents=True,exist_ok=True); outputs=[]
    for i,(start,end) in enumerate(zip(points,points[1:]),1):
        dst=outdir/f"segment_{i:02d}.mp4"
        inp=ffmpeg.input(input_path,ss=start,t=end-start)
        out=ffmpeg.output(inp.video,inp.audio,str(dst),vcodec='libx264',acodec='aac',pix_fmt='yuv420p',movflags='+faststart').overwrite_output()
        try: out.run(capture_stdout=True,capture_stderr=True)
        except ffmpeg.Error as e: raise RuntimeError((e.stderr or b'').decode(errors='replace')[-2500:])
        outputs.append(str(dst))
    return outputs
