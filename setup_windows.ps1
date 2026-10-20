$ErrorActionPreference = 'Stop'
Write-Host '=== Prompt-Based AI Video Editor setup ===' -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher not found. Install Python 3.11 x64 and enable Add Python to PATH, then reopen PowerShell.'
}
py -3.11 --version
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Write-Host 'FFmpeg/ffprobe was not found. Install it first with:' -ForegroundColor Yellow
    Write-Host 'winget install --id Gyan.FFmpeg.Shared --exact'
    throw 'Install FFmpeg, reopen PowerShell, then run this script again.'
}
ffmpeg -version | Select-Object -First 1
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    py -3.11 -m venv .venv
}
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip setuptools wheel
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
Write-Host ''
Write-Host 'Setup complete.' -ForegroundColor Green
Write-Host 'Set your API key and start the app using:' -ForegroundColor Cyan
Write-Host '$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"'
Write-Host '$env:GEMINI_MODEL="gemini-2.5-flash"'
Write-Host '$env:REPLICATE_API_TOKEN="YOUR_REPLICATE_TOKEN"  # optional hosted AI models'
Write-Host '.\.venv\Scripts\Activate.ps1'
Write-Host 'streamlit run app.py'
