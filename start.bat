@echo off
:: Usage: start.bat show ^| diff ^| sync [--box NAME]
pushd "%~dp0"
uv run easy-fritz-control %*
set RESULT=%ERRORLEVEL%
popd
exit /b %RESULT%
