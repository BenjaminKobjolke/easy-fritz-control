@echo off
setlocal
if not exist "%~dp0analyze_code_config.bat" (
    echo ERROR: Copy analyze_code_config.example.bat to analyze_code_config.bat first.
    exit /b 1
)
call "%~dp0analyze_code_config.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0.." || exit /b 1
set "PATH=%CD%\.venv\Scripts;%PATH%"
"%CLI_ANALYZER_PATH%\venv\Scripts\python.exe" "%CLI_ANALYZER_PATH%\ruff_fixer.py" --path "." --rules "code_analysis_rules.json" %* <NUL
set "FIX_RESULT=%ERRORLEVEL%"
popd
exit /b %FIX_RESULT%
