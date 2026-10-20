# 🎬 Prompt-Based AI Video Editing Engine

**An AI-assisted video editing application that transforms raw video footage into polished content using natural-language prompts, automatic subtitles, visual overlays, speed control, transitions, and audio editing tools.**

## 📌 Overview

The **Prompt-Based AI Video Editing Engine** is a Python-based video editing application designed to simplify common video editing tasks. Instead of manually performing every editing operation, users can describe the changes they want in natural language and use the application's editing tools to process their videos.

The application combines AI-assisted prompt interpretation with FFmpeg-based video processing and additional modules for subtitles, animations, voiceovers, and background removal. It provides an interactive interface built with Streamlit.

The user interface is presented as **NovaCut AI Video Studio**.

## ✨ Features

### 1. 🤖 Prompt-Based Video Editing
- Accepts natural-language editing instructions.
- Interprets editing intent through the project's prompt-processing module.
- Uses FFmpeg to apply supported video editing operations.
- Simplifies video editing through an interactive interface.

### 2. 📝 Automatic Subtitle Generation
- Generates subtitles from speech using OpenAI Whisper.
- Supports subtitle generation for compatible input videos.
- Burns subtitles directly into the video using FFmpeg.

### 3. ✂️ Silence Removal
- Detects silent portions of video audio.
- Helps remove unnecessary pauses.
- Uses FFmpeg-based processing to create a more continuous video.

### 4. 🖼️ Image Overlays and Branding
- Adds images or graphics over video footage.
- Supports visual elements such as logos and branding assets.
- Provides an overlay workflow through the Streamlit interface.

### 5. ⚡ Speed Control
- Changes video playback speed.
- Supports speed-ramp processing through the advanced editing module.
- Helps create faster or slower visual sequences.

### 6. 🎞️ Transitions and Clip Editing
- Merges video clips.
- Applies supported transitions between clips.
- Splits videos at specified timestamps.

### 7. 🎙️ Voiceover Studio
- Generates text-to-speech audio using Edge TTS.
- Adds voiceovers to video.
- Supports audio mixing workflows for combining narration with existing video audio.

### 8. 🎭 Background Removal
- Provides a video background-removal workflow using the `rembg` ecosystem.
- Processes compatible video frames to remove backgrounds.
- Depends on the installed models, runtime, and processing environment.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Streamlit | Interactive web interface |
| FFmpeg | Video and audio processing |
| OpenAI Whisper | Speech recognition and subtitle generation |
| Google Gen AI SDK | AI integration, where configured |
| Edge TTS | Text-to-speech voice generation |
| Pillow | Image processing |
| rembg | Background removal |
| ONNX Runtime | Machine-learning inference support |

## 🏗️ Project Architecture

The project is organized into feature-specific Python modules.

```text
Prompt_Based_Video_Editor/
│
├── app.py
│   └── Streamlit user interface and feature workflows
│
├── engine.py
│   └── Prompt interpretation and core video editing engine
│
├── ai_features.py
│   └── Automatic subtitles, silence detection,
│       and subtitle burning
│
├── animation_engine.py
│   └── Image overlay and animation-related processing
│
├── advanced_features.py
│   └── Speed ramps, transitions, clip splitting,
│       voiceovers, audio mixing, and background removal
│
├── requirements.txt
│   └── Python dependencies
│
├── .gitignore
│   └── Files excluded from version control
│
└── README.md
    └── Project documentation
```

*Note: This structure represents the main modules used by the application. Add any additional files or folders that exist in your actual repository.*

## ⚙️ Installation and Setup

### Prerequisites

Install the following before running the application:

- Python 3.10 or another version supported by your dependencies.
- FFmpeg, with its executable available on your system `PATH`.
- Git, if you want to clone the repository.
- Required API credentials if your configured AI functionality uses an external API.

