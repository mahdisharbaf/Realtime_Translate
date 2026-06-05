@echo off
title Live Caption Translator - Install

echo -----------------------------------------------
echo  Live Caption Translator - Installing...
echo -----------------------------------------------
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
python --version

echo.
echo [1/3] Upgrading pip...
python -m pip install --upgrade pip -q

echo.
echo [2/3] Installing Python packages...
pip install mss Pillow numpy pytesseract deep-translator pywin32 arabic-reshaper python-bidi uiautomation psutil

python -m pywin32_postinstall -install > nul 2>&1

echo.
echo [3/3] Checking Tesseract OCR...

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract already installed.
    goto :verify
)
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract already installed.
    goto :verify
)

echo Tesseract not found. Downloading (~50MB)...

set "TESS_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
set "TESS_SETUP=%TEMP%\tesseract_setup.exe"

powershell -NoProfile -Command "Invoke-WebRequest -Uri '%TESS_URL%' -OutFile '%TESS_SETUP%' -UseBasicParsing"

if not exist "%TESS_SETUP%" (
    echo [ERROR] Download failed.
    echo Please install manually from:
    echo   https://github.com/UB-Mannheim/tesseract/releases
    pause
    exit /b 1
)

echo Installing Tesseract silently...
"%TESS_SETUP%" /S
del /f /q "%TESS_SETUP%" > nul 2>&1
timeout /t 4 /nobreak > nul

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract installed successfully.
) else (
    echo [WARNING] Tesseract path not found after install. May need manual install.
)

:verify
echo.
echo -----------------------------------------------
echo  Verifying packages...
echo -----------------------------------------------
python -c "import mss, PIL, numpy, pytesseract, deep_translator, win32gui; print('[OK] All packages ready!')"

echo.
echo -----------------------------------------------
echo  Done! Run the app with: run.bat
echo -----------------------------------------------
echo.
pause
