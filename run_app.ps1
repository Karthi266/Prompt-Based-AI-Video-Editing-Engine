$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    throw 'Virtual environment not found. Run .\setup_windows.ps1 first.'
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw 'FFmpeg/ffprobe not found in PATH. Install FFmpeg and reopen PowerShell.'
}
if (-not $env:GEMINI_API_KEY) {
    Write-Host 'Set Gemini API key in this PowerShell window first:' -ForegroundColor Yellow
    Write-Host '$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"'
    throw 'GEMINI_API_KEY is required for prompt parsing.'
}
& '.\.venv\Scripts\python.exe' -m streamlit run app.py
