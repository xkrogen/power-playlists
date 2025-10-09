# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About Power Playlists

Power Playlists is a Python CLI tool for creating dynamic Spotify playlists using YAML configuration files. It uses a graph-based node system where playlists are built by connecting nodes (inputs, filters, combiners, sorters, outputs) to create complex playlist workflows. The tool supports daemon mode for automatic periodic updates.

## Development Commands

This project uses [Task](https://taskfile.dev) for development automation and [uv](https://github.com/astral-sh/uv) for fast dependency management.

### Essential Commands

```bash
# Initial setup
task install              # Install uv, Python, and all dependencies

# Development workflow
task check                # Run all validation (tests, linting, formatting, type checking) - ALWAYS run before committing
task test                 # Run test suite (~2 seconds)
task test -- -v           # Run tests with verbose output
task fix                  # Auto-fix formatting and linting issues

# Run the application
task run -- --help                           # Show CLI help
task run -- run --userconf path/to/config    # Run with specific config
task run -- edit                             # Launch graphical editor
task run -- daemon start                     # Start daemon mode

# Other tasks
task docs                 # Generate documentation (~1.6 seconds)
task build                # Build package for distribution
task clean                # Clean build artifacts and caches
```

### Running Individual Tests

```bash
# Run specific test file
task test -- tests/test_node.py

# Run specific test function
task test -- tests/test_node.py::test_function_name

# Run tests matching a pattern
task test -- -k "pattern"
```

### Manual Validation (if not using `task check`)

```bash
uv run ruff check .            # Linting
uv run ruff format --check .   # Formatting check
uv run mypy src/               # Type checking
uv run pytest                  # Tests
```

## Architecture Overview

### Core Application Flow

1. **Configuration Loading** (`utils.py`): Loads app config (`~/.power-playlists/conf.yaml`) and user configs (`~/.power-playlists/userconf/*.yaml`)
2. **Node Resolution** (`nodes.py`): Parses YAML into node objects, resolves template nodes into concrete nodes, validates the graph
3. **Spotify Authentication** (`spotify_client.py`): Manages OAuth tokens (stored per config file), wraps spotipy library
4. **Track Processing**: Each node type processes tracks (fetch, filter, combine, sort, limit) and caches results
5. **Playlist Updates** (`main.py`): Output nodes sync results to Spotify playlists, with verification modes

### Node System Architecture

The node system (`nodes.py`) is the core of Power Playlists. Key concepts:

- **Node Types**: All nodes inherit from `Node` base class with a `tracks()` method
  - `InputNode`: Base for nodes that fetch tracks (e.g., `PlaylistNode`, `LikedNode`)
  - `TransformerNode`: Base for nodes that transform input (filters, combiners, sorters, limiters)
  - `OutputNode`: Saves tracks to Spotify playlists
  - `TemplateNode`: Dynamic node generation with variable substitution

- **Node Resolution**: Multi-phase process in `resolve_node_list()`:
  1. Load all nodes from YAML dicts
  2. Resolve template nodes (may require multiple passes)
  3. Resolve input references between nodes
  4. Validate no playlists are both input and output

- **Track Caching**: `InputNode` caches `tracks()` results to avoid redundant Spotify API calls

### Key Files

- `main.py` (152 lines): CLI entry point with Click commands (`run`, `daemon`, `launchd`, `edit`)
- `nodes.py` (1050+ lines): All node type implementations and resolution logic
- `spotify_client.py` (500+ lines): Spotify API wrapper with caching and error handling
- `utils.py` (200+ lines): Configuration management, constants, verify modes
- `gui_editor.py` (1000+ lines): Web-based graphical editor with HTTP server

### Configuration Files

- `~/.power-playlists/conf.yaml`: App configuration (daemon interval, log settings, etc.)
- `~/.power-playlists/userconf/*.yaml`: User playlist definitions (one file per Spotify account)
- Each YAML file maps to a separate Spotify authentication token

### Graphical Editor

The `edit` command launches a web-based editor (`gui_editor.py`) that:
- Runs a local HTTP server with an embedded HTML/CSS/JS interface
- Provides visual node-based editing with drag-and-drop
- Supports all node types except dynamic templates
- Saves changes back to YAML files

## Important Development Notes

### Before Committing

**ALWAYS run `task check`** - This runs the same validation as CI and catches issues early. The CI will fail if these checks don't pass.

### Testing Expectations

- Test suite runs in ~2 seconds - never cancel, set timeouts to 60+ seconds
- Tests use mock Spotify clients (`tests/test_mocks.py`) to avoid real API calls
- Browser-based tests (`test_gui_editor_browser.py`) use Selenium with Chrome/Chromium

### Configuration Validation

When testing with real configs:
1. App will hang waiting for Spotify auth on first run (expected behavior)
2. Use `--verifymode incremental` for detailed debugging
3. Logs written to `~/.power-playlists/app.log`
4. Token cache stored in `~/.power-playlists/cache/`

### Node Development Patterns

When adding/modifying node types:
1. Inherit from appropriate base class (`InputNode`, `TransformerNode`, etc.)
2. Implement `ntype()` class method returning unique string identifier
3. Implement `tracks()` method (use caching from base class if applicable)
4. Implement `resolve_inputs()` to resolve node references
5. Handle template resolution if supporting dynamic templates
6. Add schema to `gui_editor.py` if node should appear in graphical editor
7. Update `scripts/generate_node_docs.py` for documentation generation

### Common Gotchas

- **Circular dependencies**: Node resolution will hang if nodes reference each other in a cycle
- **Template explosion**: Template nodes can generate many concrete nodes; watch for exponential growth
- **Playlist name conflicts**: Same playlist name can't be both input and output (validated in `resolve_node_list()`)
- **Track deduplication**: Spotify URIs are used for identity; multiple adds of same track are handled

## Project Standards

### Code Quality

- **Formatting**: Ruff with 120 character line length
- **Type hints**: Required in source (mypy strict mode)
- **Python versions**: 3.9+ supported, 3.12 for development
- **Docstrings**: Required for public APIs and node types

### Testing

- Tests must not require real Spotify credentials
- Mock all external API calls
- Browser tests can be skipped if browser not available
- Test file naming: `test_*.py` in `tests/` directory

### Documentation

- Node types documented via docstrings extracted by `generate_node_docs.py`
- User-facing docs generated with pdoc to GitHub Pages
- Sample configs in `samples/` directory demonstrate features

## Daemon Mode

Two daemon implementations:
1. **Self-managed daemon** (Unix/Linux): Uses `python-daemon` library, PID file at `~/.power-playlists/daemon.pid`
2. **launchd integration** (macOS): Creates plist in `~/Library/LaunchAgents/`, managed by system

Both update playlists every 12 hours by default (configurable via `daemon_sleep_period_minutes` in app config).
