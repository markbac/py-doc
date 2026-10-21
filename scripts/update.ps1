<#
.SYNOPSIS
    Bring a py-doc install up to date and check that it works: the code, the Python packages, the py-doc
    command, Docker and the tool image.

.DESCRIPTION
    Run it after every pull, or whenever py-doc misbehaves after a change. Each step says what it does,
    and the script stops at the first step that fails, with what to do about it.

      1. Code         git pull --ff-only (skipped with -NoPull, or when this is not a Git checkout)
      2. Python       the project's own virtual environment, .venv in this folder, made from a Python 3.10
                      or later when it is missing or broken (-System or -Python: another Python instead)
      3. Packages     pip install -e . into it (with the test tools when -Dev), then pip check, which
                      sees only py-doc's own packages because the environment is py-doc's alone
      4. Command      py-doc runs, and the py-doc on the PATH is this one (-AddToPath puts it there)
      5. Docker       the container engine answers (py-doc setup installs it when it does not)
      6. Tool image   built when its definition changed (every layer again with -Rebuild),
                      and the images of earlier versions removed unless -KeepOldImages
      7. Doctor       py-doc doctor: the container runs the tools
      8. Tests        with -Test: the test suite and the documentation lint

.PARAMETER NoPull
    Do not pull: use the code as it is.

.PARAMETER Dev
    Also install the test and lint tools (pip install -e ".[dev]"). -Test implies it.

.PARAMETER Rebuild
    Build every layer of the tool image again, even when it is up to date.

.PARAMETER KeepOldImages
    Keep the tool images of earlier versions (each is several GB).

.PARAMETER Test
    Also run the test suite and lint the documentation.

.PARAMETER Python
    Install into this Python instead of .venv, such as C:\venvs\py-doc\Scripts\python.exe.

.PARAMETER System
    Install into the Python on the PATH (python, else py -3) instead of .venv. Its other packages can then
    conflict with py-doc's, which pip check reports.

.PARAMETER RecreateVenv
    Delete .venv and make it again, such as after a Python upgrade.

.PARAMETER AddToPath
    Put .venv\Scripts at the front of your user PATH, so py-doc in a new terminal is this one.

.PARAMETER CaFile
    An extra certificate for image builds behind a TLS-inspecting proxy (passed to py-doc tools build).

.EXAMPLE
    .\scripts\update.ps1
.EXAMPLE
    .\scripts\update.ps1 -Dev -Test
.EXAMPLE
    .\scripts\update.ps1 -AddToPath
.EXAMPLE
    .\scripts\update.ps1 -NoPull -Rebuild -RecreateVenv
#>
[CmdletBinding()]
param(
    [switch]$NoPull,
    [switch]$Dev,
    [switch]$Rebuild,
    [switch]$KeepOldImages,
    [switch]$Test,
    [string]$Python,
    [switch]$System,
    [switch]$RecreateVenv,
    [switch]$AddToPath,
    [string]$CaFile
)

Set-StrictMode -Version Latest
# Programs report failure through their exit status, which every step checks. 'Stop' would also turn any
# line a program writes to stderr into an error in Windows PowerShell 5.1, so it is not used.
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
$script:Step = 0
$script:Started = Get-Date

function Write-Step([string]$Text) {
    $script:Step++
    Write-Host ""
    Write-Host "[$script:Step] $Text" -ForegroundColor Cyan
}

function Write-Ok([string]$Text) { Write-Host "    ok    $Text" -ForegroundColor Green }
function Write-Note([string]$Text) { Write-Host "    note  $Text" -ForegroundColor Yellow }

function Stop-Update([string]$Text, [string]$Advice) {
    Write-Host "    FAIL  $Text" -ForegroundColor Red
    if ($Advice) { Write-Host "          $Advice" -ForegroundColor Red }
    exit 1
}

