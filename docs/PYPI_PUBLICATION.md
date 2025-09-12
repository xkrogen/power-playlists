# PyPI Publication Setup

This document describes the automated PyPI publication setup for the Power Playlists project.

## Overview

The project is now configured for automated publication to PyPI with the following features:

- **Dynamic Versioning**: Versions are automatically generated based on git commits using `hatch-vcs`
- **Automated Testing**: All publishments are preceded by complete test suites (pytest, ruff linting, mypy type checking)
- **Dual Publishing**: Development versions go to TestPyPI, releases go to PyPI
- **Trusted Publishing**: Uses OpenID Connect for secure, keyless authentication

## Publication Strategy

### Development Versions (TestPyPI)
- **Trigger**: Every push to the `main` branch
- **Destination**: https://test.pypi.org/p/power-playlists
- **Version Format**: `0.1.dev<N>+g<commit-hash>.d<date>`
- **Purpose**: Testing and validation of the packaging pipeline

### Release Versions (PyPI)
- **Trigger**: Creating a GitHub release
- **Destination**: https://pypi.org/p/power-playlists
- **Version Format**: Based on git tags (e.g., `v1.0.0` → `1.0.0`)
- **Purpose**: Official releases for end users

## Setup Requirements

### Repository Configuration
1. **Trusted Publishing**: Configure trusted publisher relationships in PyPI/TestPyPI
   - Go to PyPI/TestPyPI → Account settings → Publishing
   - Add GitHub repository as trusted publisher
   - Specify environment names: `pypi` and `testpypi`

2. **GitHub Environments**: Create protected environments in GitHub
   - `pypi`: For production releases
   - `testpypi`: For development releases

### Package Structure
- **Package Name**: `power-playlists` (matches repository name)
- **Module Name**: `power_playlists` (Python-friendly identifier)
- **Entry Point**: `power-playlists = power_playlists.main:cli`

## Workflow Files

### `.github/workflows/pypi-publish.yml`
Main publication workflow with three jobs:
1. **build**: Runs tests and builds packages
2. **test-pypi-publish**: Publishes dev versions to TestPyPI
3. **pypi-publish**: Publishes releases to PyPI

### `.github/workflows/ci.yml` 
Enhanced CI workflow with proper git history for versioning.

## Version Management

Versions are automatically managed by `hatch-vcs`:
- **Development**: `0.1.dev<N>+g<hash>.d<date>`
- **Tagged releases**: Version from git tag
- **Configuration**: See `[tool.hatch.version]` in `pyproject.toml`

## Manual Release Process

To create a new release:
1. Create and push a git tag: `git tag v1.0.0 && git push origin v1.0.0`
2. Create a GitHub release from the tag
3. The workflow will automatically publish to PyPI

## Installation

Users can install from PyPI:
```bash
pip install power-playlists
```

Or from TestPyPI for development versions:
```bash
pip install --index-url https://test.pypi.org/simple/ power-playlists
```