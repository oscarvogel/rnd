#define AppName "RND"
#define AppVersion "2026.8.6.2"
#define AppPublisher "Jose Oscar Vogel"
#define AppExeName "main.exe"

[Setup]
AppId={{2F4B6F16-7E5A-46B1-9B4D-7C55620B2711}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName=C:\RND
DefaultGroupName={#AppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
UsePreviousAppDir=no
OutputDir=..\dist\installer
OutputBaseFilename=setup_rnd
SetupIconFile=..\imagenes\LogoS-01.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\PyQt5"
Type: filesandordirs; Name: "{app}\numpy"
Type: filesandordirs; Name: "{app}\pandas"
Type: filesandordirs; Name: "{app}\scipy"
Type: filesandordirs; Name: "{app}\PIL"
Type: filesandordirs; Name: "{app}\fitz"
Type: filesandordirs; Name: "{app}\pdfminer"
Type: filesandordirs; Name: "{app}\pymongo"
; Type: filesandordirs; Name: "{app}\cryptography" ; COMENTADO 2026-08-05: cryptography lo necesita pymysql para el handshake
; de auth con MySQL 8 (caching_sha2_password). Borrarlo rompe la conexion
; a la DB con un 1045 "Access denied" enganoso. Si se quiere limpiar
; una version vieja, hacerlo manualmente antes de actualizar.
Type: files; Name: "{app}\*.dll"
Type: files; Name: "{app}\*.pyd"
Type: files; Name: "{app}\*.zip"

[Files]
Source: "..\dist\main\*"; DestDir: "{app}"; Excludes: "sistema.ini,rnd.ini"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\main\sistema.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "..\dist\main\rnd.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[INI]
Filename: "{app}\sistema.ini"; Section: "param"; Key: "InicioSistema"; String: "{app}\"
Filename: "{app}\rnd.ini"; Section: "param"; Key: "InicioSistema"; String: "{app}\"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Parameters: "-i ""{app}"" -a ""sistema.ini"""; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Parameters: "-i ""{app}"" -a ""sistema.ini"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Parameters: "-i ""{app}"" -a ""sistema.ini"""; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
