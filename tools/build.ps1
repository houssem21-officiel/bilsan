# يبني Bilsan.exe ثم ملفات التثبيت (واحد لكل حاسوب). يعمل على Windows (GitHub Actions).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$ver = (Get-Content VERSION).Trim()
Write-Host "== Bilsan $ver"

python -m pip install --upgrade pip
python -m pip install flask waitress pillow pyinstaller

python tools/make_configs.py build/variants.txt
pyinstaller --noconfirm --clean --noconsole --onedir --name Bilsan `
  --icon static\bilsan.ico --add-data "static;static" `
  --hidden-import waitress --collect-submodules waitress launcher.py
if (!(Test-Path dist\Bilsan\Bilsan.exe)) { throw "PyInstaller failed" }

# اختبار سريع: البرنامج المبني يشتغل ويجيب على صفحة الدخول
$env:BILSAN_DATA = "$PWD\build\smoke"
New-Item -ItemType Directory -Force $env:BILSAN_DATA | Out-Null
$p = Start-Process dist\Bilsan\Bilsan.exe -ArgumentList "--background" -PassThru
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep 1
  try { $r = Invoke-WebRequest http://127.0.0.1:5000/login -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { $ok = $true; break } } catch {}
}
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Remove-Item Env:\BILSAN_DATA
if (!$ok) { Get-Content build\smoke\bilsan.log -ErrorAction SilentlyContinue; throw "smoke test failed" }
Write-Host "smoke test OK"

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (!(Test-Path $iscc)) { choco install innosetup -y --no-progress; }
foreach ($v in Get-Content build\variants.txt) {
  & $iscc /Qp "/DVariant=$v" "/DAppVer=$ver" "/DCfgDir=..\build\cfg\$v" installer\bilsan.iss
  if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed for $v" }
}
Get-ChildItem dist\installers | Format-Table Name, Length
