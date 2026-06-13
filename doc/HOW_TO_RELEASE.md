# How to Release Shello CLI

Simple guide for creating a new release.

## Prerequisites

- All changes committed and pushed to `main` branch
- Tests passing
- CHANGELOG.md updated with new version

## Release Steps

### 1. Update Version Number

Edit `shello_cli/__init__.py`:
```python
__version__ = "0.x.x"  # Update to new version
```

### 2. Update CHANGELOG.md

Add a section at the top of the file for the new version:
```markdown
## [0.x.x] - YYYY-MM-DD

### Added
- Feature descriptions...

### Changed
- Change descriptions...

### Fixed
- Bug fix descriptions...
```

### 3. Commit Changes

```bash
git add shello_cli/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 0.x.x and <brief description of changes>"
git push origin main
```

### 4. Create and Push Tag

```bash
# Create annotated tag
git tag -a v0.x.x -m "Release v0.x.x - <Brief description of changes>"

# Push tag to GitHub
git push origin v0.x.x
```

### 5. GitHub Actions

The release workflow will automatically:
- Build executables for Windows, Linux, and macOS
- Create a GitHub release
- Upload binaries as release assets

Check the Actions tab on GitHub to monitor progress.

## Quick Commands

```bash
# Update version in __init__.py (manual edit)
# Update CHANGELOG.md (manual edit)

# Commit and tag
git add shello_cli/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 0.x.x and <brief description of changes>"
git tag -a v0.x.x -m "Release v0.x.x - <Brief description of changes>"
git push origin main
git push origin v0.x.x
```

## If You Need to Fix a Release

If you pushed a tag with issues:

```bash
# Delete local tag
git tag -d v0.x.x

# Delete remote tag
git push origin :refs/tags/v0.x.x

# Fix the issue, commit it
git add <files>
git commit -m "fix: description"
git push origin main

# Recreate tag
git tag -a v0.x.x -m "Release v0.x.x - Description"
git push origin v0.x.x
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, backward compatible

## Notes

- Always test locally before releasing
- Keep CHANGELOG.md up to date
- Tag messages should be descriptive but brief
- GitHub Actions handles the build and release automatically
