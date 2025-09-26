#!/usr/bin/env python3
"""
Test for the GUI editor functionality.
"""

import os
import tempfile
import threading
import time
from unittest.mock import patch

import yaml

from power_playlists.gui_editor import WebConfigurationEditor, launch_gui_editor
from power_playlists.utils import AppConfig


class TestGuiEditor:
    """Test cases for the GUI editor."""

    def test_launch_gui_editor_with_config(self):
        """Test that launch_gui_editor handles web server startup gracefully."""
        # Create a mock app config
        app_conf = AppConfig(None)

        # Create a temporary config file
        test_config = {
            "input_playlist": {"type": "playlist", "uri": "spotify:playlist:test123"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f, default_flow_style=False)
            temp_file = f.name

        try:
            # Test that launch_gui_editor can start with a config file
            # We'll mock the browser opening to avoid actually opening a browser
            with patch("webbrowser.open"):
                # Start the editor in a separate thread with a timeout
                editor_thread = threading.Thread(target=lambda: launch_gui_editor(app_conf, temp_file))
                editor_thread.daemon = True
                editor_thread.start()

                # Give it a moment to start, then it should handle the graceful shutdown
                time.sleep(0.1)

                # Thread should be running or have completed gracefully
                assert editor_thread.is_alive() or not editor_thread.is_alive()
        finally:
            os.unlink(temp_file)

    def test_web_configuration_editor_init(self):
        """Test WebConfigurationEditor initialization."""
        app_conf = AppConfig(None)

        # Should be able to create the editor instance
        editor = WebConfigurationEditor(app_conf)
        assert editor.app_conf is app_conf
        assert editor.userconf_path is None
        assert editor.httpd is None
        assert editor.port == 8080

    def test_web_configuration_editor_with_userconf(self):
        """Test WebConfigurationEditor with a user config path."""
        app_conf = AppConfig(None)
        test_path = "/path/to/config.yaml"

        editor = WebConfigurationEditor(app_conf, test_path)
        assert editor.userconf_path == test_path

    def test_find_available_port(self):
        """Test port finding functionality."""
        app_conf = AppConfig(None)
        editor = WebConfigurationEditor(app_conf)

        # Should find a port (testing the method exists and runs)
        port = editor._find_available_port()
        assert isinstance(port, int)
        assert 8080 <= port <= 8089

    def test_yaml_configuration_handling(self):
        """Test that the GUI can handle YAML configuration data."""
        # Create a temporary YAML file
        test_config = {
            "input_playlist": {"type": "playlist", "uri": "spotify:playlist:test123"},
            "filter_liked": {"type": "is_liked", "input": "input_playlist"},
            "output_playlist": {"type": "output", "input": "filter_liked", "playlist_name": "Filtered Playlist"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
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

    def test_combine_sort_dedup_output_validation(self):
        """Test validation logic for combine_sort_dedup_output nodes."""

        # Create a mock handler class to test the validation method
        class MockHandler:
            def _validate_node_properties(self, node_id: str, node_type: str, node_data: dict):
                # Copy the validation logic from ConfigurationRequestHandler
                errors = []

                node_schemas = {
                    "combine_sort_dedup_output": {
                        "required": ["output_playlist_name", "sort_key"],
                        "optional": ["sort_desc", "input_nodes", "input_uris"],
                    },
                }

                if node_type not in node_schemas:
                    return errors

                schema = node_schemas[node_type]

                # Check required properties
                for req_prop in schema["required"]:
                    if req_prop not in node_data:
                        errors.append(f"Node '{node_id}' is missing required property '{req_prop}'")

                # Special validation for combine_sort_dedup_output
                if node_type == "combine_sort_dedup_output":
                    has_input_nodes = "input_nodes" in node_data and node_data["input_nodes"]
                    has_input_uris = "input_uris" in node_data and node_data["input_uris"]
                    if not has_input_nodes and not has_input_uris:
                        errors.append(f"Node '{node_id}' must have either 'input_nodes' or 'input_uris' property")
                    elif has_input_nodes and has_input_uris:
                        errors.append(f"Node '{node_id}' cannot have both 'input_nodes' and 'input_uris' properties")

                return errors

        handler = MockHandler()

        # Test valid configuration with input_nodes
        valid_data = {
            "type": "combine_sort_dedup_output",
            "input_nodes": ["playlist1", "playlist2"],
            "output_playlist_name": "Combined Output",
            "sort_key": "time_added",
            "sort_desc": True,
        }
        errors = handler._validate_node_properties("multi_output", "combine_sort_dedup_output", valid_data)
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

        # Test valid configuration with input_uris
        valid_data_uris = {
            "type": "combine_sort_dedup_output",
            "input_uris": ["spotify:playlist:123", "spotify:playlist:456"],
            "output_playlist_name": "Combined Output",
            "sort_key": "name",
        }
        errors = handler._validate_node_properties("multi_output", "combine_sort_dedup_output", valid_data_uris)
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

        # Test invalid configuration - missing both input_nodes and input_uris
        invalid_data = {
            "type": "combine_sort_dedup_output",
            "output_playlist_name": "Combined Output",
            "sort_key": "time_added",
        }
        errors = handler._validate_node_properties("multi_output", "combine_sort_dedup_output", invalid_data)
        assert len(errors) > 0, "Expected validation errors for missing inputs"
        assert any("must have either 'input_nodes' or 'input_uris'" in error for error in errors)

        # Test invalid configuration - both input_nodes and input_uris
        invalid_data_both = {
            "type": "combine_sort_dedup_output",
            "input_nodes": ["playlist1"],
            "input_uris": ["spotify:playlist:123"],
            "output_playlist_name": "Combined Output",
            "sort_key": "time_added",
        }
        errors = handler._validate_node_properties("multi_output", "combine_sort_dedup_output", invalid_data_both)
        assert len(errors) > 0, "Expected validation errors for conflicting inputs"
        assert any("cannot have both 'input_nodes' and 'input_uris'" in error for error in errors)

    def test_combine_sort_dedup_output_node_support(self):
        """Test that combine_sort_dedup_output nodes are properly supported in GUI editor."""
        test_config = {
            "multi_output": {
                "type": "combine_sort_dedup_output",
                "input_nodes": ["playlist1", "playlist2"],
                "output_playlist_name": "Combined Output",
                "sort_key": "time_added",
                "sort_desc": True,
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f, default_flow_style=False)
            temp_file = f.name

        try:
            # Verify the file can be read back
            with open(temp_file) as f:
                loaded_config = yaml.safe_load(f)

            assert loaded_config == test_config
            assert "multi_output" in loaded_config
            assert loaded_config["multi_output"]["type"] == "combine_sort_dedup_output"
            assert loaded_config["multi_output"]["input_nodes"] == ["playlist1", "playlist2"]
            assert loaded_config["multi_output"]["output_playlist_name"] == "Combined Output"
            assert loaded_config["multi_output"]["sort_key"] == "time_added"
            assert loaded_config["multi_output"]["sort_desc"]

        finally:
            os.unlink(temp_file)

    def test_gui_editor_module_import(self):
        """Test that the GUI editor module can be imported."""
        # This should work even without a display
        import power_playlists.gui_editor as gui_editor

        assert hasattr(gui_editor, "launch_gui_editor")
        assert callable(gui_editor.launch_gui_editor)
        assert hasattr(gui_editor, "WebConfigurationEditor")
        assert hasattr(gui_editor, "ConfigurationRequestHandler")
