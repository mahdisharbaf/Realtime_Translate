@echo off
title Live Caption Translator
cd /d "%~dp0"
python caption_translator.py
if errorlevel 1 (
    echo.
    echo App exited with an error. Run install.bat first.
    pause
)
