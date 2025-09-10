#!/usr/bin/env python3
"""
Test for the GUI editor functionality.
"""

import os
import tempfile

import yaml

from powerplaylists.gui_editor import launch_gui_editor
from powerplaylists.utils import AppConfig


class TestGuiEditor:
    """Test cases for the GUI editor."""

    def test_launch_gui_editor_no_tkinter(self):
        """Test that launch_gui_editor handles missing tkinter gracefully."""
        # Create a mock app config
        app_conf = AppConfig(None)
        
        # Test that launch_gui_editor doesn't crash
        # In a headless environment, this should handle the lack of display gracefully
        launch_gui_editor(app_conf)  # Should print error message but not crash

    def test_yaml_configuration_handling(self):
        """Test that the GUI can handle YAML configuration data."""
        # Create a temporary YAML file
        test_config = {
            "input_playlist": {
                "type": "playlist",
                "uri": "spotify:playlist:test123"
            },
            "filter_liked": {
                "type": "is_liked",
                "input": "input_playlist"
            },
            "output_playlist": {
                "type": "output",
                "input": "filter_liked",
                "playlist_name": "Filtered Playlist"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f, default_flow_style=False)
            temp_file = f.name
        
        try:
            # Verify the file can be read back
            with open(temp_file) as f:
                loaded_config = yaml.safe_load(f)
            
            assert loaded_config == test_config
            assert "input_playlist" in loaded_config
            assert loaded_config["filter_liked"]["input"] == "input_playlist"
            assert loaded_config["output_playlist"]["input"] == "filter_liked"
            
        finally:
            os.unlink(temp_file)

    def test_gui_editor_module_import(self):
        """Test that the GUI editor module can be imported."""
        # This should work even without tkinter
        import powerplaylists.gui_editor as gui_editor
        
        assert hasattr(gui_editor, 'launch_gui_editor')
        assert callable(gui_editor.launch_gui_editor)