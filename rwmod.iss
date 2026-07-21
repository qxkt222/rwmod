[Setup]
AppName=rwmod
AppVersion=0.4.0
AppPublisher=qxkt222
DefaultDirName={commonpf}\rwmod
DefaultGroupName=rwmod
OutputDir=dist
OutputBaseFilename=rwmod_setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=rwmod RimWorld Mod Manager
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\rwmod.exe"; DestDir: "{app}"
Source: "steamcmd\*.*"; DestDir: "{app}\steamcmd"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{commondesktop}\rwmod"; Filename: "{app}\rwmod.exe"; Parameters: "web"; WorkingDir: "{app}"
Name: "{group}\rwmod"; Filename: "{app}\rwmod.exe"; Parameters: "web"; WorkingDir: "{app}"
Name: "{group}\Uninstall rwmod"; Filename: "{uninstallexe}"
