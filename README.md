# Power Playlists

## What is it?

Power Playlists is a command-line tool written in Python that allows for
the creation of dynamic playlists in Spotify, i.e., playlists that are
defined as filters and combinations of other playlists or sources. You
create playlist definitions in a YAML config file, and whenever the
command-line tool is run, it will sync your Spotify playlists to match
their definitions. Daemonization is also supported to run the tool as a
background process with periodic updates.

## Quick Start Guide

### Installation

#### Using pip

First, make sure you have a functioning Python 3.9+ installation. Then,
install `power-playlists` from PyPi:

    > pip install power-playlists

#### Using uv

With uv, you can either install the tool, at which point you can invoke it directly:

    > uv tool install power-playlists

Or run it using `uvx`, no installation necessary:

    > uvx power-playlists

Note that if you use `uvx`, you will need to prefix the command with `uvx` each time it is invoked.

### Usage

After this you can simply run `power-playlists` to interact with the
tool, including seeing the usage info:

```shell
> power-playlists
Usage: power-playlists [OPTIONS] COMMAND [ARGS]...

Options:
  ...
  --help          Show this message and exit.

Commands:
  edit     Launch the graphical editor for creating/editing configurations.
  run      Run a single iteration of the playlist updates.
  daemon   Run the tool in daemon mode for automatic updates.
```

