; ملف تثبيت برنامج بيلسان
; يُبنى عدة مرات: مرة لكل حاسوب (Variant) مع ملف إعداده الخاص.
;   ISCC bilsan.iss /DVariant=Central /DCfgDir=..\build\cfg\Central /DAppVer=18.0

#ifndef Variant
  #define Variant "Setup"
#endif
#ifndef AppVer
  #define AppVer "18.0"
#endif
#ifndef CfgDir
  #define CfgDir "..\build\cfg\" + Variant
#endif
#define Data "{commonappdata}\Bilsan"

[Setup]
AppId={{3E86114A-2D43-483A-8EE8-F9C5F2CCE2BE}
AppName=Bilsan
AppVerName=Bilsan {#AppVer}
AppVersion={#AppVer}
AppPublisher=Bilsan
DefaultDirName={autopf}\Bilsan
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=..\dist\installers
OutputBaseFilename=Bilsan-{#Variant}
SetupIconFile=..\static\bilsan.ico
UninstallDisplayIcon={app}\Bilsan.exe
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
CloseApplications=force

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Dirs]
; البيانات: كل مستخدمي الحاسوب يستطيعون الكتابة فيها
Name: "{#Data}"; Permissions: users-modify

[Files]
Source: "..\dist\Bilsan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; ملف الإعداد يُنسخ فقط في التثبيت الأول (حاسوب بلا بيانات)، فالتحديث لا يغيّر شيئًا
Source: "{#CfgDir}\*"; DestDir: "{#Data}"; Flags: onlyifdoesntexist; Check: IsFirstInstall

[Icons]
Name: "{commondesktop}\Bilsan"; Filename: "{app}\Bilsan.exe"; IconFilename: "{app}\Bilsan.exe"
Name: "{commonprograms}\Bilsan"; Filename: "{app}\Bilsan.exe"
; يعمل في الخلفية عند تشغيل الحاسوب حتى تبقى المزامنة شغالة
Name: "{commonstartup}\Bilsan"; Filename: "{app}\Bilsan.exe"; Parameters: "--background"

[Run]
#if Variant == "Central"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Bilsan"""; Flags: runhidden
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Bilsan"" dir=in action=allow protocol=TCP localport=5000"; Flags: runhidden
#endif
Filename: "{app}\Bilsan.exe"; Description: "Open Bilsan"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im Bilsan.exe"; Flags: runhidden; RunOnceId: "KillBilsan"

[Code]
function IsFirstInstall: Boolean;
begin
  Result := not FileExists(ExpandConstant('{#Data}\bilsan.db'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im Bilsan.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Sleep(800);
  Result := '';
end;
