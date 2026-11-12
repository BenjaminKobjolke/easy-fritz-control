@echo off
setlocal
if not exist "%~dp0analyze_code_config.bat" (
    echo ERROR: analyze_code_config.bat not found.
    echo Copy analyze_code_config.example.bat to analyze_code_config.bat and set CLI_ANALYZER_PATH and LANGUAGE.
    exit /b 1
)
call "%~dp0analyze_code_config.bat"
if errorlevel 1 exit /b 1
if not exist "%CLI_ANALYZER_PATH%\venv\Scripts\python.exe" (
    echo ERROR: cli-code-analyzer was not found. Check CLI_ANALYZER_PATH and its venv.
    exit /b 1
)
if not exist "%CLI_ANALYZER_PATH%\main.py" (
    echo ERROR: cli-code-analyzer was not found. Check CLI_ANALYZER_PATH.
    exit /b 1
)
pushd "%~dp0.." || exit /b 1
REM Reuse the project's locked Ruff installation without global tool configuration.
set "PATH=%CD%\.venv\Scripts;%PATH%"
echo Running Python code analysis...
"%CLI_ANALYZER_PATH%\venv\Scripts\python.exe" "%CLI_ANALYZER_PATH%\main.py" --language %LANGUAGE% --path "." --verbosity minimal --output "code_analysis_results" --rules "code_analysis_rules.json" --fail-on-warnings --fail-on-findings %* <NUL
set "ANALYSIS_RESULT=%ERRORLEVEL%"
popd
exit /b %ANALYSIS_RESULT%
