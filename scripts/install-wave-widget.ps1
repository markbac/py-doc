<#
.SYNOPSIS
    Add py-doc's preview widget to Wave Terminal's sidebar, or bring it up to date, when Wave is installed.

.DESCRIPTION
    Wave Terminal (https://www.waveterm.dev/) keeps its sidebar widgets in widgets.json, in its configuration
    folder (~\.config\waveterm). This script adds py-doc's "preview" widget there, or updates it when py-doc's
    definition of it changed, and otherwise says it is up to date. Every other widget and key in widgets.json
    is kept as it is. A widgets.json that cannot be read is left alone, with a note saying why.

    Wave is found on the PATH (wave, wsh), in its usual install folder
    (%LOCALAPPDATA%\Programs\waveterm), through its wsh (%LOCALAPPDATA%\waveterm\Data\bin\wsh.exe), or by its
    configuration folder. When it is not there, the script says so and changes nothing.

    scripts\update.ps1 runs it; -NoWave there skips it. It exits 0 when Wave is not installed, and 1 when
    the widget could not be added.

.PARAMETER Python
    The Python that has py-doc installed (default: the py-doc command on the PATH).

.PARAMETER ConfigDir
    Wave's configuration folder (default: WAVETERM_CONFIG_HOME, else ~\.config\waveterm). Wave counts as
    installed when this folder is named and exists.

.EXAMPLE
    .\scripts\install-wave-widget.ps1
#>
[CmdletBinding()]
param(
    [string]$Python,
    [string]$ConfigDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

function Write-Ok([string]$Text) { Write-Host "    ok    $Text" -ForegroundColor Green }
function Write-Note([string]$Text) { Write-Host "    note  $Text" -ForegroundColor Yellow }

$home_ = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
$local = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $home_ 'AppData\Local' }

# Where Wave keeps widgets.json
$named = [bool]$ConfigDir
if (-not $ConfigDir) {
    $ConfigDir = if ($env:WAVETERM_CONFIG_HOME) { $env:WAVETERM_CONFIG_HOME } else { Join-Path $home_ '.config\waveterm' }
}

# W-41: is Wave there?
$wsh = $null
$found = $null
if ($named) {
    if (Test-Path -LiteralPath $ConfigDir -PathType Container) { $found = "its configuration folder $ConfigDir" }
} else {
    $command = Get-Command wsh -ErrorAction SilentlyContinue
    if ($command) { $wsh = $command.Source }
    $ownWsh = Join-Path $local 'waveterm\Data\bin\wsh.exe'
    if (-not $wsh -and (Test-Path -LiteralPath $ownWsh)) { $wsh = $ownWsh }
    $exe = Join-Path $local 'Programs\waveterm\Wave.exe'
    if (Get-Command wave -ErrorAction SilentlyContinue) { $found = 'wave on the PATH' }
    elseif (Test-Path -LiteralPath $exe) { $found = $exe }
    elseif ($wsh) { $found = $wsh }
    elseif (Test-Path -LiteralPath $ConfigDir -PathType Container) { $found = "its configuration folder $ConfigDir" }
}
if (-not $found) {
    Write-Note "Wave Terminal is not installed, so there is nothing to set up"
    exit 0
}
Write-Ok "Wave Terminal found: $found"

# W-42, W-43: the widget, through py-doc, which keeps every other widget
$arguments = @('wave', 'widget', '--install', '--yes', '--config-dir', $ConfigDir)
if ($Python) {
    $output = & $Python -m py_doc @arguments 2>&1 | ForEach-Object { "$_" }
} elseif (Get-Command py-doc -ErrorAction SilentlyContinue) {
    $output = & py-doc @arguments 2>&1 | ForEach-Object { "$_" }
} else {
    Write-Note "py-doc is not on the PATH, so the widget was not added. Run: py-doc wave widget --install"
    exit 1
}
$status = $LASTEXITCODE
$line = @($output | Where-Object { $_ -match '^(added|updated|up to date|note):' } | Select-Object -Last 1)
if ($status -ne 0) {
    $why = if ($line) { $line[0] -replace '^note:\s*', '' } else { ($output -join ' ').Trim() }
    Write-Note "py-doc's widget was not added: $why"
    exit 1
}
if ($line -and $line[0] -match '^up to date') {
    Write-Ok "py-doc's preview widget is up to date"
} elseif ($line -and $line[0] -match '^updated') {
    Write-Ok "py-doc's preview widget updated, as its definition changed ($(Join-Path $ConfigDir 'widgets.json'))"
} else {
    Write-Ok "py-doc's preview widget added to Wave's sidebar ($(Join-Path $ConfigDir 'widgets.json'))"
}

# W-44: wsh, which opens the preview in a Wave pane
if (-not $named) {
    if (-not $wsh) {
        Write-Note "wsh was not found, so previews open in the browser until it is: start Wave once, and open a new terminal in it"
    } else {
        $answer = & $wsh version 2>&1 | Select-Object -First 1
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "wsh answers ($answer)"
        } else {
            Write-Note "wsh is at $wsh but answers only inside a Wave terminal; py-doc doctor checks it there"
        }
    }
}
exit 0
