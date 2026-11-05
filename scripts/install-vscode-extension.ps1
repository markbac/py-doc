<#
.SYNOPSIS
    Install py-doc's VS Code extension from this checkout, or update it when it changed.

.DESCRIPTION
    Finds VS Code's command line (code). When there is none, it says so and does nothing. Otherwise it
    builds the extension in editors/vscode and installs it into VS Code when:

      - it is not installed, or
      - the installed version is not the one in editors/vscode/package.json, or
      - a file of the extension changed since this script last installed it (its hash is kept in
        .py-doc/vscode-extension.sha256), or
      - -Force is given.

    Building needs Node.js (npm). The build runs npm ci and @vscode/vsce in editors/vscode, and the
    .vsix it makes is deleted once installed. update.ps1 runs this script; it can also run on its own.

    Exit status 0 when the extension is installed and up to date, or VS Code is not there; 1 when it
    could not be built or installed, with the reason.

.PARAMETER Code
    VS Code's command line, when it is not on the PATH or in its usual place, such as
    "C:\Program Files\Microsoft VS Code\bin\code.cmd".

.PARAMETER Force
    Build and install the extension even when it is up to date.

.PARAMETER StateFile
    Where the hash of the installed extension's files is kept. The default is
    .py-doc/vscode-extension.sha256 in this checkout.

.EXAMPLE
    .\scripts\install-vscode-extension.ps1
.EXAMPLE
    .\scripts\install-vscode-extension.ps1 -Force
#>
[CmdletBinding()]
param(
    [string]$Code,
    [switch]$Force,
    [string]$StateFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'  # programs report failure through their exit status, checked below
$Root = Split-Path -Parent $PSScriptRoot
$Extension = Join-Path (Join-Path $Root 'editors') 'vscode'
$Id = 'py-doc.vscode-py-doc-preview'
$Vsce = '@vscode/vsce@3.6.2'
if (-not $StateFile) { $StateFile = Join-Path (Join-Path $Root '.py-doc') 'vscode-extension.sha256' }

function Write-Ok([string]$Text) { Write-Host "    ok    $Text" -ForegroundColor Green }
function Write-Note([string]$Text) { Write-Host "    note  $Text" -ForegroundColor Yellow }
function Stop-Install([string]$Text, [string]$Advice) {
    Write-Host "    FAIL  $Text" -ForegroundColor Red
    if ($Advice) { Write-Host "          $Advice" -ForegroundColor Red }
    exit 1
}

# VS Code's command line: -Code, else code on the PATH, else where the Windows installers put it
function Find-Code {
    if ($Code) {
        $named = Get-Command $Code -ErrorAction SilentlyContinue
        if (-not $named) { Stop-Install "-Code names $Code, which is not there" "Give the path of code.cmd (Windows) or code" }
        return $named.Source
    }
    $onPath = Get-Command code -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($onPath) { return $onPath.Source }
    $places = @()
    if ($env:LOCALAPPDATA) { $places += Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd' }
    if ($env:ProgramFiles) { $places += Join-Path $env:ProgramFiles 'Microsoft VS Code\bin\code.cmd' }
    foreach ($place in $places) { if (Test-Path -LiteralPath $place) { return $place } }
    return $null
}

# One hash of the extension's own files (not node_modules, the tests or a built .vsix), the same on every platform
function Get-ExtensionHash {
    $lines = Get-ChildItem -LiteralPath $Extension -Recurse -File |
        ForEach-Object {
            $relative = $_.FullName.Substring($Extension.Length).TrimStart('\', '/').Replace('\', '/')
            if ($relative -notmatch '^(node_modules|test)/' -and $relative -notmatch '\.vsix$') {
                "$relative $((Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash)"
            }
        } |
        Sort-Object -CaseSensitive
    $bytes = [Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '') } finally { $sha.Dispose() }
}

$codeExe = Find-Code
if (-not $codeExe) {
    Write-Note "VS Code not found, so its extension is not installed. With VS Code elsewhere, pass -Code with its code.cmd"
    exit 0
}

$version = (Get-Content -Raw -LiteralPath (Join-Path $Extension 'package.json') | ConvertFrom-Json).version
$hash = Get-ExtensionHash
$listed = & $codeExe --list-extensions --show-versions 2>$null
if ($LASTEXITCODE -ne 0) { Stop-Install "VS Code ($codeExe) did not list its extensions" "Start VS Code once, then run this again" }
$installed = @($listed | Where-Object { "$_" -like "$Id@*" } | ForEach-Object { "$_".Split('@')[1] }) | Select-Object -First 1
$stamped = if (Test-Path -LiteralPath $StateFile) { (Get-Content -Raw -LiteralPath $StateFile).Trim() } else { '' }

if ($Force) {
    $why = "-Force"
} elseif (-not $installed) {
    $why = "it is not installed"
} elseif ($installed -ne $version) {
    $why = "$installed is installed and this checkout has $version"
} elseif ($stamped -ne $hash) {
    $why = "its files changed since it was installed"
} else {
    Write-Ok "py-doc Live Preview $version is installed in VS Code and up to date"
    exit 0
}

Write-Host "    installing py-doc Live Preview $version into VS Code: $why"
$npm = Get-Command npm -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1  # npm.cmd on Windows
$npx = Get-Command npx -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $npm -or -not $npx) {
    Stop-Install "Node.js is needed to build the extension, and npm is not on the PATH" "Install Node.js 18 or later from nodejs.org, open a new terminal and run this again"
}

$vsix = Join-Path ([IO.Path]::GetTempPath()) "vscode-py-doc-preview-$version.vsix"
Push-Location $Extension
try {
    & $npm.Source ci --ignore-scripts --no-audit --no-fund --loglevel=error
    if ($LASTEXITCODE -ne 0) { Stop-Install "npm ci failed (exit status $LASTEXITCODE)" "npm's message is above; a proxy may need npm config set proxy" }
    & $npx.Source --yes $Vsce package --out $vsix
    if ($LASTEXITCODE -ne 0) { Stop-Install "building the extension failed (exit status $LASTEXITCODE)" "vsce's message is above" }
} finally {
    Pop-Location
}

& $codeExe --install-extension $vsix --force
$status = $LASTEXITCODE
Remove-Item -LiteralPath $vsix -ErrorAction SilentlyContinue
if ($status -ne 0) { Stop-Install "VS Code did not install the extension (exit status $status)" "VS Code's message is above" }

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StateFile) | Out-Null
Set-Content -LiteralPath $StateFile -Value $hash -Encoding ascii
Write-Ok "py-doc Live Preview $version installed in VS Code. In a VS Code window already open, run Developer: Reload Window"
exit 0
