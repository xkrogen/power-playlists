# Power Playlists - GitHub Copilot Instructions

**ALWAYS follow these instructions first and only fallback to additional search and context gathering if the information here is incomplete or found to be in error.**

## About Power Playlists

Power Playlists is a Python CLI tool for creating dynamic Spotify playlists using YAML configuration files. It supports combining playlists, filtering tracks, and automated playlist management with daemon mode for periodic updates.

## Working Effectively

### Bootstrap and Setup Commands
**PREFERRED**: Use Task for all development operations:

1. **Install Task**: Follow instructions at https://taskfile.dev/#/installation or use included binary `./bin/task`
2. **Complete setup**: `task setup` (or `./bin/task setup`) - installs UV, dependencies, and creates required directories
3. **List all tasks**: `task --list` (or `./bin/task --list`) - shows all available development tasks

**Alternative manual setup** (if Task is not available):
1. **Install UV package manager**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Add UV to PATH**: `export PATH="$HOME/.local/bin:$PATH"`
3. **Install all dependencies**: `uv sync --all-extras` - takes <1 second
4. **Create required application directory**: `mkdir -p ~/.power-playlists/userconf`

### Build and Test Commands

**PREFERRED**: Use Task commands for consistency with CI:

- **Run all validation checks**: `task check-all` - runs tests, linting, formatting, and type checking
- **Run tests**: `task test` - takes ~2 seconds. NEVER CANCEL, set timeout to 60+ seconds for safety
- **Run linting check**: `task lint` - takes <0.1 seconds  
- **Format code**: `task format` - takes <0.1 seconds
- **Format check**: `task format-check` - takes <0.1 seconds
- **Type checking**: `task typecheck` - takes ~2.5 seconds. NEVER CANCEL, set timeout to 60+ seconds for safety
- **Fix formatting and linting**: `task fix` - auto-fixes issues
- **Generate documentation**: `task docs` - takes ~1.6 seconds

**Alternative manual commands** (if Task is not available):
- **Run tests**: `uv run pytest` - takes ~2 seconds. NEVER CANCEL, set timeout to 60+ seconds for safety
- **Linting check**: `uv run ruff check .` - takes <0.1 seconds  
- **Format code**: `uv run ruff format .` - takes <0.1 seconds
- **Format check**: `uv run ruff format --check .` - takes <0.1 seconds
- **Type checking**: `uv run mypy src/` - takes ~2.5 seconds. NEVER CANCEL, set timeout to 60+ seconds for safety
- **Generate documentation**: `uv run pdoc src/powerplaylists --output-directory /tmp/docs` - takes ~1.6 seconds

### Run the Application

**PREFERRED**: Use Task commands for consistency:
- **CLI help**: `task app-help`
- **Run command help**: `task app-run-help`
- **Test with sample config**: `task app-test-config`

**Alternative manual commands**:
- **CLI help**: `uv run power-playlists --help`
- **Run command help**: `uv run power-playlists run --help`
- **Test with sample config**: `uv run power-playlists run --userconf samples/xkrogen.yaml`
  - Note: Sample config contains placeholder URIs and will show validation errors - this is expected
- **Daemon commands**: `uv run power-playlists daemon --help`

## Validation Requirements

**CRITICAL**: Always perform these validation steps after making changes:

### Mandatory Pre-commit Validation
**CRITICAL**: Always run `task check-all` before committing changes or the CI will fail.

Alternatively, you can run individual checks manually:
1. `uv run ruff check .` - must pass (linting)
2. `uv run ruff format --check .` - must pass (formatting)  
3. `uv run pytest` - must pass (675 tests)
4. `uv run mypy src/` - must pass (type checking)

### Application Functionality Testing
After making changes to the core application logic, use Task commands for consistency:
1. **Test CLI help**: `task app-help` - should show usage info
2. **Test run command**: `task app-run-help` - should show run options
3. **Test config parsing**: `task app-test-config` - should show validation error about missing inputs (this is expected behavior)
4. **Verify error handling**: Check that configuration errors are caught gracefully
5. **Note**: With a valid config file, the application will hang waiting for Spotify authentication - this is normal behavior and indicates successful config parsing

### Manual Testing Scenarios
- **Configuration validation**: Test with various YAML config files to ensure proper error messages
- **Directory requirements**: Verify application creates/handles ~/.power-playlists directory correctly
- **CLI argument parsing**: Test all command line options work as expected

## Important Project Information

### Timing Expectations and Timeouts
- **Dependency installation**: <1 second - set timeout to 30+ seconds  
- **Test suite**: ~2 seconds (673 tests) - NEVER CANCEL, set timeout to 60+ seconds
- **Linting**: <0.1 seconds - set timeout to 30+ seconds
- **Type checking**: ~2.5 seconds - NEVER CANCEL, set timeout to 60+ seconds
- **Documentation generation**: ~1.6 seconds - set timeout to 30+ seconds

