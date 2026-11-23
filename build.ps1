param([string]$Destination = "$PSScriptRoot/dist")
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
 python -m PyInstaller --clean --noconfirm --onefile --windowed --name AwardStudio --distpath $Destination --add-data "assets/template.psd;assets" --add-data "assets/paper.jpg;assets" --add-data "scripts/render.jsx;scripts" --collect-data pypinyin --exclude-module numpy --exclude-module pandas --exclude-module scipy --exclude-module matplotlib --exclude-module IPython --exclude-module lxml --exclude-module cv2 --exclude-module PyQt5 --exclude-module PySide6 scripts/studio.py
 if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally { Pop-Location }

