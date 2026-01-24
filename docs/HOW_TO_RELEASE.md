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

Check commits since last release:
```bash
git log v0.x.x-1..HEAD --oneline
```

Add new version entry at the top (after the header), **using commit messages as content**:
```markdown
## [0.x.x] - YYYY-MM-DD

### Fixed
- Version detection in executables (from: fix: version detection in executables)

### Added  
- New feature name (from: feat: new feature name)

### Changed
- Documentation updates (from: docs: documentation updates)
```

### 3. Commit Changes

```bash
git add shello_cli/__init__.py CHANGELOG.md
git commit -m "fix: short description here"
git push origin main
```

**Commit message format**: `fix:` or `feat:` or `chore:` followed by 3-5 words

### 4. Create and Push Tag

```bash
# Create annotated tag
git tag -a v0.x.x -m "Release v0.x.x - Brief Description"

# Push tag to GitHub
git push origin v0.x.x
```

### 5. GitHub Actions

The release workflow will automatically:
- Build executables for Windows, Linux, and macOS
- Create a GitHub release with CHANGELOG entry
- Upload binaries as release assets

Check the Actions tab on GitHub to monitor progress: https://github.com/om-mapari/shello-cli/actions

**That's it!** The release is complete once GitHub Actions finishes.

## Quick Commands

```bash
# Check commits since last release
git log v0.x.x-1..HEAD --oneline

# Update version in __init__.py (manual edit)
# Update CHANGELOG.md (manual edit)

# Commit and tag
git add shello_cli/__init__.py CHANGELOG.md
git commit -m "fix: short description here"
git tag -a v0.x.x -m "Release v0.x.x - Brief description"
git push origin main
git push origin v0.x.x

# Done! GitHub Actions handles the rest
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
