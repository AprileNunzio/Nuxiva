#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef DistDir
  #define DistDir "..\build\dist\Nuxiva"
#endif
#define AppName "Nuxiva"
#define AppExe "Nuxiva.exe"
#define Publisher "NunzioTech"
#define SiteUrl "https://github.com/AprileNunzio/Nuxiva"

[Setup]
AppId={{6F2C8E41-7B3A-4C1D-9E55-A7E1D0C4B2F9}
AppName={#AppName}
AppVerName={#AppName} {#AppVersion}
AppVersion={#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#SiteUrl}
AppSupportURL={#SiteUrl}/issues
AppUpdatesURL={#SiteUrl}/releases
AppCopyright=Copyright (c) 2026 {#Publisher}
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#Publisher}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
VersionInfoCopyright=Copyright (c) 2026 {#Publisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
PrivilegesRequired=admin
MinVersion=10.0
SetupMutex=NuxivaSetupMutex
OutputDir=..\build\installer
OutputBaseFilename=Nuxiva_Setup
SetupIconFile=..\build\nuxiva.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile=..\..\..\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; Comment: "{#AppName}"
Name: "{autoprograms}\{#AppName}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; Tasks: desktopicon

[InstallDelete]
Type: files; Name: "{userprograms}\NUXIVA Assistente.lnk"
Type: files; Name: "{userdesktop}\NUXIVA Assistente.lnk"
Type: filesandordirs; Name: "{localappdata}\Programs\NUXIVA"
Type: filesandordirs; Name: "{localappdata}\Programs\ATENA"
Type: files; Name: "{userprograms}\ATENA.lnk"
Type: files; Name: "{userdesktop}\ATENA.lnk"
Type: filesandordirs; Name: "{userprograms}\ATENA"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "NUXIVA Assistente"; Flags: deletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "ATENA"; Flags: deletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\ATENA_is1"; Flags: deletekey

[Run]
Filename: "{app}\{#AppExe}"; Parameters: "{code:EnrollmentParameters}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""Nuxiva"" /F"; Flags: runhidden; RunOnceId: "RemoveAutostartTask"
Filename: "{cmd}"; Parameters: "/C reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v ""NUXIVA Assistente"" /f"; Flags: runhidden; RunOnceId: "RemoveLegacyAutostart"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
    Exec(ExpandConstant('{sys}\schtasks.exe'), '/Delete /TN "ATENA" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function EnrollmentParameters(Value: String): String;
var
  EnrollmentFile: String;
begin
  Result := '';
  EnrollmentFile := ExpandConstant('{src}\enroll.json');
  if FileExists(EnrollmentFile) then
    Result := '--enrollment-file "' + EnrollmentFile + '"';
end;
