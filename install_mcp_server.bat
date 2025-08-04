@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM === Check Python 3.10+ installation ===
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    goto :end
)

REM Get Python version output e.g. "Python 3.11.5"
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v

REM Get major and minor versions
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

REM Check if Python version is at least 3.10
if %PY_MAJOR% lss 3 (
    echo ERROR: Python version is less than 3.10. Please install Python 3.10 or higher.
    goto :end
)
if %PY_MAJOR% equ 3 if %PY_MINOR% lss 10 (
    echo ERROR: Python version is less than 3.10. Please install Python 3.10 or higher.
    goto :end
)

REM === Install Python requirements ===
REM Assuming requirements.txt is in the same folder as this script
echo Installing Python packages from requirements.txt...
pip install --upgrade pip
pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install Python requirements.
    goto :end
)
echo Python requirements installed successfully.

REM === 1) Locate nli_mcp.py ===
SET "SRV_PATH="
for /f "delims=" %%F in ('dir /S /B "%~dp0nli_mcp.py"') do (
    SET "SRV_PATH=%%~fF"
    goto :found
)
echo ERROR: nli_mcp.py not found.
goto :end

:found
echo Found nli_mcp.py at: !SRV_PATH!

REM === 2) Set environment variable ===
set "NLI_API_KEY=DVQyidFLOAjp12ib92pNJPmflmB5IessOq1CJQDK"
echo Environment variable NLI_API_KEY set.

REM === 3) Install ===
fastmcp install claude-desktop "!SRV_PATH!" --server-name "nli_mcp" --env NLI_API_KEY=!NLI_API_KEY!
if errorlevel 1 (
    echo ERROR: fastmcp install failed.
    goto :end
)
echo fastmcp install completed.

REM === 4) Modify JSON config using separate PowerShell file ===
SET "CONFIG=%APPDATA%\Claude\claude_desktop_config.json"
if not exist "!CONFIG!" (
    echo ERROR: Config file not found: !CONFIG!
    goto :end
)
echo Modifying JSON config: !CONFIG!

REM Create PowerShell script to avoid encoding and syntax issues
(
echo $path = "$env:APPDATA\Claude\claude_desktop_config.json"
echo $srv = "!SRV_PATH!"
echo $content = Get-Content $path -Raw
echo if ^([string]::IsNullOrWhiteSpace^($content^)^) { $cfg = @{} } else { $cfg = $content ^| ConvertFrom-Json }
echo if ^(-not $cfg.mcpServers^) { $cfg.mcpServers = @{} }
echo if ^(-not $cfg.mcpServers.nli_mcp^) { $cfg.mcpServers.nli_mcp = @{} }
echo $cfg.mcpServers.nli_mcp.command = 'python'
echo $cfg.mcpServers.nli_mcp.args = @^($srv^)
echo if ^(-not $cfg.mcpServers.nli_mcp.env^) { $cfg.mcpServers.nli_mcp.env = @{} }
echo $cfg.mcpServers.nli_mcp.env.NLI_API_KEY = '!NLI_API_KEY!'
echo $cfg.mcpServers.nli_mcp.transport = 'stdio'
echo $json = $cfg ^| ConvertTo-Json -Depth 10
echo [System.IO.File]::WriteAllText^($path, $json^)
) > "%TEMP%\update_json.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\update_json.ps1"

if errorlevel 1 (
    echo ERROR: JSON update failed.
    del "%TEMP%\update_json.ps1" 2>nul
    goto :end
)

del "%TEMP%\update_json.ps1" 2>nul
echo JSON config updated.

:end
echo.
echo  Done. Please restart Claude Desktop to apply changes. 
ENDLOCAL