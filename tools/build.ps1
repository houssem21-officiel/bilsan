# يبني Bilsan.exe ثم ملفات التثبيت (واحد لكل حاسوب). يعمل على Windows (GitHub Actions).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$ver = (Get-Content VERSION).Trim()
Write-Host "== Bilsan $ver"

python -m pip install --upgrade pip
python -m pip install flask waitress pillow pyinstaller

python tools/make_configs.py build/variants.txt
pyinstaller --noconfirm --clean --noconsole --onedir --name Bilsan `
  --icon static\bilsan.ico --add-data "static;static" --add-data "VERSION;." --add-data "i18n_dict.json;." `
  --hidden-import waitress --collect-submodules waitress launcher.py
if (!(Test-Path dist\Bilsan\Bilsan.exe)) { throw "PyInstaller failed" }
$dict = Get-ChildItem -Recurse dist\Bilsan -Filter i18n_dict.json | Select-Object -First 1
if (!$dict) { throw "i18n_dict.json missing" }
Write-Host "translations: $($dict.FullName)"
# ملف التحديث التلقائي (يوضع مع الحاسوب المركزي)
New-Item -ItemType Directory -Force dist\update | Out-Null
Compress-Archive -Path dist\Bilsan\* -DestinationPath "dist\update\Bilsan-update-$ver.zip" -Force

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

# اختبار التحديث التلقائي: مركزي بنسخة أحدث + حاسوب فرع بنسخة أقدم
$T = "$PWD\build\uptest"
New-Item -ItemType Directory -Force "$T\c\update", "$T\n" | Out-Null
Copy-Item -Recurse dist\Bilsan "$T\n\app"
Copy-Item "dist\update\Bilsan-update-$ver.zip" "$T\c\update\Bilsan-update-99.0.zip"
'{"sync_key":"kkkkkkkkkkkkkkkkkkkkkkkk","devices":[{"username":"d1","full_name":"t","branch_id":1,"role":"reception","slot":101,"password":"1111"}]}' | Out-File -Encoding ascii "$T\c\seed.json"
'{"branch_id":1,"slot":101,"device":"d1","central_url":"http://127.0.0.1:5000","key":"kkkkkkkkkkkkkkkkkkkkkkkk"}' | Out-File -Encoding ascii "$T\n\node.json"
$env:BILSAN_DATA = "$T\c"; $env:BILSAN_VERSION = "99.0"; $env:BILSAN_PORT = "5000"
$pc = Start-Process dist\Bilsan\Bilsan.exe -ArgumentList "--background" -PassThru
Start-Sleep 8
$env:BILSAN_DATA = "$T\n"; $env:BILSAN_VERSION = "1.0"; $env:BILSAN_PORT = "5001"; $env:BILSAN_UPDATE_EVERY = "3"
# نشغّله من داخل مجلده (كما يفعل اختصار سطح المكتب) للتأكد أن التحديث يستبدل المجلد رغم ذلك
$pn = Start-Process "$T\n\app\Bilsan.exe" -ArgumentList "--background" -WorkingDirectory "$T\n\app" -PassThru
Remove-Item Env:\BILSAN_DATA, Env:\BILSAN_VERSION, Env:\BILSAN_PORT, Env:\BILSAN_UPDATE_EVERY
$up = $false
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep 1
  if ((Test-Path "$T\n\app_old\Bilsan.exe") -and (Test-Path "$T\n\app\Bilsan.exe")) {
    try { $r = Invoke-WebRequest http://127.0.0.1:5001/login -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {}
  }
}
Get-Process Bilsan -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Content "$T\n\bilsan.log" -ErrorAction SilentlyContinue | Select-Object -Last 15
Get-Content "$T\n\update_result.txt" -ErrorAction SilentlyContinue
if (!$up) { throw "auto-update test failed" }
if (!(Select-String -Path "$T\n\update_result.txt" -Pattern "ok" -Quiet)) { throw "auto-update did not replace the app" }
Write-Host "auto-update test OK"

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (!(Test-Path $iscc)) { choco install innosetup -y --no-progress; }
foreach ($v in Get-Content build\variants.txt) {
  & $iscc /Qp "/DVariant=$v" "/DAppVer=$ver" "/DCfgDir=..\build\cfg\$v" installer\bilsan.iss
  if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed for $v" }
}
Get-ChildItem dist\installers | Format-Table Name, Length
