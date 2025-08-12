# Revised PowerShell Script to Copy Python Files as Text

<#
.SYNOPSIS
    Copies only Python (.py) files from the 'src' and 'config' folders (and their subfolders)
    to a single 'txt' folder in the project root, renaming them with a .txt extension.

.DESCRIPTION
    This script is designed to be run from the root directory of your project.
    It performs the following actions:
    1. Checks if a 'txt' folder exists in the project root. If not, it creates it.
    2. (Optional) Prompts to clear the 'txt' folder if it exists, to ensure a clean copy.
    3. Recursively finds all files within the 'src' and 'config' directories.
    4. Explicitly filters these files to include only those with a '.py' extension.
    5. For each found Python file, it copies the file to the 'txt' folder.
    6. During the copy, it renames the file to have a '.txt' extension while retaining its original base name.

.NOTES
    - Ensure you run this script from the root directory of your project where 'src' and 'config' folders reside.
    - If you choose not to clear the 'txt' folder, existing files with the same name will be overwritten.
#>

# Define the root directory where the script is being run
$ProjectRoot = $PSScriptRoot

# Define the target directory for the text files
$TargetTxtFolder = Join-Path -Path $ProjectRoot -ChildPath "txt"

Write-Host "Starting script to copy Python files as text..."
Write-Host "Project Root: $ProjectRoot"
Write-Host "Target Text Folder: $TargetTxtFolder"

# 1. Create the 'txt' folder if it doesn't exist
if (-not (Test-Path -Path $TargetTxtFolder -PathType Container)) {
    Write-Host "Creating target folder: $TargetTxtFolder"
    try {
        New-Item -ItemType Directory -Path $TargetTxtFolder -Force | Out-Null
        Write-Host "Folder created successfully."
    }
    catch {
        Write-Error "Failed to create folder '$TargetTxtFolder'. Error: $($_.Exception.Message)"
        exit 1 # Exit script if folder creation fails
    }
} else {
    Write-Host "Target folder '$TargetTxtFolder' already exists."

    # Optional: Prompt to clear the folder for a clean copy
    $ConfirmClear = Read-Host "The 'txt' folder already exists. Do you want to clear its contents before copying new files? (Y/N)"
    if ($ConfirmClear -eq "Y" -or $ConfirmClear -eq "y") {
        Write-Host "Clearing contents of '$TargetTxtFolder'..."
        try {
            Remove-Item -Path (Join-Path -Path $TargetTxtFolder -ChildPath "*") -Recurse -Force -ErrorAction Stop
            Write-Host "Contents cleared."
        }
        catch {
            Write-Error "Failed to clear contents of '$TargetTxtFolder'. Error: $($_.Exception.Message)"
            exit 1 # Exit script if clearing fails
        }
    } else {
        Write-Host "Contents of 'txt' folder will not be cleared. Existing files may be overwritten."
    }
}

# Define the source folders to process
$SourceFolders = @(
    (Join-Path -Path $ProjectRoot -ChildPath "src"),
    (Join-Path -Path $ProjectRoot -ChildPath "config")
)

# Filter out any source folders that don't exist, to prevent errors
$ExistingSourceFolders = $SourceFolders | Where-Object { Test-Path -Path $_ -PathType Container }

if ($ExistingSourceFolders.Count -eq 0) {
    Write-Error "Neither 'src' nor 'config' folders were found in the project root. Please ensure you are running the script from the correct directory."
    exit 1
}

Write-Host "Processing Python files from: $($ExistingSourceFolders -join ', ') and their subfolders..."

# 2. Get all files recursively from the specified source folders,
#    then explicitly filter for .py files. This is more robust.
$PythonFiles = Get-ChildItem -Path $ExistingSourceFolders -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Extension -eq ".py" }

if ($PythonFiles.Count -eq 0) {
    Write-Warning "No Python files found in 'src' or 'config' directories. Please check your folder structure."
} else {
    foreach ($File in $PythonFiles) {
        $NewFileName = "$($File.BaseName).txt"
        $DestinationPath = Join-Path -Path $TargetTxtFolder -ChildPath $NewFileName

        Write-Host "Copying '$($File.FullName)' to '$NewFileName'..."
        try {
            Copy-Item -Path $File.FullName -Destination $DestinationPath -Force
        }
        catch {
            Write-Error "Failed to copy '$($File.FullName)'. Error: $($_.Exception.Message)"
        }
    }
}

Write-Host "Script execution completed."
