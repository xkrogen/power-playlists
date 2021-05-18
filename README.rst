Power Playlists
=====================================================

What is it?
--------------

Power Playlists is a command-line tool written in Python that allows for the creation of dynamic playlists in Spotify,
i.e., playlists that are defined as filters and combinations of other playlists or sources. You create playlist definitions
in a YAML config file, and whenever the command-line tool is run, it will sync your Spotify playlists to match their
definitions. Daemonization is also supported to run the tool as a background process with periodic updates.

Quick Start Guide
-----------------

First, make sure you have a functioning Python 3 installation. Then, install ``power-playlists`` from PyPi::

  > pip install power-playlists

After this you can simply run ``power-playlists`` to interact with the tool, including seeing the usage info:

.. code-block:: bash

  > power-playlists
  Usage: power-playlists [OPTIONS] COMMAND [ARGS]...

  Options:
    ...
    --help          Show this message and exit.

  Commands:
    ...
    run      Run a single iteration of the playlist updates.

Out of the box, nothing interesting will happen. Get started by creating a `YAML configuration file <https://yaml.org/>`_
to contain details about your Spotify account and the playlists you want to define. If you need a primer on YAML,
check out `Wikipedia <https://en.wikipedia.org/wiki/YAML#Syntax>`_ or the guide provided by
`Camel <https://camel.readthedocs.io/en/latest/yamlref.html>`_. For the purpose of defining your playlists, you only
need to understand `sequences <https://camel.readthedocs.io/en/latest/yamlref.html#sequences>`_ and
`mappings <https://camel.readthedocs.io/en/latest/yamlref.html#mappings>`_. Really, just looking at some examples
will probably be sufficient -- YAML is designed to be intuitive.

By default, ``power-playlists`` will search for YAML config files within the ``~/.power-playlists/userconf``
directory. You can open this in your favorite text editor like::

  > vi ~/.power-playlists/userconf/myconf.yaml

At the top level, this must be a mapping, each key-value pair of which will define a ``node``. Nodes are the building
blocks of your playlist definitions, such as a ``playlist`` node (an input consisting of all of the tracks from a
playlist), an ``is_liked`` node (filters to only tracks which have been liked/saved), or an ``output`` node (saves the
tracks to a playlist).

Each YAML file should contain all of the playlist definitions for a single user. When you first run
``power-playlists``, you'll be prompted to log in to your Spotify account. A token allowing ``power-playlists``
to access your account will be stored based on the name of the YAML file, so you'll have to log in once for each
file, and if the name of the file changes, you will have to re-login.

Let's look at a simple example:

.. code-block:: yaml

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
    playlist_name: 'Playlist A + B Combined'

This will take two playlists, combine them, and save the result as a new playlist. Input playlists
are generally referred to by their URI, or unique identifier, which can be found by right-clicking
on a playlist and going to ``Share > Copy Spotify URI``.

Full documentation can be found on the `Power Playlists page on Read the Docs <https://power-playlists.readthedocs.io>`_.

TODO get the Python docs set up, link to all nodes
TODO show a more complex example involving template
TODO describe daemonization

The Backstory
--------------

Remember `Smart Playlists from iTunes <https://support.apple.com/guide/itunes/create-delete-and-use-smart-playlists-itns3001/windows>`_\?
They're pretty much the *only* thing I miss about iTunes, otherwise being grateful to be fully devoted to the Church of Spotify.
I've found two projects along the direction of enhancing Spotify with such functionality:

* `Smarter Playlists <http://smarterplaylists.playlistmachinery.com/>`_ - This one really resonated with me. The graph-based
  playlist designer was intuitive and powerful, if a little clunky. By the time I came across the project in 2020, it had
  clearly fallen out of maintenance and various things were broken.
* `PLYLST <https://plylst.app/>`_ - This was another good attempt, with a much shinier and modern UI, though it came at the
  cost of decreased flexibility and functionality. As of February 2021, it has shut down, a victim of its own success as a
  personal side project grew too big for the server costs to make sense.

Both of these were great projects in their own right! But, and this might just be the programmer in me talking, I always
felt like something fundamental was missing. Automating playlist creation is fantastic and opens up a whole world of
possibilities, but graphical interfaces mean that creating and editing playlist definitions was always a manual and
laborious process. If I had many similar but slightly different definitions, and I wanted to make a tweak, I had to
go through and make the same tweak many times, navigating the UI each time. I longed for config-driven playlist
definitions. Thus Power Playlists was born, out of a desire to create an automated playlist manager that was designed
to be *flexible* and *extensible*, with a config-driven approach that allowed for templating.

Unfortunately, I know nothing about programming for the web, so instead of a shiny UI, all you get is a command-line
tool. But this also means it's fairly easy to get started on your own, and you don't run the risk of setting up a bunch
of custom playlist definitions and building your music library around them -- only to find out that one day, the
application breaks and doesn't get fixed, or has to shut down.
