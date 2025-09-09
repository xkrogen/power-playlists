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

First, make sure you have a functioning Python 3.9+ installation. Then,
install `power-playlists` from PyPi:

    > pip install power-playlists

After this you can simply run `power-playlists` to interact with the
tool, including seeing the usage info:

``` bash
> power-playlists
Usage: power-playlists [OPTIONS] COMMAND [ARGS]...

Options:
  ...
  --help          Show this message and exit.

Commands:
  ...
  run      Run a single iteration of the playlist updates.
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
the `~/.power-playlists/userconf` directory. You can open this in your
favorite text editor like:

    > vi ~/.power-playlists/userconf/myconf.yaml

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

``` yaml
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

Full documentation can be found on the [Power Playlists page on GitHub
Pages](https://xkrogen.github.io/power-playlists). A full reference of
all supported node types is also available in the [Node
Reference](https://xkrogen.github.io/power-playlists/powerplaylists.html#node-reference).

## Examples

Power Playlists supports many advanced features through its flexible node system. Below are several example configurations demonstrating different capabilities, from basic filtering to complex multi-stage processing with dynamic templates.

### Basic Filtering and Combination

This example shows how to filter tracks by time and liked status, then combine and organize them:

<details>
<summary>Click to expand: basic-filtering.yaml</summary>

```yaml
# Basic filtering example demonstrating time-based and liked track filtering
# This configuration shows how to filter tracks by when they were added and liked status

# Input: A source playlist
MySourcePlaylist:
  type: 'playlist'
  uri: 'spotify:playlist:xxxxxxxxxxxxxxxxx'

# Filter to only tracks added in the last 30 days
RecentlyAdded:
  type: 'filter_time_added'
  input: 'MySourcePlaylist'
  days_ago: 30

# Filter to only liked/saved tracks
LikedTracks:
  type: 'is_liked'
  input: 'MySourcePlaylist'

# Combine recent and liked tracks, then sort by when they were added
RecentAndLikedCombined:
  type: 'combiner'
  inputs:
    - 'RecentlyAdded'
    - 'LikedTracks'
  combine_type: 'interleave'

# Sort the combined tracks by add date (most recent first)
SortedByAddDate:
  type: 'sort'
  input: 'RecentAndLikedCombined'
  sort_key: 'time_added'
  sort_desc: true

# Remove any duplicate tracks
Deduplicated:
  type: 'dedup'
  input: 'SortedByAddDate'

# Limit to 100 tracks and output to a new playlist
FilteredOutput:
  type: 'limit'
  input: 'Deduplicated'
  max_size: 100

FinalOutput:
  type: 'output'
  input: 'FilteredOutput'
  playlist_name: 'Recent and Liked Tracks'
```
</details>

### Dynamic Templates for Genre Organization

This example demonstrates how to use dynamic templates to apply the same processing logic to multiple playlists:

<details>
<summary>Click to expand: dynamic-template-simple.yaml</summary>

```yaml
# Dynamic template example demonstrating genre-based playlist organization
# This shows how to use templates to process multiple playlists with the same logic

GenrePlaylistTemplate:
  type: 'dynamic_template'
  template:
    # Define the template structure with placeholders
    '{genre} Source':
      type: 'playlist'
      uri: '{source_uri}'
    
    # Sort tracks by when they were added (newest first)
    '{genre} Sorted':
      type: 'sort'
      input: '{genre} Source'
      sort_key: 'time_added'
      sort_desc: true
    
    # Filter to only liked tracks
    '{genre} Liked':
      type: 'is_liked'
      input: '{genre} Sorted'
    
    # Limit to last 50 tracks
    '{genre} Recent':
      type: 'limit'
      input: '{genre} Sorted'
      max_size: 50
    
    # Output the processed playlist
    '{genre} Output':
      type: 'output'
      input: '{genre} Recent'
      playlist_name: '{genre} - Recent Favorites'
  
  # Apply the template to multiple genres
  instances:
    - genre: 'Electronic'
      source_uri: 'spotify:playlist:xxxxxxxxxxxxxxxxx'
    - genre: 'Rock'
      source_uri: 'spotify:playlist:yyyyyyyyyyyyyyyyy'
    - genre: 'Hip Hop'
      source_uri: 'spotify:playlist:zzzzzzzzzzzzzzzzz'

# Combine all genre outputs into one master playlist
AllGenresCombined:
  type: 'combine_sort_dedup_output'
  input_nodes:
    - 'Electronic Output'
    - 'Rock Output'
    - 'Hip Hop Output'
  sort_key: 'time_added'
  sort_desc: true
  output_playlist_name: 'All Genres - Recent Mix'
```
</details>

### Release Date Filtering by Decades

This example shows how to organize your music library by release time periods:

<details>
<summary>Click to expand: release-date-filtering.yaml</summary>

```yaml
# Release date filtering example demonstrating time-period based music organization
# This shows how to organize your music library by release decades

# Start with your full music library
FullLibrary:
  type: 'all_tracks'

# Filter tracks by release decades using dynamic templates
DecadePlaylistTemplate:
  type: 'dynamic_template'
  template:
    # Filter to tracks released after the start year
    '{decade} Start Filter':
      type: 'filter_release_date'
      input: 'FullLibrary'
      cutoff_time: '{start_year}'
    
    # Filter to tracks released before the end year
    '{decade} End Filter':
      type: 'filter_release_date'
      input: '{decade} Start Filter'
      cutoff_time: '{end_year}'
      keep_before: true
    
    # Sort by release date
    '{decade} Sorted':
      type: 'sort'
      input: '{decade} End Filter'
      sort_key: 'release_date'
      sort_desc: false
    
    # Output the decade playlist
    '{decade} Output':
      type: 'output'
      input: '{decade} Sorted'
      playlist_name: '{decade}s Music'
  
  instances:
    - decade: '1980'
      start_year: '1980'
      end_year: '1990'
    - decade: '1990'
      start_year: '1990'
      end_year: '2000'
    - decade: '2000'
      start_year: '2000'
      end_year: '2010'
    - decade: '2010'
      start_year: '2010'
      end_year: '2020'
    - decade: '2020'
      start_year: '2020'
      end_year: '2030'

# Create a playlist of newer releases (last 2 years)
RecentReleases:
  type: 'filter_release_date'
  input: 'FullLibrary'
  cutoff_time: '2022'

RecentReleasesSorted:
  type: 'sort'
  input: 'RecentReleases'
  sort_key: 'release_date'
  sort_desc: true

RecentReleasesOutput:
  type: 'output'
  input: 'RecentReleasesSorted'
  playlist_name: 'Recent Releases (2022+)'
```
</details>

### Complex Multi-Stage Workflow

This comprehensive example combines multiple features for advanced playlist management:

<details>
<summary>Click to expand: complex-workflow.yaml</summary>

```yaml
# Complex workflow example combining multiple Power Playlists features
# This demonstrates a comprehensive music organization system

# Input sources
ChillPlaylist:
  type: 'playlist'
  uri: 'spotify:playlist:xxxxxxxxxxxxxxxxx'

EnergeticPlaylist:
  type: 'playlist' 
  uri: 'spotify:playlist:yyyyyyyyyyyyyyyyy'

ClassicRockPlaylist:
  type: 'playlist'
  uri: 'spotify:playlist:zzzzzzzzzzzzzzzzz'

# Template for processing mood-based playlists
MoodPlaylistProcessor:
  type: 'dynamic_template'
  template:
    # Sort source playlist by add date
    '{mood} Sorted':
      type: 'sort'
      input: '{source_playlist}'
      sort_key: 'time_added'
      sort_desc: true
    
    # Get recently added tracks (last 90 days)
    '{mood} Recent':
      type: 'filter_time_added'
      input: '{mood} Sorted'
      days_ago: 90
    
    # Get liked tracks from the same source
    '{mood} Liked':
      type: 'is_liked'
      input: '{mood} Sorted'
    
    # Combine recent and liked, favoring recent tracks
    '{mood} Combined':
      type: 'combiner'
      inputs:
        - '{mood} Recent'
        - '{mood} Liked'
      combine_type: 'interleave'
    
    # Remove duplicates
    '{mood} Deduped':
      type: 'dedup'
      input: '{mood} Combined'
    
    # Limit to manageable size
    '{mood} Limited':
      type: 'limit'
      input: '{mood} Deduped'
      max_size: '{max_tracks}'
    
    # Output the processed playlist
    '{mood} Output':
      type: 'output'
      input: '{mood} Limited'
      playlist_name: '{mood} - Best Recent & Liked'
  
  instances:
    - mood: 'Chill'
      source_playlist: 'ChillPlaylist'
      max_tracks: 75
    - mood: 'Energetic'
      source_playlist: 'EnergeticPlaylist'
      max_tracks: 100
    - mood: 'Classic Rock'
      source_playlist: 'ClassicRockPlaylist'
      max_tracks: 50

# Create a master mix of all processed playlists
MasterMix:
  type: 'combine_sort_dedup_output'
  input_nodes:
    - 'Chill Output'
    - 'Energetic Output'
    - 'Classic Rock Output'
  sort_key: 'time_added'
  sort_desc: true
  output_playlist_name: 'Master Mix - All Moods'

# Create a liked-only super playlist from your full library
FullLibrary:
  type: 'all_tracks'

AllLikedTracks:
  type: 'is_liked'
  input: 'FullLibrary'

# Filter liked tracks to recent additions
RecentLikedTracks:
  type: 'filter_time_added'
  input: 'AllLikedTracks'
  days_ago: 180

# Sort and limit
RecentLikedSorted:
  type: 'sort'
  input: 'RecentLikedTracks'
  sort_key: 'time_added'
  sort_desc: true

RecentLikedLimited:
  type: 'limit'
  input: 'RecentLikedSorted'
  max_size: 200

RecentLikedOutput:
  type: 'output'
  input: 'RecentLikedLimited'
  playlist_name: 'Recent Favorites (6 months)'
```
</details>

### Sample Files

All of these examples are available as sample files in the [`samples/`](samples/) directory:

- [`samples/xkrogen.yaml`](samples/xkrogen.yaml) - Basic playlist combination
- [`samples/basic-filtering.yaml`](samples/basic-filtering.yaml) - Time-based and liked track filtering
- [`samples/dynamic-template-simple.yaml`](samples/dynamic-template-simple.yaml) - Genre organization with templates  
- [`samples/release-date-filtering.yaml`](samples/release-date-filtering.yaml) - Music organization by release decades
- [`samples/complex-workflow.yaml`](samples/complex-workflow.yaml) - Comprehensive multi-stage processing

To try any of these examples, copy them to your `~/.power-playlists/userconf/` directory and replace the placeholder URIs with your actual Spotify playlist URIs.

### Running in Daemon Mode

Power Playlists can also run continuously in daemon mode to automatically update your playlists on a schedule. See the [documentation](https://xkrogen.github.io/power-playlists) for more details on daemon mode configuration.

## Development

Power Playlists uses modern Python tooling with
[uv](https://github.com/astral-sh/uv) for dependency management and
builds. To set up a development environment:

1.  Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2.  Clone the repository
3.  Run `uv sync --all-extras` to install all dependencies including
    testing and documentation tools
4.  Run tests with `uv run python -m pytest tests/`
5.  Run the tool with `uv run power-playlists --help`

The project is configured with `pyproject.toml` and includes a lockfile
(`uv.lock`) for reproducible builds.

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
