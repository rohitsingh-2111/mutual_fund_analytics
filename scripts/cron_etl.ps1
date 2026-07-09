# 1. Establish absolute tracking roots relative to script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 2. Correctly jump up one folder level using core resolution engine
$ProjectRoot = (Get-Item (Join-Path $ScriptDir "..")).FullName

# 3. Formulate absolute destinations
$LogFile = "$ProjectRoot\data\processed\etl_cron_log.txt"
$TargetScript = "$ScriptDir\live_nav_fetch.py"

# 4. Provision data directories automatically if missing
$LogDir = Split-Path -Parent $LogFile
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# 5. Output chronological header tags to log records
"--------------------------------------------------" | Out-File -FilePath $LogFile -Append
"⏳ SYSTEM TIME NAV FETCH DISPATCH TRIGGERED: $(Get-Date)" | Out-File -FilePath $LogFile -Append
"--------------------------------------------------" | Out-File -FilePath $LogFile -Append

# 6. Locate the Python interpreter and execute the live NAV fetch wrapper
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
if (-not $PythonExe) {
    $PythonExe = (Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
}
if (-not $PythonExe) {
    "ERROR: Python interpreter not found on PATH." | Out-File -FilePath $LogFile -Append
    exit 1
}

& $PythonExe $TargetScript >> $LogFile 2>&1

# Note: This wrapper updates raw NAV CSV files via live_nav_fetch.py.
# For a full analytics rebuild, run `python -m scripts.etl_pipeline` after the NAV refresh.
