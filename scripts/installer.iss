[Setup]
AppName=CLIPFORGE AI
AppVersion=1.0
DefaultDirName={autopf}\CLIPFORGE AI
DefaultGroupName=CLIPFORGE AI
OutputDir=..\dist
OutputBaseFilename=CLIPFORGE_AI_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "..\dist\CLIPFORGE_AI\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
[Icons]
Name: "{group}\CLIPFORGE AI"; Filename: "{app}\CLIPFORGE_AI.exe"
Name: "{autodesktop}\CLIPFORGE AI"; Filename: "{app}\CLIPFORGE_AI.exe"
[Run]
Filename: "{app}\CLIPFORGE_AI.exe"; Description: "Launch CLIPFORGE AI"; Flags: nowait postinstall skipifsilent
