[Setup]
AppName=QR Attendance Scanner
AppVersion=1.0
AppPublisher=QR Scanner Project
AppPublisherURL=https://example.com
DefaultDirName={commonpf}\QRAttendanceScanner
DefaultGroupName=QR Attendance Scanner
OutputDir=.\dist
OutputBaseFilename=QRScannerSetup
Compression=lz4
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\QR Attendance Scanner\QR Attendance Scanner.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\QR Attendance Scanner\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\QR Attendance Scanner"; Filename: "{app}\QR Attendance Scanner.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\QR Attendance Scanner"; Filename: "{app}\QR Attendance Scanner.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\QR Attendance Scanner"; Filename: "{app}\QR Attendance Scanner.exe"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\QR Attendance Scanner.exe"; Description: "{cm:LaunchProgram,QR Attendance Scanner}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{app}"
