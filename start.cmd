@echo off
cd /d "%~dp0"
title Teaching Assistant - keep this window open
echo Checking local teaching assistant before opening browser...
python launch.py
echo The teaching assistant has stopped. Check errors above.
pause
