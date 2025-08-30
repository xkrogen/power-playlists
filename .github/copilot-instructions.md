# Power Playlists Development Instructions

Power Playlists is a Python command-line tool for creating dynamic Spotify playlists through YAML configuration files. The tool allows playlist definitions using filters and combinations of other playlists or sources.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Bootstrap and Setup
Install all dependencies and set up the development environment:
```bash
pip3 install click pytest pyyaml spotipy lockfile psutil python-daemon python-dateutil
pip3 install sphinx sphinx-rtd-theme  # For documentation
```

### Project Structure
- `src/powerplaylists/` - Main Python package source code
- `tests/` - Test suite using pytest
- `docs/` - Sphinx documentation
- `samples/` - Example YAML configuration files
- `setup.py` - Package configuration and dependencies

### Running Tests
```bash
cd /path/to/power-playlists
PYTHONPATH=src python3 -m pytest tests/ -v
```
- **TIMING**: Test suite completes in ~15 seconds. NEVER CANCEL.
- **EXPECTATION**: Many tests fail (654 failures, 19 pass) due to Spotify API mocking issues - this is normal for development environment without real Spotify credentials.
- Only tests in `tests/test_mocks.py` are expected to pass consistently.

### Building Documentation  
```bash
cd docs
PYTHONPATH=../src make html
```
- **TIMING**: Documentation build completes in ~3 seconds. NEVER CANCEL.
- Output will be in `docs/_build/html/`
- Expect 2 warnings about missing _static directory and language configuration - these are normal.

### Running the CLI Tool
```bash
cd /path/to/power-playlists
PYTHONPATH=src python3 -m powerplaylists.main --help
PYTHONPATH=src python3 -c "from powerplaylists.main import cli; cli(['--help'])"
```

Available commands:
- `run` - Execute a single iteration of playlist updates
- `daemon start/stop/restart/show` - Control background process

### Development Installation
Do NOT use `pip install -e .` as it may fail due to PyYAML compilation issues. Instead, use `PYTHONPATH=src` approach for all testing and development.

## Validation and Testing

### Manual Validation Workflow
Always test functionality after making changes:

1. **Create test configuration**:
```bash
mkdir -p ~/.power-playlists/userconf
cat > ~/.power-playlists/userconf/test.yaml << 'EOF'
PlaylistA:
  type: 'playlist'
  uri: 'spotify:playlist:xxxxxxxxxxxxxxxxx'
PlaylistB:
  type: 'playlist'
  uri: 'spotify:playlist:yyyyyyyyyyyyyyyyy'
PlaylistABCombined:
  type: 'combiner'
  inputs:
    - PlaylistA
    - PlaylistB
PlaylistABCombinedOutput:
  type: 'output'
  playlist_name: 'Playlist A + B Combined'
EOF
```

2. **Test CLI commands**:
```bash
PYTHONPATH=src python3 -c "from powerplaylists.main import cli; cli(['run', '--help'])"
PYTHONPATH=src python3 -c "from powerplaylists.main import cli; cli(['daemon', '--help'])"
```

3. **Run working tests**:
```bash
PYTHONPATH=src python3 -m pytest tests/test_mocks.py -v
```

### Pre-commit Validation
Always run before committing changes:
```bash
# Run working tests only (avoid Spotify API dependent tests)
PYTHONPATH=src python3 -m pytest tests/test_mocks.py -v

# Verify CLI still works
PYTHONPATH=src python3 -m powerplaylists.main --help

# Build documentation  
cd docs && PYTHONPATH=../src make html
```

## Key Development Areas

### Core Components
- `src/powerplaylists/main.py` - CLI interface using Click framework
- `src/powerplaylists/nodes.py` - Playlist node definitions and logic
- `src/powerplaylists/spotify_client.py` - Spotify API client wrapper
- `src/powerplaylists/utils.py` - Configuration and utility functions

