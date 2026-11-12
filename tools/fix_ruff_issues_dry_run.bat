@echo off
setlocal
call "%~dp0fix_ruff_issues.bat" --dry-run
exit /b %ERRORLEVEL%
