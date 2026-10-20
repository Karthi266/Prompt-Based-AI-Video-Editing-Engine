
from __future__ import annotations

import os
import tempfile
import traceback
from pathlib import Path

import streamlit as st

from day1_engine import FFmpegVideoEngine, IntentParser
from day2_ai_features import (
    AutoSubtitleGenerator,
    SilenceJumpCutter,
    burn_subtitles,
)
from day3_animation_engine import add_image_overlay

from advanced_features import (
    speed_ramp,
    merge_with_transition,
    generate_tts,
    add_voiceover,
    remove_video_background,
    probe_duration,
    split_video_at,
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="NovaCut | AI Video Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# CUSTOM UI THEME
# --------------------------------------------------

st.markdown(
    """
    
<style>
/* ===== COLOURFUL LIGHT THEME ===== */

.stApp {
    background: linear-gradient(135deg, #f5f3ff 0%, #eef6ff 48%, #fff1f7 100%);
    color: #202442;
}

.block-container {
    max-width: 1500px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f0edff 100%);
    border-right: 1px solid #ddd6fe;
}

[data-testid="stSidebar"] * {
    color: #302858;
}

/* General text */
.stApp, .stApp p, .stApp label,
.stApp [data-testid="stMarkdownContainer"] {
    color: #28304a;
}

h1, h2, h3 {
    color: #39277d !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
}

/* Hero banner */
.hero {
    padding: 34px;
    border-radius: 24px;
    background: linear-gradient(115deg, #6c3df4, #4778f5 55%, #e15bb7);
    box-shadow: 0 12px 35px rgba(91, 76, 220, 0.20);
    margin-bottom: 28px;
}

.hero-tag {
    color: #f3e8ff !important;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-size: 0.78rem;
    font-weight: 800;
    margin-bottom: 12px;
}

.hero-title {
    color: #ffffff !important;
    font-size: clamp(2rem, 4vw, 3.1rem);
    line-height: 1.15;
    font-weight: 850;
    margin: 0;
}

.hero-description {
    color: #f5f3ff !important;
    font-size: 1rem;
    line-height: 1.8;
    max-width: 800px;
    margin-top: 12px;
}

/* Feature cards */
.feature-card {
    padding: 20px;
    min-height: 140px;
    border-radius: 18px;
    background: #ffffff;
    border: 1px solid #e1ddff;
    box-shadow: 0 5px 18px rgba(62, 48, 130, 0.08);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 25px rgba(91, 76, 220, 0.16);
}

.feature-icon {
    font-size: 1.8rem;
    margin-bottom: 12px;
}

.feature-name {
    color: #4528a8 !important;
    font-size: 1rem;
    font-weight: 800;
}

.feature-description {
    color: #65708c !important;
    font-size: 0.85rem;
    line-height: 1.6;
    margin-top: 7px;
}

/* Containers */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid #e1ddff !important;
    border-radius: 18px !important;
    box-shadow: 0 5px 20px rgba(62, 48, 130, 0.06);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    padding: 8px;
    background: #e9e5ff;
    border-radius: 15px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 12px 15px;
    color: #514779 !important;
    font-weight: 700;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(110deg, #7148f5, #4988f7) !important;
    color: #ffffff !important;
}

/* Inputs */
[data-baseweb="input"],
[data-baseweb="textarea"],
[data-baseweb="select"] {
    background-color: #ffffff !important;
    border-radius: 10px !important;
}

input, textarea {
    color: #252744 !important;
    background-color: #ffffff !important;
}

[data-testid="stFileUploader"] {
    background: #f7f5ff;
    border: 1px dashed #a89bfa;
    border-radius: 14px;
    padding: 10px;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    border-radius: 11px;
    font-weight: 750;
    min-height: 44px;
    border: 1px solid #d6ceff;
    color: #4b32ad;
    background: #ffffff;
    transition: all 0.2s ease;
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(110deg, #7046f4, #4388f7);
    color: #ffffff !important;
    border: none;
    box-shadow: 0 5px 13px rgba(103, 70, 244, 0.20);
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    border-color: #8b76fa;
    transform: translateY(-2px);
    box-shadow: 0 7px 17px rgba(103, 70, 244, 0.14);
}

/* Expanders */
[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #ddd6fe;
    border-radius: 13px;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 13px;
}

/* Progress and separators */
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #7847f5, #3e9cf7, #ec69b7);
}

hr {
    border-color: #dcd8f5;
}

/* Captions */
[data-testid="stCaptionContainer"] {
    color: #68728d;
}

/* Slider accent */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background-color: #7148f5;
}

/* Video previews */
[data-testid="stVideo"] {
    border-radius: 14px;
    overflow: hidden;
}

/* Footer */
</style>

    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HEADER
# --------------------------------------------------


st.markdown("""
<div class="hero">
    <div class="hero-tag">✦ AI-powered creative workspace</div>
    <div class="hero-title">NovaCut AI Video Studio</div>
    <div class="hero-description">
        Transform your footage with AI-assisted editing, subtitles,
        visual overlays, transitions, and professional audio tools.
    </div>
</div>
""", unsafe_allow_html=True)



# --------------------------------------------------
# SIDEBAR SETTINGS
# --------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Studio settings")
    st.caption("Configure your video processing pipeline.")

    st.divider()

    enable_silence_cut = st.checkbox(
        "✂️ Smart silence removal",
        value=False,
        help="Detect and remove silence. Review the result for natural pauses.",
    )

    enable_subtitles = st.checkbox(
        "💬 Auto-generate subtitles",
        value=True,
    )

    whisper_model = st.selectbox(
        "Speech recognition model",
        ["tiny", "base", "small", "medium"],
        index=1,
        help="Larger models can improve transcription but generally need more resources.",
    )

    subtitle_size = st.slider(
        "Subtitle font size",
        16,
        36,
        22,
    )

    subtitle_margin = st.slider(
        "Subtitle bottom margin",
        20,
        100,
        55,
        help="Increase the value to move subtitles farther upward from the bottom.",
    )

    st.divider()

    st.markdown("**🧰 Available tools**")
    st.caption("AI editing · Subtitles · Branding · Speed control · Transitions · Audio")


# --------------------------------------------------
# MAIN EDITOR
# --------------------------------------------------

st.markdown("## ✨ AI Video Editor")
st.caption("Upload your footage and describe the changes you want in plain English.")

feature_columns = st.columns(4)

feature_items = [
    ("🎬", "Prompt editing", "Describe edits using natural language."),
    ("💬", "Smart subtitles", "Transcribe speech and burn captions."),
    ("✂️", "Silence removal", "Remove unwanted pauses."),
    ("🎨", "Visual styling", "Apply supported edits through your prompt."),
]

for column, (icon, name, description) in zip(feature_columns, feature_items):
    with column:
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-name">{name}</div>
                <div class="feature-description">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")

c1, c2 = st.columns([1, 1], gap="large")

with c1:
    with st.container(border=True):
        st.markdown("### 📁 Source media")
        st.caption("Choose the video you want to edit.")

        uploaded = st.file_uploader(
            "Upload a video",
            type=["mp4", "mov", "mkv"],
            help="Supported formats: MP4, MOV, MKV.",
            key="main_video",
        )

        if uploaded:
            st.video(uploaded)
            st.caption(f"Selected file: {uploaded.name}")
        else:
            st.info("Your video preview will appear here after upload.")

with c2:
    with st.container(border=True):
        st.markdown("### ✍️ Editing instructions")
        st.caption("Tell the editor what you want to change.")

        prompt = st.text_area(
            "Describe your desired edits",
            value=(
                "Trim the first 1 second, speed up video to 1.15x, "
                "crop into a 1:1 square ratio, and overlay text "
                "'CLOUD COMPUTING 101' at the bottom."
            ),
            height=155,
            placeholder="Example: Trim the beginning, add a title, and crop to vertical format.",
            help="The available operations depend on the capabilities of your prompt parser.",
        )

        with st.expander("💡 Prompt examples"):
            st.markdown(
                """
                - Fade in the title.
                - Convert the video to 9:16 vertical format.
                - Trim the opening section.
                - Add text at the bottom of the video.
                - Apply a cinematic color grade.
                """
            )

        run = st.button(
            "🚀 Generate edit plan & render",
            type="primary",
            use_container_width=True,
            disabled=uploaded is None,
        )


# --------------------------------------------------
# MAIN VIDEO RENDERING
# --------------------------------------------------

if run and uploaded:
    work = Path(tempfile.mkdtemp(prefix="prompt_video_editor_"))
    suffix = Path(uploaded.name).suffix.lower() or ".mp4"
    source = work / f"source{suffix}"
    source.write_bytes(uploaded.getvalue())

    try:
        engine = FFmpegVideoEngine(str(source))

        with st.spinner("🧠 Converting your prompt into an edit plan..."):
            plan = IntentParser().parse_prompt(
                prompt,
                engine.get_video_duration(),
            )

        with st.expander("🗺️ View generated edit plan"):
            st.json(plan.model_dump())

        stage1 = str(work / "stage1.mp4")

        with st.spinner("🎬 Applying video edits..."):
            engine.execute_plan(plan, stage1)

        current = stage1
        srt = None

        if enable_silence_cut:
            stage2 = str(work / "jumpcut.mp4")

            with st.spinner("✂️ Detecting and removing silence..."):
                SilenceJumpCutter().remove_silence(current, stage2)

            current = stage2

        if enable_subtitles:
            srt = str(work / "subtitles.srt")
            final = str(work / "final_edited_output.mp4")

            with st.spinner("💬 Transcribing speech and rendering subtitles..."):
                AutoSubtitleGenerator(
                    model_size=whisper_model
                ).generate_srt(current, srt)

                burn_subtitles(
                    current,
                    srt,
                    final,
                    font_size=subtitle_size,
                    margin_v=subtitle_margin,
                )

            current = final

        st.divider()
        st.markdown("## ✅ Your video is ready")
        st.success("Video processing completed successfully.")

        left, right = st.columns(2, gap="large")

        with left:
            st.markdown("### 🎞️ Original video")
            st.video(str(source))

        with right:
            st.markdown("### ✨ Edited result")
            st.video(current)

            st.download_button(
                "⬇️ Download edited video",
                data=Path(current).read_bytes(),
                file_name="edited_output.mp4",
                mime="video/mp4",
                use_container_width=True,
            )

        if enable_subtitles and srt and Path(srt).exists():
            with st.expander("📝 View generated subtitle file"):
                st.code(
                    Path(srt).read_text(encoding="utf-8")[:12000],
                    language="text",
                )

    except Exception as exc:
        st.error(f"Video processing failed: {exc}")

        with st.expander("🔧 Technical details"):
            st.code(traceback.format_exc())


# --------------------------------------------------
# IMAGE OVERLAYS & BRANDING
# --------------------------------------------------

st.divider()
st.markdown("## 🖼️ Overlays & Branding")
st.caption(
    "Add logos, stickers, watermarks, or other images on top of a video."
)

with st.container(border=True):
    with st.form("overlay_form"):
        overlay_image = st.file_uploader(
            "Upload an overlay image",
            type=["png", "jpg", "jpeg"],
            key="overlay_image",
            help="Transparent PNG images work well for logos.",
        )

        pos = st.selectbox(
            "Overlay position",
            [
                "top_left",
                "top_right",
                "center",
                "bottom_left",
                "bottom_right",
            ],
            format_func=lambda value: value.replace("_", " ").title(),
        )

        col1, col2 = st.columns(2)

        with col1:
            start = st.number_input(
                "Start time (seconds)",
                min_value=0.0,
                value=0.0,
                step=0.5,
            )

        with col2:
            dur = st.number_input(
                "Duration (seconds)",
                min_value=0.2,
                value=5.0,
                step=0.5,
            )

        width = st.slider(
            "Overlay width",
            60,
            600,
            220,
            step=20,
        )

        overlay_submit = st.form_submit_button(
            "🎨 Apply image overlay",
            type="primary",
            use_container_width=True,
        )

if overlay_submit:
    if not uploaded or not overlay_image:
        st.warning("Upload both the source video and an overlay image.")
    else:
        work2 = Path(tempfile.mkdtemp(prefix="video_overlay_"))
        src = work2 / Path(uploaded.name).name
        img = work2 / Path(overlay_image.name).name
        dst = work2 / "overlay_output.mp4"

        src.write_bytes(uploaded.getvalue())
        img.write_bytes(overlay_image.getvalue())

        try:
            with st.spinner("🎨 Rendering your overlay..."):
                add_image_overlay(
                    str(src),
                    str(img),
                    str(dst),
                    position=pos,
                    start=start,
                    duration=dur,
                    width=width,
                )

            st.success("Overlay applied successfully.")
            st.video(str(dst))

            st.download_button(
                "⬇️ Download branded video",
                dst.read_bytes(),
                file_name="overlay_output.mp4",
                mime="video/mp4",
            )

        except Exception as exc:
            st.error(f"Overlay processing failed: {exc}")


# --------------------------------------------------
# ADVANCED VIDEO STUDIO
# --------------------------------------------------

st.divider()
st.markdown("## 🛠️ Advanced Video Studio")
st.caption(
    "Fine-tune motion, combine clips, create narration, and replace backgrounds."
)

tab_ramp, tab_merge, tab_voice, tab_bg = st.tabs(
    [
        "⚡ Speed Control",
        "🎞️ Transitions & Clips",
        "🎙️ Voiceover Studio",
        "🪄 Background Removal",
    ]
)


# Shared upload helper
def _save_upload(upload, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / Path(upload.name).name
    dest.write_bytes(upload.getvalue())
    return dest


# --------------------------------------------------
# SPEED CONTROL
# --------------------------------------------------

with tab_ramp:
    st.markdown("### ⚡ Speed Ramp")
    st.caption(
        "Create slow-motion or fast-motion sections using three consecutive speed segments."
    )

    ramp_video = st.file_uploader(
        "Upload video for speed control",
        type=["mp4", "mov", "mkv"],
        key="ramp_video",
    )

    if ramp_video:
        ramp_tmp = Path(tempfile.mkdtemp(prefix="ramp_"))
        ramp_src = _save_upload(ramp_video, ramp_tmp)
        ramp_len = probe_duration(str(ramp_src))

        st.info(f"Video duration: {ramp_len:.2f} seconds")

        if ramp_len <= 0.3:
            st.warning("This video is too short for the three-segment speed ramp.")
        else:
            cut1 = st.slider(
                "First segment ends at (seconds)",
                min_value=0.1,
                max_value=max(0.2, ramp_len - 0.2),
                value=max(0.1, min(ramp_len / 3, ramp_len - 0.2)),
                key="ramp_cut1",
            )

            cut2_min = min(ramp_len - 0.1, cut1 + 0.1)
            cut2_max = max(cut1 + 0.1, ramp_len - 0.05)

            cut2 = st.slider(
                "Second segment ends at (seconds)",
                min_value=cut2_min,
                max_value=cut2_max,
                value=max(
                    cut1 + 0.1,
                    min(2 * ramp_len / 3, ramp_len - 0.05),
                ),
                key="ramp_cut2",
            )

            speeds = st.columns(3)

            speed_options = [
                0.25, 0.5, 0.75, 1.0, 1.25,
                1.5, 2.0, 3.0, 4.0,
            ]

            s1 = speeds[0].select_slider(
                "Segment 1 speed",
                options=speed_options,
                value=1.0,
                key="ramp_s1",
            )

            s2 = speeds[1].select_slider(
                "Segment 2 speed",
                options=speed_options,
                value=2.0,
                key="ramp_s2",
            )

            s3 = speeds[2].select_slider(
                "Segment 3 speed",
                options=speed_options,
                value=1.0,
                key="ramp_s3",
            )

            st.caption(
                f"Speed sequence: {s1}× → {s2}× → {s3}×"
            )

            if st.button(
                "⚡ Apply speed ramp",
                type="primary",
                key="do_ramp",
                use_container_width=True,
            ):
                if not (0 < cut1 < cut2 < ramp_len):
                    st.error(
                        "Choose increasing cut points inside the video duration."
                    )
                else:
                    dst = ramp_tmp / "speed_ramp.mp4"

                    try:
                        with st.spinner("Rendering speed changes..."):
                            speed_ramp(
                                str(ramp_src),
                                str(dst),
                                [
                                    {
                                        "start": 0,
                                        "end": cut1,
                                        "speed": s1,
                                    },
                                    {
                                        "start": cut1,
                                        "end": cut2,
                                        "speed": s2,
                                    },
                                    {
                                        "start": cut2,
                                        "end": ramp_len,
                                        "speed": s3,
                                    },
                                ],
                            )

                        st.success("Speed ramp completed.")
                        st.video(str(dst))

                        st.download_button(
                            "⬇️ Download speed-ramped video",
                            dst.read_bytes(),
                            file_name="speed_ramp.mp4",
                            mime="video/mp4",
                            key="dl_ramp",
                        )

                    except Exception as exc:
                        st.error(str(exc))


# --------------------------------------------------
# TRANSITIONS, MERGING & SPLITTING
# --------------------------------------------------

with tab_merge:
    st.markdown("### 🎞️ Transitions & Video Merge")
    st.caption(
        "Combine multiple clips with transitions. Clips are normalized to 1280×720 at 30 fps."
    )

    merge_uploads = st.file_uploader(
        "Upload clips in the desired order",
        type=["mp4", "mov", "mkv"],
        accept_multiple_files=True,
        key="merge_uploads",
    )

    transition = st.selectbox(
        "Transition effect",
        [
            "fade",
            "dissolve",
            "wipeleft",
            "wiperight",
            "wipeup",
            "wipedown",
            "slideleft",
            "slideright",
            "circleopen",
            "circleclose",
            "pixelize",
            "smoothleft",
            "smoothright",
        ],
        key="transition_kind",
    )

    transition_len = st.slider(
        "Transition duration (seconds)",
        0.2,
        2.0,
        0.7,
        0.1,
        key="transition_len",
    )

    if st.button(
        "🎬 Merge clips",
        type="primary",
        key="do_merge",
        use_container_width=True,
    ):
        if not merge_uploads or len(merge_uploads) < 2:
            st.warning("Upload at least two video clips.")
        else:
            merge_tmp = Path(tempfile.mkdtemp(prefix="transition_merge_"))

            sources = [
                _save_upload(upload, merge_tmp / f"clip_{i:02d}")
                for i, upload in enumerate(merge_uploads)
            ]

            dst = merge_tmp / "transition_output.mp4"

            try:
                with st.spinner("Combining clips and rendering transitions..."):
                    merge_with_transition(
                        [str(path) for path in sources],
                        str(dst),
                        transition,
                        transition_len,
                    )

                st.success("Clips merged successfully.")
                st.video(str(dst))

                st.download_button(
                    "⬇️ Download merged video",
                    dst.read_bytes(),
                    file_name="merged_transitions.mp4",
                    mime="video/mp4",
                    key="dl_merge",
                )

            except Exception as exc:
                st.error(str(exc))

    st.divider()

    st.markdown("### ✂️ Split Video")
    st.caption("Split one video into separate clips at specified timestamps.")

    split_upload = st.file_uploader(
        "Upload video to split",
        type=["mp4", "mov", "mkv"],
        key="split_upload",
    )

    split_points = st.text_input(
        "Split timestamps in seconds, separated by commas",
        value="10,20",
        key="split_points",
        help="Example: 10,20 creates cuts at 10 and 20 seconds.",
    )

    if st.button(
        "✂️ Split video",
        type="primary",
        key="do_split",
        use_container_width=True,
    ):
        if not split_upload:
            st.warning("Upload a video to split.")
        else:
            try:
                times = [
                    float(value.strip())
                    for value in split_points.split(",")
                    if value.strip()
                ]

                split_tmp = Path(tempfile.mkdtemp(prefix="split_video_"))
                split_src = _save_upload(split_upload, split_tmp)
                outdir = split_tmp / "segments"

                with st.spinner("Splitting video into segments..."):
                    pieces = split_video_at(
                        str(split_src),
                        times,
                        str(outdir),
                    )

                st.success(f"Created {len(pieces)} segments.")

                for i, piece in enumerate(pieces, 1):
                    with st.expander(f"🎞️ Segment {i}"):
                        st.video(piece)

                        st.download_button(
                            f"⬇️ Download segment {i}",
                            Path(piece).read_bytes(),
                            file_name=Path(piece).name,
                            mime="video/mp4",
                            key=f"dl_segment_{i}",
                            use_container_width=True,
                        )

            except Exception as exc:
                st.error(str(exc))


# --------------------------------------------------
# VOICEOVER STUDIO
# --------------------------------------------------

with tab_voice:
    st.markdown("### 🎙️ Voiceover Studio")
    st.caption(
        "Generate speech from text or mix a narration track with an existing video."
    )

    st.markdown("#### 🗣️ Text-to-Speech")

    tts_text = st.text_area(
        "Narration script",
        placeholder="Welcome to Cloud Computing 101...",
        key="tts_text",
    )

    voice_name = st.selectbox(
        "Narrator voice",
        [
            "en-US-AriaNeural",
            "en-US-GuyNeural",
            "en-GB-SoniaNeural",
            "en-IN-NeerjaNeural",
            "en-IN-PrabhatNeural",
        ],
        key="tts_voice",
    )

    voice_rate = st.select_slider(
        "Speaking rate",
        options=["-20%", "-10%", "+0%", "+10%", "+20%"],
        value="+0%",
        key="tts_rate",
    )

    if st.button(
        "🎤 Generate narration",
        type="primary",
        key="do_tts",
        use_container_width=True,
    ):
        if not tts_text.strip():
            st.warning("Enter a narration script first.")
        else:
            voice_tmp = Path(tempfile.mkdtemp(prefix="tts_"))
            audio_dst = voice_tmp / "voiceover.mp3"

            try:
                with st.spinner("Generating narration audio..."):
                    generate_tts(
                        tts_text,
                        str(audio_dst),
                        voice_name,
                        voice_rate,
                    )

                st.success("Narration generated.")
                st.audio(str(audio_dst))

                st.download_button(
                    "⬇️ Download narration audio",
                    audio_dst.read_bytes(),
                    file_name="voiceover.mp3",
                    mime="audio/mpeg",
                    key="dl_tts",
                )

            except Exception as exc:
                st.error(str(exc))

    st.divider()

    st.markdown("#### 🎚️ Mix Voiceover with Video")

    mix_video = st.file_uploader(
        "Upload video",
        type=["mp4", "mov", "mkv"],
        key="mix_video",
    )

    mix_audio = st.file_uploader(
        "Upload narration audio",
        type=["mp3", "wav", "m4a", "aac"],
        key="mix_audio",
    )

    col1, col2 = st.columns(2)

    with col1:
        bg_vol = st.slider(
            "Original video volume",
            0.0,
            1.0,
            0.25,
            0.05,
            key="bg_vol",
        )

    with col2:
        vo_vol = st.slider(
            "Voiceover volume",
            0.0,
            2.0,
            1.0,
            0.05,
            key="vo_vol",
        )

    duck = st.checkbox(
        "Reduce original audio under narration",
        value=True,
        key="voice_duck",
    )

    if st.button(
        "🎧 Mix audio tracks",
        type="primary",
        key="do_mix",
        use_container_width=True,
    ):
        if not mix_video or not mix_audio:
            st.warning("Upload both a video and an audio file.")
        else:
            mix_tmp = Path(tempfile.mkdtemp(prefix="voice_mix_"))
            vp = _save_upload(mix_video, mix_tmp)
            ap = _save_upload(mix_audio, mix_tmp)
            dst = mix_tmp / "voiceover_mix.mp4"

            try:
                with st.spinner("Mixing audio tracks..."):
                    add_voiceover(
                        str(vp),
                        str(ap),
                        str(dst),
                        vo_vol,
                        bg_vol,
                        duck,
                    )

                st.success("Voiceover mixed successfully.")
                st.video(str(dst))

                st.download_button(
                    "⬇️ Download narrated video",
                    dst.read_bytes(),
                    file_name="voiceover_mix.mp4",
                    mime="video/mp4",
                    key="dl_mix",
                )

            except Exception as exc:
                st.error(str(exc))


# --------------------------------------------------
# BACKGROUND REMOVAL
# --------------------------------------------------

with tab_bg:
    st.markdown("### 🪄 Background Removal")
    st.caption(
        "Replace the background with a solid color using frame-by-frame segmentation."
    )

    st.warning(
        "Processing can be slow. Fine details such as hair and moving edges may flicker."
    )

    bg_video = st.file_uploader(
        "Upload video",
        type=["mp4", "mov", "mkv"],
        key="bg_video",
    )

    bg_color = st.color_picker(
        "Replacement background color",
        value="#202020",
        key="bg_color",
    )

    max_width = st.select_slider(
        "Processing resolution",
        options=[480, 640, 800, 960, 1280],
        value=640,
        key="bg_width",
        help="Higher resolutions take longer to process.",
    )

    if st.button(
        "🪄 Remove background",
        type="primary",
        key="do_bg",
        use_container_width=True,
    ):
        if not bg_video:
            st.warning("Upload a video first.")
        else:
            bg_tmp = Path(tempfile.mkdtemp(prefix="remove_bg_"))
            src = _save_upload(bg_video, bg_tmp)
            dst = bg_tmp / "background_removed.mp4"

            try:
                with st.spinner(
                    "Loading the segmentation model and processing video frames..."
                ):
                    remove_video_background(
                        str(src),
                        str(dst),
                        bg_color,
                        max_width,
                    )

                st.success("Background replacement completed.")
                st.video(str(dst))

                st.download_button(
                    "⬇️ Download processed video",
                    dst.read_bytes(),
                    file_name="background_removed.mp4",
                    mime="video/mp4",
                    key="dl_bg",
                )

            except Exception as exc:
                st.error(str(exc))


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.markdown(
    """
    <div style="text-align:center; padding:12px 0 4px 0;">
        <div style="font-weight:750; color:#d8d2ff;">
            NovaCut AI Video Studio
        </div>
        <div style="font-size:0.82rem; color:#8e95ad; margin-top:5px;">
            Prompt-powered editing · FFmpeg rendering · AI-assisted workflows
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
