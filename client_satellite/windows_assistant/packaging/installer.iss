#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef DistDir
  #define DistDir "..\build\dist\NUXIVA"
#endif

[Setup]
AppId={{6F2C8E41-7B3A-4C1D-9E55-A7E1D0C4B2F9}
AppName=NUXIVA Assistente
AppVersion={#AppVersion}
AppPublisher=NunzioTech
AppPublisherURL=https://github.com/AprileNunzio/NUXIVA
DefaultDirName={localappdata}\Programs\NUXIVA
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\build\installer
OutputBaseFilename=NUXIVA_Assistente_Setup
SetupIconFile=..\build\nuxiva.ico
UninstallDisplayIcon={app}\NUXIVA.exe
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

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\NUXIVA Assistente"; Filename: "{app}\NUXIVA.exe"
Name: "{userdesktop}\NUXIVA Assistente"; Filename: "{app}\NUXIVA.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NUXIVA.exe"; Description: "{cm:LaunchProgram,NUXIVA Assistente}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\NUXIVA.exe"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v ""NUXIVA Assistente"" /f"; Flags: runhidden; RunOnceId: "RemoveAutostart"
