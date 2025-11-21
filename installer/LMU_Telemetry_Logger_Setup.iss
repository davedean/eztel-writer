; LMU Telemetry Logger - Inno Setup Installer Script
; This script creates a Windows installer for the LMU Telemetry Logger

#define MyAppName "LMU Telemetry Logger"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "LMU Telemetry Team"
#define MyAppURL "https://github.com/davedean/eztel-writer"
#define MyAppExeName "LMU_Telemetry_Logger.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{8B5F9C2A-1D4E-4F3A-9B2C-7E8D4A5F6C9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Disable license page if no LICENSE file (can be re-enabled when LICENSE is added)
;LicenseFile=..\LICENSE
DisableProgramGroupPage=yes
; Output configuration
OutputDir=output
OutputBaseFilename=LMU_Telemetry_Logger_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
; Architecture
ArchitecturesInstallIn64BitMode=x64
; Uninstall configuration
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Wizard appearance
WizardStyle=modern
; Use default wizard images (embedded in Inno Setup)
; WizardImageFile and WizardSmallImageFile will use defaults if not specified

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start with Windows"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
; Main executable (from dist folder after PyInstaller build)
Source: "..\dist\LMU_Telemetry_Logger\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; All other files from the PyInstaller bundle
Source: "..\dist\LMU_Telemetry_Logger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Documentation
Source: "..\USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: LICENSE file commented out until it exists
;Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
; Default config (only install if doesn't exist to preserve user settings)
Source: "config_default.json"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist

[Dirs]
; Create default output directory in user's Documents folder
; This will be created with proper permissions for the user
Name: "{userdocs}\LMU Telemetry"; Permissions: users-modify

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Open Output Folder"; Filename: "{userdocs}\LMU Telemetry"
Name: "{group}\User Guide"; Filename: "{app}\USER_GUIDE.md"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Optional desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
; Add to Windows startup (if user selected auto-start option)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart
; Store installation info for upgrades and version tracking
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "OutputDir"; ValueData: "{userdocs}\LMU Telemetry"; Flags: uninsdeletekey

[Run]
; Option to launch the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  OutputDirPage: TInputDirWizardPage;
  DataDirLabel: TNewStaticText;

// Function to check if this is an upgrade
function IsUpgrade(): Boolean;
var
  InstallPath: String;
begin
  Result := RegQueryStringValue(HKCU, 'Software\{#MyAppName}', 'InstallPath', InstallPath);
end;

// Function to get existing installation directory
function GetOldInstallPath(Param: String): String;
var
  InstallPath: String;
begin
  if RegQueryStringValue(HKCU, 'Software\{#MyAppName}', 'InstallPath', InstallPath) then
    Result := InstallPath
  else
    Result := '';
end;

// Initialize wizard with custom pages
procedure InitializeWizard;
var
  ExistingOutputDir: String;
begin
  // Create custom page for telemetry output directory selection
  OutputDirPage := CreateInputDirPage(wpSelectDir,
    'Select Telemetry Output Directory',
    'Where should telemetry files be saved?',
    'Select the folder where you want telemetry CSV files to be saved.' + #13#10 +
    'The default location is in your Documents folder for easy access.' + #13#10#13#10 +
    'Click Next to continue.',
    False, '');
  OutputDirPage.Add('Telemetry Output Folder:');

  // Set default value
  if IsUpgrade() then
  begin
    // If upgrading, try to read existing output directory
    if RegQueryStringValue(HKCU, 'Software\{#MyAppName}', 'OutputDir', ExistingOutputDir) then
      OutputDirPage.Values[0] := ExistingOutputDir
    else
      OutputDirPage.Values[0] := ExpandConstant('{userdocs}\LMU Telemetry');
  end
  else
    OutputDirPage.Values[0] := ExpandConstant('{userdocs}\LMU Telemetry');
end;

// Called when "Next" button is clicked
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = OutputDirPage.ID then
  begin
    // Validate that output directory is not empty
    if Trim(OutputDirPage.Values[0]) = '' then
    begin
      MsgBox('Please select a valid output directory.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

// Update config.json with user's chosen output directory
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  ConfigContent: TStringList;
  OutputDir: String;
  I: Integer;
  Line: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigFile := ExpandConstant('{app}\config.json');
    OutputDir := OutputDirPage.Values[0];

    // Replace backslashes with double backslashes for JSON
    StringChangeEx(OutputDir, '\', '\\', True);

    // Read config file
    ConfigContent := TStringList.Create;
    try
      if FileExists(ConfigFile) then
      begin
        ConfigContent.LoadFromFile(ConfigFile);

        // Find and replace the output_dir line
        for I := 0 to ConfigContent.Count - 1 do
        begin
          Line := ConfigContent[I];
          if Pos('"output_dir"', Line) > 0 then
          begin
            // Replace the output_dir value with user's choice
            ConfigContent[I] := '  "output_dir": "' + OutputDir + '",';
            Break;
          end;
        end;

        // Save modified config
        ConfigContent.SaveToFile(ConfigFile);
      end;
    finally
      ConfigContent.Free;
    end;

    // Save output directory to registry for future upgrades
    RegWriteStringValue(HKCU, 'Software\{#MyAppName}', 'OutputDir', OutputDirPage.Values[0]);

    // Create the output directory if it doesn't exist
    if not DirExists(OutputDirPage.Values[0]) then
      CreateDir(OutputDirPage.Values[0]);
  end;
end;

// Custom uninstall confirmation for data preservation
function UninstallDataPrompt(): Boolean;
var
  OutputDir: String;
begin
  // Get output directory from registry
  if RegQueryStringValue(HKCU, 'Software\{#MyAppName}', 'OutputDir', OutputDir) then
  begin
    Result := MsgBox('Do you want to delete your telemetry data and configuration?' + #13#10#13#10 +
                     'Location: ' + OutputDir + #13#10#13#10 +
                     'Click Yes to delete all data, or No to keep it.',
                     mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  end
  else
  begin
    // If we can't find the output dir, ask about default location
    Result := MsgBox('Do you want to delete your configuration file?' + #13#10#13#10 +
                     'Your telemetry data will not be deleted.',
                     mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  end;
end;

// Uninstall event handler
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  OutputDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if UninstallDataPrompt() then
    begin
      // Delete config file
      DeleteFile(ExpandConstant('{app}\config.json'));

      // Delete output directory if we can find it
      if RegQueryStringValue(HKCU, 'Software\{#MyAppName}', 'OutputDir', OutputDir) then
      begin
        if DirExists(OutputDir) then
          DelTree(OutputDir, True, True, True);
      end;
    end;
  end;
end;

// Display message on the finishing page
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    if IsUpgrade() then
      WizardForm.FinishedLabel.Caption :=
        'Setup has finished upgrading {#MyAppName} on your computer.' + #13#10#13#10 +
        'Your configuration and telemetry data have been preserved.' + #13#10#13#10 +
        'Click Finish to exit Setup.'
    else
      WizardForm.FinishedLabel.Caption :=
        'Setup has finished installing {#MyAppName} on your computer.' + #13#10#13#10 +
        'The application will save telemetry files to:' + #13#10 +
        OutputDirPage.Values[0] + #13#10#13#10 +
        'You can change this location later in Settings.' + #13#10#13#10 +
        'Click Finish to exit Setup.';
  end;
end;