### Step 1: Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_PROJECT_DIRECTORY>
```

Replace the placeholders with your actual repository URL and directory name.

### Step 2: Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use an approved environment-activation method for your machine rather than changing system security settings unnecessarily.

### Step 3: Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Verify FFmpeg

Check whether FFmpeg is available:

```powershell
ffmpeg -version
```

If the command is not recognized, install FFmpeg and add its `bin` directory to your system `PATH`. Restart the terminal after changing the environment variables.

### Step 5: Configure API credentials

If your implementation uses an external AI API, configure the required API key using the method expected by your code or environment configuration.

**Security note:** Never commit API keys, passwords, or private credentials to GitHub. Use environment variables or a local secrets file excluded through `.gitignore`.

### Step 6: Run the application

From the directory containing `app.py`, execute:

```powershell
python -m streamlit run app.py
```

Streamlit will provide a local URL, typically:

```text
http://localhost:8501
```

Open that address in your browser to access the application.

## 🚀 How to Use

1. Launch the Streamlit application.
2. Upload a supported input video.
3. Enter a natural-language editing prompt in the prompt-based editing section.
4. Configure the available processing options, such as silence removal or subtitle generation.
5. Run the editing workflow and review the generated output.
6. Use the additional editing sections to add image overlays, change speed, merge or split clips, generate voiceovers, or remove backgrounds.
7. Review and save the processed video produced by the selected workflow.

*The exact controls, supported prompt instructions, file formats, and output options depend on the current implementation.*

## 📂 Supported Inputs and Outputs

The application relies on FFmpeg for media processing, so supported formats depend on the installed FFmpeg build and the specific processing workflow.

Examples of commonly supported media formats include:

- **Video:** MP4, MOV, AVI, and other FFmpeg-compatible formats.
- **Audio:** WAV, MP3, AAC, and other supported audio formats.
- **Images:** PNG, JPEG, and other formats supported by the image-processing workflow.

Some operations may require specific codecs or formats. Test your input media with the relevant feature before processing large files.

## 🧠 How It Works

The application follows a modular processing workflow:

```text
User Uploads Video
        ↓
User Enters Editing Prompt
        ↓
Prompt Interpretation
        ↓
Editing Operation Selection
        ↓
FFmpeg / AI Processing Modules
        ↓
Subtitle, Audio, or Visual Processing
        ↓
Processed Video Output
```

The prompt-processing module interprets the requested edits, while the relevant feature modules perform the corresponding operations. Whisper handles speech recognition for subtitles, and other optional components provide text-to-speech and background-removal capabilities.

Not every workflow requires every module; the processing path depends on the selected feature.

## 🔐 Security and Privacy

- Keep API credentials out of source control.
- Avoid uploading confidential or sensitive videos to external AI services without authorization.
- Review the privacy policies of any external services used by your configuration.
- Store temporary files and generated videos securely.
- Remove temporary media files when they are no longer needed, where appropriate.

## ⚠️ Limitations

- Processing time depends on video duration, resolution, available hardware, and the selected operations.
- Whisper and background-removal workflows may require substantial CPU, memory, or GPU resources.
- External AI functionality may require valid credentials, network access, and applicable API quotas.
- Results depend on the quality of the input video and audio.
- Advanced effects and supported prompt instructions depend on the capabilities implemented in the project.

## 🤝 Contributing

Contributions and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement and test your changes.
4. Commit your changes with a descriptive message.
5. Open a pull request describing the improvement.

## 🧪 Troubleshooting

**Streamlit command not found**

```powershell
python -m pip install streamlit
python -m streamlit run app.py
```

**FFmpeg command not found**

Check the installation and confirm that FFmpeg's `bin` directory is included in `PATH`.

**Python dependency errors**

Activate the project's virtual environment and reinstall the dependencies:

```powershell
python -m pip install -r requirements.txt
```

**Subtitle generation errors**

Check that Whisper is installed, the input contains usable audio, and the required model can be loaded.

**Background-removal errors**

Verify that the background-removal dependencies and compatible model files are installed. This feature may consume considerable system resources.

**AI API errors**

Check your credentials, network connection, API configuration, and usage limits.
