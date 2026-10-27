$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv }
elseif (Get-Command python -ErrorAction SilentlyContinue) { python -m venv .venv }
else { throw "请先安装 Python 3.10+" }
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path inbox,data,output | Out-Null
Write-Host '初始化完成。运行 .\quick_test.ps1' -ForegroundColor Green
