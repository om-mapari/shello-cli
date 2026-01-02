@echo off
echo Building Shello CLI with PyInstaller...
echo.

REM Install PyInstaller if not already installed
pip install pyinstaller

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist\shello rmdir /s /q dist\shello

REM Build the executable
pyinstaller shello.spec --clean

echo.
if exist dist\shello.exe (
    echo ✓ Build successful!
    echo.
    echo Executable created at: dist\shello.exe
    echo.
    echo To use it system-wide:
    echo 1. Add the dist folder to your PATH environment variable, OR
    echo 2. Copy dist\shello.exe to a folder that's already in your PATH
    echo.
    echo Test it with: dist\shello.exe --version
) else (
    echo ✗ Build failed! Check the output above for errors.
)

pause
