$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = ".\.venv\Scripts\python.exe"
if (!(Test-Path $python)) { throw "先执行 setup_windows.ps1" }
& $python news_factory.py check "samples\example.json"
if ($LASTEXITCODE -ne 0) { exit 1 }
& $python news_factory.py import "samples\example.json"
if ($LASTEXITCODE -ne 0) { exit 1 }
& $python news_factory.py report --date "2026-10-27"
if ($LASTEXITCODE -ne 0) { exit 1 }
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
  & $python news_factory.py render --date "2026-10-27" --demo
  if ($LASTEXITCODE -ne 0) { exit 1 }
} else { Write-Host "无 FFmpeg，跳过视频。请安装 FFmpeg 后重试。" }
Write-Host '完成：output\2026-10-27\review.html' -ForegroundColor Green
