param([string]$Destination = "$PSScriptRoot/dist")
$ErrorActionPreference = 'Stop'
$previousPath=$env:Path
$env:Path=(($env:Path -split ';' | Where-Object {$_ -notmatch '[\\/]poppler[\\/]'}) -join ';')
Push-Location $PSScriptRoot
try {
 python -m PyInstaller --clean --noconfirm --onefile --windowed --name AwardStudio --version-file assets/version.txt --icon assets/awardstudio.ico --add-data "assets/awardstudio.ico;assets" --distpath $Destination --add-data "assets/template.psd;assets" --add-data "assets/paper.jpg;assets" --add-data "scripts/render.jsx;scripts" --collect-data pypinyin --exclude-module numpy --exclude-module pandas --exclude-module scipy --exclude-module matplotlib --exclude-module IPython --exclude-module lxml --exclude-module cv2 --exclude-module PyQt5 --add-data "web;web" scripts/studio.py
 if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally { Pop-Location; $env:Path=$previousPath }





