#define MyAppName "RND DEMO"
#define MyAppPublisher "Vogel Consultoria"
#ifndef MyAppVersion
  #define MyAppVersion "0000.00.00.00"
#endif

[Setup]
AppId={{5C6DA3C2-3B49-4E66-A45A-DFD3F9B814D2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\RND DEMO
DefaultGroupName=RND DEMO
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=setup_rnd_demo
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
UninstallDisplayName=RND DEMO
Uninstallable=yes
ArchitecturesAllowed=x64compatible
SetupIconFile=..\imagenes\vogel_consultoria_oficial.ico
UninstallDisplayIcon={app}\RND Demo.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\RND Demo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\RND DEMO"; Filename: "{app}\RND Demo.exe"; WorkingDir: "{app}"; IconFilename: "{app}\RND Demo.exe"
Name: "{autodesktop}\RND DEMO"; Filename: "{app}\RND Demo.exe"; WorkingDir: "{app}"; IconFilename: "{app}\RND Demo.exe"; Tasks: desktopicon
Name: "{autoprograms}\Desinstalar RND DEMO"; Filename: "{uninstallexe}"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo de RND DEMO en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Run]
Filename: "{app}\RND Demo.exe"; Description: "Abrir RND DEMO"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: files; Name: "{app}\sistema.db"
Type: files; Name: "{app}\rnd_crash.log"