# Runs a program, shows its output, and stops the update when it fails.
function Invoke-Checked([string]$What, [string]$Advice, [string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { Stop-Update "$What failed (exit status $LASTEXITCODE)" $Advice }
}

# Runs py-doc through the chosen Python, so it is always this install that runs.
function Invoke-PyDoc([string[]]$Arguments) {
    & $script:PythonExe @script:PythonArgs -m py_doc @Arguments
}

Push-Location $Root
try {
    Write-Host "py-doc update in $Root"

    # 1. Code ------------------------------------------------------------------------------------
    Write-Step "Code"
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($NoPull) {
        Write-Note "not pulled (-NoPull)"
    } elseif (-not $git -or -not (Test-Path (Join-Path $Root '.git'))) {
        Write-Note "not a Git checkout, so nothing to pull"
    } else {
        $branch = (& git rev-parse --abbrev-ref HEAD).Trim()
        $dirty = & git status --porcelain --untracked-files=no
        if ($dirty) { Write-Note "local changes to tracked files are kept; a pull that would touch them stops here" }
        if ($branch -ne 'main') { Write-Note "on branch $branch, not main" }
        Invoke-Checked "git pull" "Pull or merge by hand (the pull only fast-forwards), or run with -NoPull" git @('pull', '--ff-only')
        Write-Ok "$branch at $((& git log -1 --format='%h %s').Trim())"
    }

    # 2. Python ----------------------------------------------------------------------------------
    Write-Step "Python"
    $script:PythonArgs = @()
    $venv = Join-Path $Root '.venv'
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    if (-not (Test-Path $venvPython)) { $venvPython = Join-Path $venv 'bin/python' }  # PowerShell on Linux

    # A Python 3.10 or later on the PATH: the base of the virtual environment, or the target with -System
    function Find-BasePython {
        foreach ($candidate in @(@('python'), @('py', '-3'), @('python3'))) {
            if (-not (Get-Command $candidate[0] -ErrorAction SilentlyContinue)) { continue }
            $extra = @($candidate | Select-Object -Skip 1)
            $ok = & $candidate[0] @extra -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return , $candidate }
        }
        Stop-Update "no Python 3.10 or later found" "Install Python 3.10 or later from python.org, or name one with -Python"
    }

    if ($Python) {
        $script:PythonExe = $Python
        $where = "the Python -Python names"
    } elseif ($System) {
        $base = Find-BasePython
        $script:PythonExe = $base[0]
        $script:PythonArgs = @($base | Select-Object -Skip 1)
        $where = "the Python on the PATH (-System)"
    } else {
        $healthy = $false
        if ((Test-Path $venvPython) -and -not $RecreateVenv) {
            & $venvPython -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
            $healthy = ($LASTEXITCODE -eq 0)
            if (-not $healthy) { Write-Note ".venv is broken or too old (was its Python removed or upgraded?), so it is made again" }
        }
        if (-not $healthy) {
            if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
            $base = Find-BasePython
            $baseArgs = @($base | Select-Object -Skip 1)
            Write-Host "    making .venv with $($base -join ' ')"
            Invoke-Checked "making the virtual environment" "Check that this Python can make one (python -m venv)" $base[0] ($baseArgs + @('-m', 'venv', $venv))
            $venvPython = Join-Path $venv 'Scripts\python.exe'
            if (-not (Test-Path $venvPython)) { $venvPython = Join-Path $venv 'bin/python' }
        }
        $script:PythonExe = $venvPython
        $where = "py-doc's own virtual environment, .venv"
    }
    $version = & $script:PythonExe @script:PythonArgs -c "import sys; print('%d.%d.%d' % sys.version_info[:3]); print(sys.executable)"
    if ($LASTEXITCODE -ne 0 -or -not $version) { Stop-Update "$script:PythonExe does not run" "Run again with -RecreateVenv, or name a working Python with -Python" }
    $parts = $version[0].Split('.')
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
        Stop-Update "Python $($version[0]) is too old" "py-doc needs Python 3.10 or later"
    }
    Write-Ok "Python $($version[0]) in $where"

    # 3. Packages --------------------------------------------------------------------------------
    Write-Step "Packages"
    $target = if ($Dev -or $Test) { '.[dev]' } else { '.' }
    Invoke-Checked "pip install" "Read pip's message above; a proxy may need PIP_INDEX_URL or a certificate" $script:PythonExe ($script:PythonArgs + @('-m', 'pip', 'install', '--disable-pip-version-check', '--quiet', '--upgrade', 'pip'))
    Invoke-Checked "pip install" "Read pip's message above; a proxy may need PIP_INDEX_URL or a certificate" $script:PythonExe ($script:PythonArgs + @('-m', 'pip', 'install', '--disable-pip-version-check', '--quiet', '--editable', $target))
    $shared = if ($Python -or $System) { " This Python is shared with other programs: the default, .venv, keeps py-doc's packages apart." } else { "" }
    Invoke-Checked "pip check" "A package above conflicts with another.$shared Run again with -RecreateVenv to start clean" $script:PythonExe ($script:PythonArgs + @('-m', 'pip', 'check', '--disable-pip-version-check'))
    Write-Ok "py-doc and its dependencies installed ($target)"

    # 4. Command ---------------------------------------------------------------------------------
    Write-Step "Command"
    $pyDocVersion = Invoke-PyDoc @('--version')
    if ($LASTEXITCODE -ne 0) { Stop-Update "py-doc does not start" "Its error is above. Run again with -RecreateVenv" }
    Write-Ok "$pyDocVersion"
    $find = "import os, sysconfig; dirs = [sysconfig.get_path('scripts'), sysconfig.get_path('scripts', os.name + '_user')]; " +
            "print(next((d for d in dirs if os.path.isfile(os.path.join(d, 'py-doc.exe')) or os.path.isfile(os.path.join(d, 'py-doc'))), dirs[0]))"
    $scripts = (& $script:PythonExe @script:PythonArgs -c $find | Select-Object -First 1).Trim()
    if ($AddToPath) {
        $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
        $entries = @($userPath -split ';' | Where-Object { $_ -and ($_.TrimEnd('\') -ne $scripts.TrimEnd('\')) })
        [Environment]::SetEnvironmentVariable('Path', (@($scripts) + $entries) -join ';', 'User')
        $env:Path = "$scripts;$env:Path"
        Write-Ok "$scripts is first on your user PATH: a new terminal runs this py-doc"
    }
    $command = Get-Command py-doc -ErrorAction SilentlyContinue
    $mine = $command -and ((Split-Path -Parent $command.Source).TrimEnd('\') -eq $scripts.TrimEnd('\'))
    if ($mine) {
        Write-Ok "py-doc on the PATH is this install ($($command.Source))"
    } else {
        if ($command) {
            Write-Note "the py-doc on the PATH is another install: $($command.Source)"
            if ($command.Source -match 'WindowsApps|Python3\d+\\Scripts|LocalCache') {
                Write-Note "remove it with: python -m pip uninstall py-doc   (in the Python it came from)"
            }
        } else {
            Write-Note "py-doc is not on the PATH"
        }
        Write-Note "run .\scripts\update.ps1 -AddToPath to put $scripts first, or use $scripts\py-doc.exe"
    }

    # 5. Docker ----------------------------------------------------------------------------------
    Write-Step "Docker"
    $status = Invoke-PyDoc @('tools', 'status') 2>&1 | ForEach-Object { "$_" }
    $exit = $LASTEXITCODE
    $imageLine = $status | Where-Object { $_ -match '^image\s' } | Select-Object -First 1
    if ($exit -ne 0 -or -not $imageLine) {
        $status | ForEach-Object { Write-Host "    $_" }
        Stop-Update "the container engine does not answer" "Start Docker, or run py-doc setup to install Docker Engine (in WSL 2 on Windows)"
    }
    Write-Ok "the container engine answers"

    # 6. Tool image ------------------------------------------------------------------------------
    Write-Step "Tool image"
    $tag = ($imageLine -split '\s+')[1]
    $built = $imageLine -notmatch 'not built'
    if ($built -and -not $Rebuild) {
        Write-Ok "$tag is up to date"
    } else {
        $why = if ($Rebuild) { "every layer again (-Rebuild)" } else { "its definition changed" }
        Write-Host "    building $tag, $why. The first build of a version takes 5 to 30 minutes."
        $buildArgs = @('tools', 'build')
        if ($Rebuild) { $buildArgs += '--no-cache' }
        if ($CaFile) { $buildArgs += @('--ca-file', $CaFile) }
        Invoke-PyDoc $buildArgs
        if ($LASTEXITCODE -ne 0) { Stop-Update "the image build failed" "The build log is above. Behind a TLS-inspecting proxy, pass the proxy's certificate with -CaFile" }
        Write-Ok "$tag built"
    }
    if ($KeepOldImages) {
        Write-Note "images of earlier versions kept (-KeepOldImages)"
    } else {
        $removed = Invoke-PyDoc @('tools', 'prune', '-q')
        if ($LASTEXITCODE -ne 0) { Write-Note "could not remove older images: $removed" } else { Write-Ok "$removed" }
    }

    # 7. Doctor ----------------------------------------------------------------------------------
    Write-Step "Doctor"
    Invoke-Checked "py-doc doctor" "Each failing check above says what to do" $script:PythonExe ($script:PythonArgs + @('-m', 'py_doc', 'doctor'))
    Write-Ok "the tools run in the container"

    # 8. Tests -----------------------------------------------------------------------------------
    if ($Test) {
        Write-Step "Tests"
        Invoke-Checked "the test suite" "A failing test above names what broke" $script:PythonExe ($script:PythonArgs + @('-m', 'pytest', '-q', '-p', 'no:cacheprovider'))
        Invoke-Checked "the documentation lint" "The issues are listed above" $script:PythonExe ($script:PythonArgs + @('-m', 'py_doc', 'lint', 'docs', '--strict', '-q'))
        Write-Ok "tests and documentation lint pass"
    }

    $minutes = [math]::Round(((Get-Date) - $script:Started).TotalMinutes, 1)
    Write-Host ""
    Write-Host "py-doc is up to date and working ($minutes min)." -ForegroundColor Green
    exit 0
} finally {
    Pop-Location
}
