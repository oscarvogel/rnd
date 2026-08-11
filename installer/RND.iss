#define AppName "RND"
#define AppVersion "2026.8.11.1"
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
SetupIconFile=..\imagenes\vogel_consultoria_oficial.ico
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

[Dirs]
Name: "{commonappdata}\RND"; Permissions: users-readexec

[InstallDelete]
; Eliminar el tema activo antes de copiarlo evita conservar un QSS obsoleto
; de una instalacion anterior aunque cambien marcas de tiempo o atributos.
Type: files; Name: "{app}\temas\vogel2026.qss"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\PyQt5"
Type: filesandordirs; Name: "{app}\numpy"
Type: filesandordirs; Name: "{app}\pandas"
Type: filesandordirs; Name: "{app}\scipy"
Type: filesandordirs; Name: "{app}\PIL"
Type: filesandordirs; Name: "{app}\fitz"
Type: filesandordirs; Name: "{app}\pdfminer"
Type: filesandordirs; Name: "{app}\pymongo"
Type: filesandordirs; Name: "{app}\cryptography"
Type: files; Name: "{app}\*.dll"
Type: files; Name: "{app}\*.pyd"
Type: files; Name: "{app}\*.zip"

[Files]
Source: "..\dist\main\*"; DestDir: "{app}"; Excludes: "sistema.ini,rnd.ini"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\main\sistema.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "..\dist\main\rnd.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[INI]
Filename: "{app}\sistema.ini"; Section: "param"; Key: "InicioSistema"; String: "{app}\"
Filename: "{app}\sistema.ini"; Section: "param"; Key: "icono"; String: "vogel_consultoria_oficial.ico"
Filename: "{app}\sistema.ini"; Section: "param"; Key: "logo"; String: "vogel_consultoria_oficial.png"
Filename: "{app}\rnd.ini"; Section: "param"; Key: "InicioSistema"; String: "{app}\"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Parameters: "-i ""{app}"" -a ""sistema.ini"""; WorkingDir: "{app}"; IconFilename: "{app}\imagenes\vogel_consultoria_oficial.ico"; AppUserModelID: "VogelConsultoria.RND"
Name: "{autoprograms}\{#AppName}\Configurar conexión MySQL"; Filename: "{app}\{#AppExeName}"; Parameters: "--edit-db-connection -i ""{app}"" -a ""sistema.ini"""; WorkingDir: "{app}"; IconFilename: "{app}\imagenes\vogel_consultoria_oficial.ico"; AppUserModelID: "VogelConsultoria.RND"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Parameters: "-i ""{app}"" -a ""sistema.ini"""; WorkingDir: "{app}"; IconFilename: "{app}\imagenes\vogel_consultoria_oficial.ico"; AppUserModelID: "VogelConsultoria.RND"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Parameters: "-i ""{app}"" -a ""sistema.ini"""; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
function NormalizeInstallDir(const Value: String): String;
begin
  Result := RemoveBackslashUnlessRoot(Value);
end;

function RequiredInstallDir(): String;
begin
  Result := NormalizeInstallDir('C:\RND');
end;

function InitializeSetup(): Boolean;
var
  RequestedDir: String;
begin
  RequestedDir := ExpandConstant('{param:DIR|}');
  Result := (RequestedDir = '') or
    (CompareText(NormalizeInstallDir(RequestedDir), RequiredInstallDir()) = 0);

  if not Result then
    SuppressibleMsgBox(
      'RND solo puede instalarse en C:\RND.',
      mbError,
      MB_OK,
      IDOK);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if CompareText(NormalizeInstallDir(WizardDirValue()), RequiredInstallDir()) <> 0 then
    Result := 'El destino de RND debe ser C:\RND.'
  else
    Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  CredentialDir: String;
  Params: String;
begin
  if CurStep = ssPostInstall then
  begin
    CredentialDir := ExpandConstant('{commonappdata}\RND');
    Params := '"' + CredentialDir +
      '" /inheritance:r /grant:r ' +
      '"*S-1-5-18:(OI)(CI)(F)" ' +
      '"*S-1-5-32-544:(OI)(CI)(F)" ' +
      '"*S-1-5-32-545:(OI)(CI)(RX)"';

    if (not Exec(
      ExpandConstant('{sys}\icacls.exe'),
      Params,
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode)) or (ResultCode <> 0) then
      RaiseException('No se pudieron proteger los datos compartidos de RND.');
  end;
end;