### Key Project Structure
```
src/powerplaylists/           # Main application code
├── main.py                  # CLI entry point and command definitions
├── nodes.py                 # Playlist processing nodes (input, output, filters)
├── spotify_client.py        # Spotify API client wrapper
└── utils.py                 # Configuration and utility functions

tests/                       # Comprehensive test suite (673 tests)
├── test_mocks.py           # Mock Spotify client for testing
├── test_node.py            # Node functionality tests
├── test_spotify_client.py  # Spotify client tests
└── testutil.py             # Test utilities

samples/xkrogen.yaml        # Sample playlist configuration
docs/CI_SETUP.md           # CI workflow documentation
```

### Configuration and Dependencies
- **Python versions**: 3.9, 3.10, 3.11, 3.12 supported
- **Package manager**: UV (modern, fast Python package manager)
- **Build system**: Hatchling
- **Key dependencies**: Click, spotipy, PyYAML, python-daemon
- **Dev tools**: pytest, ruff, mypy, pdoc

### Application Runtime Requirements
- **Required directory**: `~/.power-playlists/userconf` must exist before running
- **Configuration files**: YAML format in `~/.power-playlists/userconf/` by default
- **Spotify authentication**: First run requires Spotify login (stored per config file)
- **Log files**: Written to `~/.power-playlists/app.log`

## CI/CD Information

### GitHub Actions Workflow
The CI runs on every push/PR to main branch and tests against Python 3.9-3.12:
1. Install Task runner
2. Install UV and Python
3. Run all validation checks with `task ci` (equivalent to `task check-all`)

The CI uses the same Task commands as local development for consistency.

### Common CI Failures and Solutions
**PREFERRED**: Use Task commands for consistency:
- **Any validation failures**: Run `task check-all` and fix issues
- **Linting failures**: Run `task lint` to see issues, `task fix` to auto-fix
- **Formatting failures**: Run `task fix` to auto-fix
- **Test failures**: Run `task test-verbose` to see detailed failure info
- **Type checking failures**: Run `task typecheck` and fix type annotations

**Alternative manual commands**:
- **Linting failures**: Run `uv run ruff check .` and fix issues
- **Formatting failures**: Run `uv run ruff format .` to auto-fix
- **Test failures**: Run `uv run pytest -v` to see detailed failure info
- **Type checking failures**: Run `uv run mypy src/` and fix type annotations

## Common Development Tasks

### Adding New Features
1. Write tests first in appropriate test file
2. Implement feature in relevant source file
3. Run `task check-all` for complete validation
4. Test CLI functionality with `task app-help` and related tasks
5. Update documentation if needed

### Debugging Configuration Issues
1. Use sample config as reference: `samples/basic-combiner.yaml`
2. Test with: `task app-test-config` or `uv run power-playlists run --userconf your_config.yaml`
3. Check logs at: `~/.power-playlists/app.log`
4. Use `--verifymode incremental` for detailed debugging

### Working with Tests
**PREFERRED**: Use Task commands:
- **Run all tests**: `task test`
- **Run with verbose output**: `task test-verbose`
- **Quick development cycle**: `task dev-test` (lint + test)

**Alternative manual commands**:
- **Run all tests**: `uv run pytest`
- **Run specific test file**: `uv run pytest tests/test_node.py`
- **Run with verbose output**: `uv run pytest -v`
- **Test coverage includes**: Mock Spotify client, playlist operations, configuration parsing

## Reference Information

### Quick Command Reference
```bash
# Setup (PREFERRED)
task setup                               # Complete setup (installs UV, deps, creates dirs)
task --list                              # Show all available tasks

# Development (PREFERRED)
task check-all                           # Run all validation checks
task test                                # Run tests (~2s)
task lint                                # Lint (<0.1s)
task format                              # Format (<0.1s)
task typecheck                           # Type check (~2.5s)
task fix                                 # Auto-fix formatting and linting
task dev-test                            # Quick development cycle (lint + test)

# Application (PREFERRED) 
task app-help                            # CLI help
task app-run-help                        # Run command help
task app-test-config                     # Test with sample config

# Alternative manual commands (if Task not available)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync --all-extras
mkdir -p ~/.power-playlists/userconf
uv run pytest                           # Run tests (~2s)
uv run ruff check .                     # Lint (<0.1s)
uv run ruff format .                    # Format (<0.1s)
uv run mypy src/                        # Type check (~2.5s)
uv run power-playlists --help           # CLI help
```

### File Patterns to Check After Changes
- **After modifying nodes.py**: Always test playlist processing with `task app-test-config`
- **After modifying main.py**: Always test CLI commands with `task app-help` and `task app-run-help`
- **After modifying utils.py**: Always test configuration loading and validation with `task app-test-config`
- **After modifying spotify_client.py**: Always run test_spotify_client.py tests with `task test`

This tool processes Spotify playlists, so always validate that your changes don't break the core playlist processing workflow, even when making seemingly unrelated changes. Use `task check-all` before finalizing any changes.