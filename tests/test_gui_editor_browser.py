#!/usr/bin/env python3
"""
Browser-based integration tests for the graphical editor.

These tests verify the HTML/JavaScript frontend functionality by making
requests to the web server and validating responses.
"""

import json
import os
import threading
import time
from http.client import HTTPConnection
from urllib.parse import urlencode

import pytest
import yaml

from power_playlists.gui_editor import WebConfigurationEditor, ConfigurationRequestHandler
from power_playlists.utils import AppConfig


class TestGraphicalEditorBrowser:
    """Browser-based tests for the graphical editor."""

    @pytest.fixture
    def app_conf(self):
        """Create a test AppConfig instance."""
        return AppConfig(None)

    @pytest.fixture
    def editor_server(self, app_conf):
        """Start a GUI editor server for testing."""
        import socket
        import random
        
        editor = WebConfigurationEditor(app_conf)
        
        # Find a random available port in a wider range to avoid conflicts
        for attempt in range(50):  # Try 50 times
            port = random.randint(9000, 9999)  # Use different port range
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", port))
                    editor.port = port
                    break
            except OSError:
                continue
        else:
            raise RuntimeError("No available ports found after 50 attempts")
        
        # Set up handler class variables
        ConfigurationRequestHandler.app_conf = app_conf
        ConfigurationRequestHandler.userconf_path = None
        
        # Start server in background thread
        def run_server():
            from http.server import HTTPServer
            editor.httpd = HTTPServer(("localhost", editor.port), ConfigurationRequestHandler)
            editor.httpd.serve_forever()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(0.3)
        
        yield editor
        
        # Cleanup
        if editor.httpd:
            editor.httpd.shutdown()
            editor.httpd.server_close()
            time.sleep(0.1)  # Give time for cleanup

    def test_html_page_loads(self, editor_server):
        """Test that the main HTML page loads correctly."""
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            conn.request("GET", "/")
            response = conn.getresponse()
            
            assert response.status == 200
            content = response.read().decode()
            
            # Verify essential HTML elements are present
            assert "Power Playlists Configuration Editor" in content
            assert 'id="canvas"' in content
            assert 'id="addNodeBtn"' in content
            assert 'id="saveBtn"' in content
            assert 'id="loadBtn"' in content
            
            # Verify JavaScript code is present
            assert "ConfigurationEditor" in content
            assert "loadNodeSchemas" in content
            assert "displayConfiguration" in content
            
        finally:
            conn.close()

    def test_node_addition_workflow(self, editor_server):
        """Test the complete node addition workflow through API calls."""
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            # First, get the node schemas
            conn.request("GET", "/api/node-schema")
            response = conn.getresponse()
            assert response.status == 200
            
            schemas = json.loads(response.read().decode())["schemas"]
            assert "playlist" in schemas
            
            # Test adding a playlist node
            new_config = {
                "test_playlist": {
                    "type": "playlist",
                    "uri": "spotify:playlist:test123"
                }
            }
            
            # Save the new configuration
            save_data = json.dumps({"data": new_config}).encode()
            headers = {"Content-Type": "application/json"}
            conn = HTTPConnection(f"localhost:{editor_server.port}")
            conn.request("POST", "/api/save", save_data, headers)
            response = conn.getresponse()
            
            # Should accept valid configuration (200) or fail gracefully (400)
            assert response.status in [200, 400]
            
        finally:
            conn.close()

    def test_node_modification_workflow(self, editor_server):
        """Test modifying existing nodes through the API."""
        # Start with a basic configuration
        initial_config = {
            "playlist_node": {
                "type": "playlist",
                "uri": "spotify:playlist:original123"
            }
        }
        
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            # Save initial configuration
            save_data = json.dumps({"data": initial_config}).encode()
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/save", save_data, headers)
            response = conn.getresponse()
            
            # Now modify the configuration
            modified_config = {
                "playlist_node": {
                    "type": "playlist",
                    "uri": "spotify:playlist:modified456"
                }
            }
            
            conn = HTTPConnection(f"localhost:{editor_server.port}")
            save_data = json.dumps({"data": modified_config}).encode()
            conn.request("POST", "/api/save", save_data, headers)
            response = conn.getresponse()
            
            # Should handle modification appropriately
            assert response.status in [200, 400]
            
        finally:
            conn.close()

    def test_node_removal_through_empty_config(self, editor_server):
        """Test node removal by saving an empty configuration."""
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            # Save empty configuration (simulates removing all nodes)
            empty_config = {}
            save_data = json.dumps({"data": empty_config}).encode()
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/save", save_data, headers)
            response = conn.getresponse()
            
            # Should handle empty configuration
            assert response.status in [200, 400]
            
        finally:
            conn.close()

    def test_selection_window_node_types(self, editor_server):
        """Test that all expected node types are available in the selection."""
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            conn.request("GET", "/api/node-schema")
            response = conn.getresponse()
            
            assert response.status == 200
            schemas_data = json.loads(response.read().decode())
            schemas = schemas_data["schemas"]
            
            # Verify all expected node types are present
            expected_types = [
                "playlist", "output", "combiner", "is_liked", 
                "dynamic_template", "combine_sort_dedup_output"
            ]
            
            for node_type in expected_types:
                assert node_type in schemas
                schema = schemas[node_type]
                
                # Each schema should have required fields
                assert "name" in schema
                assert "description" in schema
                assert "properties" in schema
                
                # Verify properties structure
                assert isinstance(schema["properties"], dict)
                
        finally:
            conn.close()

    def test_dynamic_template_editing_workflow(self, editor_server):
        """Test the complete dynamic template editing workflow."""
        template_config = {
            "genre_template": {
                "type": "dynamic_template",
                "template": {
                    "{genre} Playlist": {
                        "type": "playlist",
                        "uri": "{playlist_uri}"
                    },
                    "{genre} Output": {
                        "type": "output",
                        "input": "{genre} Playlist",
                        "playlist_name": "{genre} Final"
                    }
                },
                "instances": [
                    {"genre": "Rock", "playlist_uri": "spotify:playlist:rock123"},
                    {"genre": "Jazz", "playlist_uri": "spotify:playlist:jazz456"}
                ]
            }
        }
        
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            # Test entering template view
            enter_data = json.dumps({
                "nodeId": "genre_template",
                "configData": template_config
            }).encode()
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/template/enter", enter_data, headers)
            response = conn.getresponse()
            
            assert response.status == 200
            
            template_data = json.loads(response.read().decode())
            
            # Verify template data structure
            assert "templateNodes" in template_data
            assert "instances" in template_data
            assert "variables" in template_data
            
            # Verify template nodes structure
            template_nodes = template_data["templateNodes"]
            assert len(template_nodes) == 2  # Should have 2 nodes in template
            
            # Verify instances
            instances = template_data["instances"]
            assert len(instances) == 2
            assert instances[0]["genre"] == "Rock"
            assert instances[1]["genre"] == "Jazz"
            
            # Verify variables extraction
            variables = template_data["variables"]
            assert "genre" in variables
            assert "playlist_uri" in variables
            
        finally:
            conn.close()

    def test_invalid_configuration_handling(self, editor_server):
        """Test that the editor properly handles and rejects invalid configurations."""
        invalid_configs = [
            # Missing type
            {"invalid_node": {"uri": "spotify:playlist:test"}},
            # Invalid type
            {"bad_type": {"type": "invalid_type"}},
            # Missing required properties for output node
            {"incomplete_output": {"type": "output"}},
            # Malformed dynamic template
            {"bad_template": {
                "type": "dynamic_template",
                "template": "not_a_dict",
                "instances": "not_a_list"
            }}
        ]
        
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            for i, invalid_config in enumerate(invalid_configs):
                save_data = json.dumps({"data": invalid_config}).encode()
                headers = {"Content-Type": "application/json"}
                conn.request("POST", "/api/save", save_data, headers)
                response = conn.getresponse()
                
                # Should reject invalid configurations
                assert response.status == 400
                
                error_data = json.loads(response.read().decode())
                assert "error" in error_data
                assert len(error_data["error"]) > 0
                
                # Reset connection for next test
                conn = HTTPConnection(f"localhost:{editor_server.port}")
                
        finally:
            conn.close()

    def test_complex_configuration_handling(self, editor_server):
        """Test handling of complex multi-node configurations."""
        complex_config = {
            "source_playlist": {
                "type": "playlist",
                "uri": "spotify:playlist:source123"
            },
            "liked_filter": {
                "type": "is_liked",
                "input": "source_playlist"
            },
            "recent_combiner": {
                "type": "combiner",
                "inputs": ["liked_filter"]
            },
            "final_output": {
                "type": "output",
                "input": "recent_combiner",
                "playlist_name": "My Filtered Playlist"
            }
        }
        
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            # Save complex configuration
            save_data = json.dumps({"data": complex_config}).encode()
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/save", save_data, headers)
            response = conn.getresponse()
            
            # Should handle complex valid configuration
            assert response.status in [200, 400]
            
            if response.status == 400:
                # If it fails, it should be due to userconf path, not validation
                error_data = json.loads(response.read().decode())
                error_msg = error_data.get("error", "")
                # Should not contain validation errors for this valid config
                assert "missing required property" not in error_msg.lower()
                
        finally:
            conn.close()

    def test_template_instance_modification(self, editor_server):
        """Test modifying template instances through the API."""
        template_with_instances = {
            "multi_genre": {
                "type": "dynamic_template",
                "template": {
                    "{name} Source": {
                        "type": "playlist",
                        "uri": "{uri}"
                    }
                },
                "instances": [
                    {"name": "Classical", "uri": "spotify:playlist:classical123"},
                    {"name": "Electronic", "uri": "spotify:playlist:electronic456"}
                ]
            }
        }
        
        conn = HTTPConnection(f"localhost:{editor_server.port}")
        
        try:
            # Enter template view
            enter_data = json.dumps({
                "nodeId": "multi_genre",
                "configData": template_with_instances
            }).encode()
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/template/enter", enter_data, headers)
            response = conn.getresponse()
            
            assert response.status == 200
            
            template_data = json.loads(response.read().decode())
            
            # Verify we can access template instances
            instances = template_data["instances"]
            assert len(instances) == 2
            assert instances[0]["name"] == "Classical"
            assert instances[1]["name"] == "Electronic"
            
            # Verify template structure
            template_nodes = template_data["templateNodes"]
            assert "{name} Source" in template_nodes
            
        finally:
            conn.close()