# Power Playlists - GitHub Copilot Instructions

**ALWAYS follow these instructions first and only fallback to additional search and context gathering if the information here is incomplete or found to be in error.**

## About Power Playlists

Power Playlists is a Python CLI tool for creating dynamic Spotify playlists using YAML configuration files. It supports combining playlists, filtering tracks, and automated playlist management with daemon mode for periodic updates.

## Working Effectively

### Environment Setup
For initial environment setup and tool installation, see `copilot-setup-steps.yml` in this directory, which contains the automated setup steps for the Copilot coding agent environment.

### Build and Test Commands

**PREFERRED**: Use Task commands for consistency with CI:

- **Run all validation checks**: `task check` - runs tests, linting, formatting, and type checking
- **Run tests**: `task test` - takes ~2 seconds. NEVER CANCEL, set timeout to 60+ seconds for safety
- **Format and fix code**: `task fix` - auto-fixes issues
- **Generate documentation**: `task docs` - takes ~1.6 seconds

### Run the Application

**PREFERRED**: Use Task commands for consistency:
- **Run application**: `task run -- --help` or `task run -- run --userconf path/to/config.yaml`
- **Daemon commands**: `uv run power-playlists daemon --help`

## Validation Requirements

**CRITICAL**: Always perform these validation steps after making changes:

### Mandatory Pre-commit Validation
**CRITICAL**: Always run `task check` before committing changes or the CI will fail.

Alternatively, you can run individual checks manually:
1. `uv run ruff check .` - must pass (linting)
2. `uv run ruff format --check .` - must pass (formatting)  
3. `uv run pytest` - must pass
4. `uv run mypy src/` - must pass (type checking)

### Application Functionality Testing
After making changes to the core application logic, use Task commands for consistency:
1. **Test CLI help**: `task run -- --help` - should show usage info
2. **Test run command**: `task run -- run --help` - should show run options
3. **Test config parsing**: `task run -- run --userconf config.yaml` - should show validation error about missing inputs (this is expected behavior)
4. **Verify error handling**: Check that configuration errors are caught gracefully
5. **Note**: With a valid config file, the application will hang waiting for Spotify authentication - this is normal behavior and indicates successful config parsing

### Manual Testing Scenarios
- **Configuration validation**: Test with various YAML config files to ensure proper error messages
- **Directory requirements**: Verify application creates/handles ~/.power-playlists directory correctly
- **CLI argument parsing**: Test all command line options work as expected

## Important Project Information

### Timing Expectations and Timeouts
- **Dependency installation**: <1 second - set timeout to 30+ seconds  
- **Test suite**: ~2 seconds - NEVER CANCEL, set timeout to 60+ seconds
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

tests/                       # Comprehensive test suite
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
3. Run all validation checks with `task check`

The CI uses the same Task commands as local development for consistency.

### Common CI Failures and Solutions
**PREFERRED**: Use Task commands for consistency:
- **Any validation failures**: Run `task check` and fix issues
- **Auto-fix issues**: Run `task fix` to auto-fix formatting and linting
- **Test failures**: Run `task test -- -v` to see detailed failure info
- **Type checking failures**: Run `task check` and fix type annotations

## Common Development Tasks

### Adding New Features
1. Write tests first in appropriate test file
2. Implement feature in relevant source file
3. Run `task check` for complete validation
4. Test CLI functionality with `task run -- --help` and related commands
5. Update documentation if needed

### Debugging Configuration Issues
1. Use sample config as reference: `samples/basic-combiner.yaml`
2. Test with: `task run -- run --userconf your_config.yaml`
3. Check logs at: `~/.power-playlists/app.log`
4. Use `--verifymode incremental` for detailed debugging

### Working with Tests
**PREFERRED**: Use Task commands:
- **Run all tests**: `task test`
- **Run with verbose output**: `task test -- -v`
- **Quick development cycle**: `task check` (all validation)

## Reference Information

### Quick Command Reference
```bash
# Development  
task check                               # Run all validation checks
task test                                # Run tests (~2s)
task fix                                 # Auto-fix formatting and linting
task docs                                # Generate documentation

# Application
task run -- --help                      # CLI help
task run -- run --userconf config.yaml  # Run with config

# Setup (see copilot-setup-steps.yml for full setup)
task install                             # Complete install (installs UV, deps, Python)
task --list                              # Show all available tasks
```

### File Patterns to Check After Changes
- **After modifying nodes.py**: Always test playlist processing with `task run -- run --userconf config.yaml`
- **After modifying main.py**: Always test CLI commands with `task run -- --help`
- **After modifying utils.py**: Always test configuration loading and validation with `task run -- run --userconf config.yaml`
- **After modifying spotify_client.py**: Always run test_spotify_client.py tests with `task test`

This tool processes Spotify playlists, so always validate that your changes don't break the core playlist processing workflow, even when making seemingly unrelated changes. Use `task check` before finalizing any changes.