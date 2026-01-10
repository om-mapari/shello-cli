# Building Shello CLI Executable

## Quick Start

### Windows
```cmd
build.bat
```

### Linux/Mac
```bash
chmod +x build.sh
./build.sh
```

## Manual Build

If you prefer to build manually:

**Using UV (Recommended):**
```bash
# Install PyInstaller
uv pip install pyinstaller

# Build the executable
pyinstaller shello.spec --clean
```



## Output

The executable will be created at:
- **Windows**: `dist/shello.exe`
- **Linux/Mac**: `dist/shello`

## Testing

Test the built executable:

```bash
# Windows
dist\shello.exe --version
dist\shello.exe --help

# Linux/Mac
./dist/shello --version
./dist/shello --help
```

## System-Wide Installation

### Windows

**Option 1: Add to PATH**
1. Copy the full path to the `dist` folder
2. Open System Properties → Environment Variables
3. Edit the `Path` variable
4. Add the `dist` folder path
5. Open a new terminal and run: `shello --version`

**Option 2: Copy to System Folder**
```cmd
copy dist\shello.exe C:\Windows\System32\
```

### Linux/Mac

**Option 1: Copy to /usr/local/bin**
```bash
sudo cp dist/shello /usr/local/bin/
sudo chmod +x /usr/local/bin/shello
```

**Option 2: Add to PATH**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:/full/path/to/dist"
```

## Troubleshooting

### Missing Modules
If you get import errors, add the missing module to `hiddenimports` in `shello.spec`:

```python
hiddenimports=[
    'your_missing_module',
    # ... other imports
],
```

### Large File Size
The executable includes Python and all dependencies. To reduce size:
- Remove unused dependencies from requirements.txt
- Use `upx=True` in the spec file (already enabled)

### Antivirus False Positives
Some antivirus software may flag PyInstaller executables. This is a known issue. You can:
- Add an exception for the executable
- Sign the executable with a code signing certificate
