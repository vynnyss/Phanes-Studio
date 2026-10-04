@echo off
set PYTHONUTF8=1
"%~dp0runtime\official\code\venv\Scripts\python.exe" "%~dp0scripts\studio_cli.py" %*
exit /b %errorlevel%
