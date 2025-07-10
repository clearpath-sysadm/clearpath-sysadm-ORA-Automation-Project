<#
.SYNOPSIS
    Copies all Python (.py) files from a directory and its subdirectories
    to a new directory, converting them to text (.txt) files, excluding
    a list of specified folders, and adding a 'py_' prefix.

.DESCRIPTION
    This script is designed to be placed in the root of a project directory.
    It searches for all files with a .py extension within the current directory
    and all of its subdirectories. It specifically excludes a list of folders
    (e.g., 'venv', 'success_files') found in the project root to avoid copying
    unwanted files.

    It then creates a new directory named 'python-files' in the root if it
    doesn't already exist.

    Finally, it copies each found Python file into the 'python-files' directory,
    prefixing the new filename with 'py_' and renaming the extension to .txt.
    This is useful for preparing and organizing code files for tools like NotebookLM.

.EXAMPLE
    PS C:\Projects\ORA_Automation> .\Convert-PyToTxt.ps1

    Place this script in your "ORA_Automation" folder and run it from PowerShell.
    It will create a "C:\Projects\ORA_Automation\python-files" directory and
    populate it with .txt versions of all your project's .py files, named like
    'py_my_script.txt', ignoring the 'venv' and 'success_files' folders.
#>

# --- Configuration ---
# Get the directory where the script is currently running.
# This assumes you will place the script in the root of your "ORA_Automation" project.
$projectRoot = Get-Location

# Define the name of the folder where the .txt files will be stored.
$outputFolderName = "python-files"

# Define the names of the folders to exclude from the search.
# To add more folders, just add them to this list, e.g., @("venv", "success_files", "another_folder")
$foldersToExclude = @("venv", "success_files")

# Define the prefix to add to each new filename.
$filePrefix = "py_"

# --- Setup Paths ---
# Combine the root path and the output folder name to create the full path.
$outputDir = Join-Path -Path $projectRoot -ChildPath $outputFolderName

# --- Script Body ---

# Step 1: Check if the output directory exists. If not, create it.
if (-not (Test-Path -Path $outputDir)) {
    Write-Host "Output directory '$outputDir' not found. Creating it..."
    New-Item -Path $outputDir -ItemType Directory | Out-Null
} else {
    Write-Host "Output directory '$outputDir' already exists."
}

# Step 2: Find all Python files recursively, then filter out the excluded folders.
Write-Host "Searching for all .py files in '$projectRoot'..."
$allPythonFiles = Get-ChildItem -Path $projectRoot -Recurse -Filter "*.py"
$filteredFiles = $allPythonFiles

if ($foldersToExclude.Count -gt 0) {
    Write-Host "Excluding files from the following folders: $($foldersToExclude -join ', ')"
    foreach ($folder in $foldersToExclude) {
        $excludedPath = Join-Path -Path $projectRoot.Path -ChildPath $folder
        # Filter the list, removing files that are in the current excluded directory.
        $filteredFiles = $filteredFiles | Where-Object { $_.FullName -notlike "$excludedPath\*" }
    }
}


# Check if any python files were found after filtering
if ($null -eq $filteredFiles) {
    Write-Warning "No Python (.py) files were found in the specified locations after exclusions."
    # Exit the script cleanly if no files are found.
    return
}

Write-Host "Found $($filteredFiles.Count) Python files. Starting copy process..."

# Step 3: Loop through each found Python file and copy it as a .txt file.
foreach ($file in $filteredFiles) {
    # Create the new file name with the prefix and new .txt extension.
    # $file.BaseName gets the file name without the extension.
    $newFileName = "$($filePrefix)$($file.BaseName).txt"

    # Define the full path for the destination file.
    $destinationFile = Join-Path -Path $outputDir -ChildPath $newFileName

    # Copy the original file to the new destination with the new name.
    # -Force will overwrite the file if it already exists in the destination.
    Copy-Item -Path $file.FullName -Destination $destinationFile -Force

    Write-Host "Copied '$($file.FullName)' to '$($destinationFile)'"
}

Write-Host "Script finished. All Python files have been copied as .txt files with the prefix '$($filePrefix)'."
