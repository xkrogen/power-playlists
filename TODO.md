Main todos:
- Add support for time-based filtering to support a "recently added" style playlist
- Add a decent README.md
- Handle duplicates, both for inputs and outputs, within nodes.py
- Update playlist description with last update time
- Check mod times on relevant playlists to see if updates can be skipped completely
- Maintain cached info to cut down on unnecessary calls. In tandem with above.
- Make template creation better -- it shouldn't require code changes. Or at least it should be plugin-able
- Increase variety of input/logic nodes.
- Create a typed wrapper around Spotipy, e.g. return a Track object instead of a dict.