Out of the box, nothing interesting will happen. Get started by creating
a [YAML configuration file](https://yaml.org/) to contain details about
your Spotify account and the playlists you want to define. If you need a
primer on YAML, check out
[Wikipedia](https://en.wikipedia.org/wiki/YAML#Syntax) or the guide
provided by
[Camel](https://camel.readthedocs.io/en/latest/yamlref.html). For the
purpose of defining your playlists, you only need to understand
[sequences](https://camel.readthedocs.io/en/latest/yamlref.html#sequences)
and
[mappings](https://camel.readthedocs.io/en/latest/yamlref.html#mappings).
Really, just looking at some examples will probably be sufficient --
YAML is designed to be intuitive.

By default, `power-playlists` will search for YAML config files within
the `~/.power-playlists/userconf` directory. You can either create these
configuration files manually using your favorite text editor:

    > vi ~/.power-playlists/userconf/myconf.yaml

Or use the built-in **graphical editor** for a more intuitive experience:

    > power-playlists edit

At the top level, this must be a mapping, each key-value pair of which
will define a `node`. Nodes are the building blocks of your playlist
definitions, such as a `playlist` node (an input consisting of all of
the tracks from a playlist), an `is_liked` node (filters to only tracks
which have been liked/saved), or an `output` node (saves the tracks to a
playlist).

Each YAML file should contain all of the playlist definitions for a
single user. When you first run `power-playlists`, you'll be prompted
to log in to your Spotify account. A token allowing `power-playlists` to
access your account will be stored based on the name of the YAML file,
so you'll have to log in once for each file, and if the name of the
file changes, you will have to re-login.

Let's look at a simple example:

```yaml
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
  type: output
  input: PlaylistABCombined
  playlist_name: 'Playlist A + B Combined'
```

This will take two playlists, combine them, and save the result as a new
playlist. Input playlists are generally referred to by their URI, or
unique identifier, which can be found by right-clicking on a playlist
and going to `Share > Copy Spotify URI`.

## Graphical Editor

Power Playlists includes a modern web-based graphical editor that makes creating and editing playlist configurations much easier than manually writing YAML files. The editor provides a visual, node-based interface with drag-and-drop functionality.

### Launching the Editor

**Basic usage** - Automatically discover and load configurations:
```shell
> power-playlists edit
```

**Load specific configuration**:
```shell
> power-playlists edit --userconf ~/.power-playlists/userconf/myplaylist.yaml
```

**Use different app configuration**:
```shell
> power-playlists edit --appconf ~/my-app-config.yaml
```

### Features

The graphical editor provides:

- **Modern web interface** - Opens automatically in your default browser with a clean, professional design
- **Visual node editor** - Color-coded nodes with intuitive icons (♫ for playlists, ❤️ for filters, 📤 for outputs)
- **Drag & drop** - Easily reposition nodes to organize your playlist flow
- **Curved connection lines** - Visual connections show dependencies between nodes
- **Smart property editing** - Structured forms with dropdowns, checkboxes, and validation
- **Real-time validation** - Prevents saving invalid configurations with detailed error messages
- **Automatic discovery** - Finds existing configurations and provides a selector when multiple exist

### Using the Editor

1. **Adding nodes**: Click "Add Node" and select the type of node you want (playlist, filter, combiner, etc.)
2. **Editing properties**: Double-click any node to edit its properties using structured forms
3. **Connecting nodes**: Nodes are automatically connected based on their input/output relationships
4. **Saving**: Use "Save" to update the current file or "Save As" to create a new configuration

### Node Types Available

The editor supports all Power Playlists node types:
- **Playlist nodes** (♫) - Input from existing Spotify playlists
- **Filter nodes** (🔍) - Filter by liked status, time added, release date, or custom expressions
- **Combiner nodes** (➕) - Combine multiple inputs into one
- **Sort nodes** (🔀) - Sort by time added, name, artist, album, or release date  
- **Limit nodes** (🔢) - Limit to a specific number of tracks
- **Output nodes** (📤) - Save results to Spotify playlists

The graphical editor is especially useful for:
- **Beginners** getting started with Power Playlists
- **Complex workflows** with many interconnected nodes
- **Visual learners** who prefer drag-and-drop to YAML editing
- **Quick iterations** when experimenting with different configurations

You can always switch between the graphical editor and manual YAML editing - both work with the same configuration files.

Full documentation can be found on the [Power Playlists page on GitHub
Pages](https://xkrogen.github.io/power-playlists). A full reference of
all supported node types is also available in the [Node
Reference](https://xkrogen.github.io/power-playlists/powerplaylists.html#node-reference).

## Examples

Power Playlists supports many advanced features through its flexible node system. Several example configurations are available in the [`samples/`](https://github.com/xkrogen/power-playlists/samples/) directory demonstrating different capabilities, from basic filtering to complex multi-stage processing with dynamic templates.

### Sample Files

- [`samples/basic-combiner.yaml`](https://github.com/xkrogen/power-playlists/samples/basic-combiner.yaml) - Basic playlist combination
- [`samples/basic-filtering.yaml`](https://github.com/xkrogen/power-playlists/samples/basic-filtering.yaml) - Time-based and liked track filtering with combining, sorting, and deduplication
- [`samples/dynamic-template-release-date-filtering.yaml`](https://github.com/xkrogen/power-playlists/samples/dynamic-template-release-date-filtering.yaml) - Music organization by release decades using dynamic templates
- [`samples/complex-workflow.yaml`](https://github.com/xkrogen/power-playlists/samples/complex-workflow.yaml) - Comprehensive multi-stage processing with mood-based workflows and master playlist creation

To try any of these examples, copy them to your `~/.power-playlists/userconf/` directory and replace the placeholder URIs with your actual Spotify playlist URIs.

## The Backstory

Remember [Smart Playlists from
iTunes](https://support.apple.com/guide/itunes/create-delete-and-use-smart-playlists-itns3001/windows)?
They're pretty much the *only* thing I miss about iTunes, otherwise
being grateful to be fully devoted to the Church of Spotify. I've found
two projects along the direction of enhancing Spotify with such
functionality:

-   [Smarter
    Playlists](http://smarterplaylists.playlistmachinery.com/) - This
    one really resonated with me. The graph-based playlist designer was
    intuitive and powerful, if a little clunky. By the time I came
    across the project in 2020, it had clearly fallen out of maintenance
    and various things were broken.
-   [PLYLST](https://plylst.app/) - This was another good attempt, with
    a much shinier and modern UI, though it came at the cost of
    decreased flexibility and functionality. As of February 2021, it has
    shut down, a victim of its own success as a personal side project
    grew too big for the server costs to make sense.

Both of these were great projects in their own right! But, and this
might just be the programmer in me talking, I always felt like something
fundamental was missing. Automating playlist creation is fantastic and
opens up a whole world of possibilities, but graphical interfaces mean
that creating and editing playlist definitions was always a manual and
laborious process. If I had many similar but slightly different
definitions, and I wanted to make a tweak, I had to go through and make
the same tweak many times, navigating the UI each time. I longed for
config-driven playlist definitions. Thus Power Playlists was born, out
of a desire to create an automated playlist manager that was designed to
be *flexible* and *extensible*, with a config-driven approach that
allowed for templating.

Unfortunately, I know nothing about programming for the web, so instead
of a shiny UI, all you get is a command-line tool. But this also means
it's fairly easy to get started on your own, and you don't run the
risk of setting up a bunch of custom playlist definitions and building
your music library around them -- only to find out that one day, the
application breaks and doesn't get fixed, or has to shut down.

## Running in Daemon Mode

Power Playlists can run continuously in daemon mode to automatically update your playlists on a schedule. This allows you to set up your playlist definitions once and have them automatically maintained without manual intervention.

### Unix/Linux Daemon Commands

For general Unix and Linux systems, Power Playlists provides self-managed daemon functionality:

```shell
# Start the daemon in the background
> power-playlists daemon start

# Check if the daemon is running
> power-playlists daemon show

# Stop the daemon
> power-playlists daemon stop

# Restart the daemon (stops existing and starts new)
> power-playlists daemon restart
```

The daemon will:
- Run playlist updates every 12 hours by default (configurable)
- Log all activity to `~/.power-playlists/app.log` with log rotation
- Use a PID file at `~/.power-playlists/daemon.pid` for process management
- Continue running across system reboots if started from a startup script

### macOS launchd Integration (Recommended for macOS)

On macOS systems, using `launchd` is preferred over the self-managed daemon as it provides better system integration:

```shell
# Install the daemon to run automatically via launchd
> power-playlists launchd install

# Uninstall the daemon from launchd
> power-playlists launchd uninstall
```

The launchd integration:
- Creates a plist file at `~/Library/LaunchAgents/com.github.xkrogen.power-playlists.plist`
- Automatically starts the daemon when you log in
- Manages the process lifecycle through the system
- Uses the same default 12-hour update interval

### Configuration Options

You can customize daemon behavior by creating a configuration file at `~/.power-playlists/conf.yaml`:

```yaml
# Update interval in minutes (default: 720 = 12 hours)
daemon_sleep_period_minutes: 360  # 6 hours

# Log file location and level
log_file_path: "~/.power-playlists/app.log"
log_file_level: "INFO"  # DEBUG, INFO, WARNING, ERROR

# PID file location (Unix daemon only)
daemon_pidfile: "~/.power-playlists/daemon.pid"
```

### Monitoring and Troubleshooting

**Check daemon status:**
```shell
# For Unix daemon
> power-playlists daemon show

# For macOS launchd
> launchctl list | grep power-playlists
```

**View logs:**
```shell
# Follow live logs
> tail -f ~/.power-playlists/app.log

# View recent log entries
> tail -50 ~/.power-playlists/app.log
```

**Common issues:**
- If daemon fails to start, check that `~/.power-playlists/userconf/` contains valid configuration files
- Ensure Spotify authentication tokens are valid (you may need to re-run manually first)
- On macOS, if launchd installation fails, verify you have write permissions to `~/Library/LaunchAgents/`

The daemon will process all YAML configuration files found in your `~/.power-playlists/userconf/` directory during each update cycle.

## Development

Power Playlists uses modern Python tooling with [uv](https://github.com/astral-sh/uv) for dependency management and [Task](https://taskfile.dev) for development automation.

### Quick Setup

1. Install [Task](https://taskfile.dev/docs/installation) for development automation. If you're using Homebrew, simply run `brew install go-task`.
2. Clone the repository 
3. Run `task install` to install all dependencies and set up the development environment
4. Run `task --list` to see all available development tasks

### Development Tasks

The project uses Task to automate common development workflows:

```shell
# Complete development setup
> task install

# Run all validation checks (tests, linting, formatting, type checking)
> task check

# Run tests
> task test

# Run tests with verbose output
> task test -- -v

# Run the application with help
> task run -- --help

# Run the application with a config file  
> task run -- run --userconf path/to/config.yaml

# Auto-fix formatting and linting issues
> task fix

# Generate documentation
> task docs

# Clean build artifacts
> task clean
```

The project is configured with `pyproject.toml` and includes a lockfile (`uv.lock`) for reproducible builds. The CI pipeline uses the same Task commands as local development to ensure consistency.
