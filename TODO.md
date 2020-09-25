Main todos:
- Add daemonization
- Add a decent README.md
- Handle duplicates, both for inputs and outputs, within nodes.py
- Update playlist description with last update time
- Make template creation better -- it shouldn't require code changes. Or at least it should be plugin-able
- Break node subtypes into separate classes.
- Increase variety of input/logic nodes.
- Create a typed wrapper around Spotipy, e.g. return a Track object instead of a dict.
- Check mod times on relevant playlists to see if updates can be skipped completely