### Configuration System
- App configuration: `~/.power-playlists/conf.yaml` (optional)
- User playlists: `~/.power-playlists/userconf/*.yaml` (required for operation)
- Cache directory: `cache/` (auto-created)

### Dependencies
Critical packages that must be available:
- Click >=7.1,<8 (CLI framework)
- PyYAML >=5.3,<6 (Configuration parsing)
- spotipy >=2.14.0,<3 (Spotify API client)
- lockfile >=0.12 (Process locking)
- psutil >5.0,<6 (Process management)
- python-daemon >=2.2.4,<3 (Background process)
- python-dateutil >=2.8.1,<3 (Date utilities)

### Testing Framework
- Uses pytest for testing
- Mock Spotify API client in `tests/test_mocks.py`
- Most tests require Spotify credentials and will fail in development
- Focus on `test_mocks.py` for reliable testing during development

## Common Issues

### Installation Problems
- PyYAML compilation may fail - install individually: `pip3 install pyyaml`
- Network timeouts during pip install - retry individual packages
- Use system Python 3.7+ (tested with 3.12)

### Runtime Issues  
- Missing Spotify credentials - normal for development, will prompt for login
- Cache directory permissions - ensure `cache/` is writable
- YAML syntax errors - validate configuration files

### Testing Issues
- Most tests fail without Spotify API credentials - expected behavior
- Focus on `tests/test_mocks.py` which contains working unit tests
- Use `PYTHONPATH=src` for all Python commands

## File Locations Reference

```
.
├── README.rst                 # Project documentation
├── setup.py                  # Package configuration  
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Development dependencies
├── src/powerplaylists/       # Main source code
│   ├── main.py              # CLI entry point
│   ├── nodes.py             # Playlist logic
│   ├── spotify_client.py    # API client
│   └── utils.py             # Configuration
├── tests/                    # Test suite
│   ├── test_mocks.py        # Working unit tests
│   ├── test_node.py         # Node tests (require API)
│   └── test_spotify_client.py # Client tests (require API)
├── docs/                     # Documentation
│   ├── Makefile             # Build documentation
│   └── conf.py              # Sphinx configuration
└── samples/                  # Example configurations
    └── xkrogen.yaml         # Sample playlist definition
```

## Expected Timing
- **Test suite (working tests)**: ~0.3 seconds (NEVER CANCEL)  
- **Test suite (full)**: ~15 seconds (NEVER CANCEL, many failures expected)
- **Documentation build**: ~1.5 seconds (NEVER CANCEL)  
- **CLI commands**: Instant response for help/validation
- **Dependency installation**: Already installed in this environment, ~1 second

Always allow sufficient time for operations to complete rather than canceling prematurely.

## CRITICAL: Failed Installation Workarounds
If `pip install -e .` fails due to PyYAML compilation issues:
```bash
# DO NOT use editable install - use PYTHONPATH instead
PYTHONPATH=src python3 -m powerplaylists.main --help
```

If network timeouts occur during dependency installation:
```bash
# Install dependencies individually
pip3 install click
pip3 install pytest  
pip3 install pyyaml
pip3 install spotipy
pip3 install lockfile psutil python-daemon python-dateutil
```

## Verification Commands
Test these commands work after making changes:
```bash
# Dependencies already installed - quick check
pip3 list | grep -E "(click|pytest|pyyaml|spotipy)"

# Working tests (13 tests, ~0.3 seconds)
PYTHONPATH=src python3 -m pytest tests/test_mocks.py -v

# CLI functionality  
PYTHONPATH=src python3 -m powerplaylists.main --help
PYTHONPATH=src python3 -c "from powerplaylists.main import cli; cli(['run', '--help'])"
PYTHONPATH=src python3 -c "from powerplaylists.main import cli; cli(['daemon', '--help'])"

# Documentation build (~1.5 seconds)
cd docs && PYTHONPATH=../src make html
```