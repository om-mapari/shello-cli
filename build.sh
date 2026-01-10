#!/bin/bash
echo "Building Shello CLI with PyInstaller..."
echo

# Install PyInstaller if not already installed
uv pip install pyinstaller

# Clean previous builds
rm -rf build dist/shello

# Build the executable
pyinstaller shello.spec --clean

echo
if [ -f "dist/shello" ]; then
    echo "✓ Build successful!"
    echo
    echo "Executable created at: dist/shello"
    echo
    echo "To use it system-wide:"
    echo "1. Add the dist folder to your PATH, OR"
    echo "2. Copy dist/shello to a folder in your PATH (e.g., /usr/local/bin)"
    echo
    echo "Test it with: ./dist/shello --version"
else
    echo "✗ Build failed! Check the output above for errors."
fi
