#!/usr/bin/env python3
"""
Graphical editor for Power Playlists YAML configuration files.

This module provides a modern web-based GUI for visually editing playlist configurations,
showing nodes as boxes with dependencies as arrows between them. The interface runs
in the user's web browser using a local HTTP server.
"""

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

import yaml

from .utils import AppConfig, UserConfig


def launch_gui_editor(app_conf: AppConfig, userconf_path: str | None = None):
    """Launch the web-based graphical configuration editor."""
    try:
        editor = WebConfigurationEditor(app_conf, userconf_path)
        editor.run()
    except Exception as e:
        # If GUI fails, show error message and exit gracefully
        print(f"Error launching graphical editor: {e}")
        print("Make sure you have a web browser available.")
        return


class ConfigurationRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the configuration editor web interface."""

    # Class variables to store configuration
    app_conf: AppConfig | None = None
    userconf_path: str | None = None

    def __init__(self, *args, **kwargs):
        self.current_config = None
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/" or path == "/index.html":
            self._serve_static_file("index.html", "text/html")
        elif path == "/api/load":
            self._handle_load_config()
        elif path == "/api/node-schema":
            self._handle_node_schema()
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/api/save":
            self._handle_save_config()
        elif path == "/api/save-as":
            self._handle_save_as_config()
        else:
            self.send_error(404, "Endpoint not found")

    def _serve_static_file(self, filename: str, content_type: str):
        """Serve static files from the web_ui directory."""
        try:
            static_dir = os.path.join(os.path.dirname(__file__), "web_ui")
            file_path = os.path.join(static_dir, filename)

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except FileNotFoundError:
            self.send_error(404, f"File not found: {filename}")
        except Exception as e:
            self.send_error(500, f"Error serving file: {str(e)}")

    def _handle_load_config(self):
        """Handle loading configuration."""
        try:
            if self.userconf_path and os.path.exists(self.userconf_path):
                user_conf = UserConfig(self.userconf_path)
                self.current_config = {"filename": os.path.basename(self.userconf_path), "data": user_conf.node_dicts}
            else:
                # Try to discover a configuration to load
                try:
                    user_configs = self.app_conf.get_user_config_files()
                    if user_configs:
                        config_path = user_configs[0]  # Load the first one found
                        user_conf = UserConfig(config_path)
                        self.current_config = {"filename": os.path.basename(config_path), "data": user_conf.node_dicts}
                    else:
                        # No config found, return empty
                        self.current_config = {"filename": "new_config.yaml", "data": {}}
                except ValueError:
                    # No config directory found, return empty
                    self.current_config = {"filename": "new_config.yaml", "data": {}}

            self._send_json_response(200, self.current_config)
        except Exception as e:
            self._send_json_response(500, {"error": f"Failed to load configuration: {str(e)}"})

    def _handle_node_schema(self):
        """Handle requests for node schema information."""
        try:
            node_schemas = {
                "playlist": {
                    "name": "Playlist",
                    "description": "A source node representing tracks from a playlist",
                    "icon": "♫",
                    "color": "#8E44AD",
                    "properties": {
                        "uri": {
                            "type": "text",
                            "required": True,
                            "description": "Playlist URI (spotify:playlist:xxxxx)",
                        }
                    },
                },
                "liked_tracks": {
                    "name": "Liked Tracks",
                    "description": "All liked/saved tracks",
                    "icon": "❤️",
                    "color": "#E74C3C",
                    "properties": {},
                },
                "all_tracks": {
                    "name": "All Tracks",
                    "description": "All tracks from multiple playlists",
                    "icon": "🎵",
                    "color": "#9B59B6",
                    "properties": {},
                },
                "output": {
                    "name": "Output",
                    "description": "Save tracks to a playlist",
                    "icon": "📤",
                    "color": "#2ECC71",
                    "properties": {
                        "input": {"type": "node_reference", "required": True, "description": "Input node"},
                        "playlist_name": {"type": "text", "required": True, "description": "Name of output playlist"},
                        "public": {
                            "type": "boolean",
                            "required": False,
                            "description": "Make playlist public",
                            "default": False,
                        },
                    },
                },
                "combiner": {
                    "name": "Combiner",
                    "description": "Combine tracks from multiple inputs",
                    "icon": "➕",
                    "color": "#F39C12",
                    "properties": {
                        "inputs": {"type": "node_list", "required": True, "description": "List of input nodes"}
                    },
                },
                "limit": {
                    "name": "Limit",
                    "description": "Limit number of tracks",
                    "icon": "🔢",
                    "color": "#34495E",
                    "properties": {
                        "input": {"type": "node_reference", "required": True, "description": "Input node"},
                        "size": {"type": "integer", "required": True, "description": "Maximum number of tracks"},
                    },
                },
                "sort": {
                    "name": "Sort",
                    "description": "Sort tracks by various criteria",
                    "icon": "🔀",
                    "color": "#3498DB",
                    "properties": {
                        "input": {"type": "node_reference", "required": True, "description": "Input node"},
                        "sort_key": {
                            "type": "select",
                            "required": True,
                            "description": "What to sort by",
                            "options": ["time_added", "name", "artist", "album", "release_date"],
                        },
                        "sort_desc": {
                            "type": "boolean",
                            "required": False,
                            "description": "Sort descending",
                            "default": False,
                        },
                    },
                },
                "filter_eval": {
                    "name": "Filter (Eval)",
                    "description": "Filter using Python expression",
                    "icon": "🔍",
                    "color": "#E67E22",
                    "properties": {
                        "input": {"type": "node_reference", "required": True, "description": "Input node"},
                        "predicate": {
                            "type": "text",
                            "required": True,
                            "description": "Python expression (track as 't')",
                        },
                    },
                },
                "filter_time_added": {
                    "name": "Filter (Time Added)",
                    "description": "Filter by when tracks were added",
                    "icon": "⏰",
                    "color": "#16A085",
                    "properties": {
                        "input": {"type": "node_reference", "required": True, "description": "Input node"},
                        "days_ago": {
                            "type": "integer",
                            "required": False,
                            "description": "Days ago (alternative to cutoff_time)",
                        },
                        "cutoff_time": {
                            "type": "text",
                            "required": False,
                            "description": "ISO date (alternative to days_ago)",
                        },
                        "only_before": {
                            "type": "boolean",
                            "required": False,
                            "description": "Keep only tracks before cutoff",
                            "default": False,
                        },
                    },
                },
                "filter_release_date": {
                    "name": "Filter (Release Date)",
                    "description": "Filter by album release date",
                    "icon": "📅",
                    "color": "#8E44AD",
                    "properties": {
                        "input": {"type": "node_reference", "required": True, "description": "Input node"},
                        "days_ago": {
                            "type": "integer",
                            "required": False,
                            "description": "Days ago (alternative to cutoff_time)",
                        },
                        "cutoff_time": {
                            "type": "text",
                            "required": False,
                            "description": "ISO date (alternative to days_ago)",
                        },
                        "only_before": {
                            "type": "boolean",
                            "required": False,
                            "description": "Keep only tracks before cutoff",
                            "default": False,
                        },
                    },
                },
                "dedup": {
                    "name": "Deduplicate",
                    "description": "Remove duplicate tracks",
                    "icon": "🎯",
                    "color": "#95A5A6",
                    "properties": {
                        "input": {"type": "node_reference", "required": True, "description": "Input node"},
                        "id_property": {
                            "type": "text",
                            "required": False,
                            "description": "Property to use for deduplication",
                            "default": "uri",
                        },
                    },
                },
                "is_liked": {
                    "name": "Is Liked",
                    "description": "Filter to only liked tracks",
                    "icon": "💖",
                    "color": "#E91E63",
                    "properties": {"input": {"type": "node_reference", "required": True, "description": "Input node"}},
                },
            }

            self._send_json_response(200, {"schemas": node_schemas})
        except Exception as e:
            self._send_json_response(500, {"error": f"Failed to get node schema: {str(e)}"})

    def _handle_save_config(self):
        """Handle saving current configuration."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            config_data = json.loads(post_data.decode("utf-8"))

            # Validate the configuration first
            validation_errors = self._validate_config_data(config_data["data"])
            if validation_errors:
                self._send_json_response(
                    400, {"error": f"Configuration validation failed: {'; '.join(validation_errors)}"}
                )
                return

            if self.userconf_path:
                save_path = self.userconf_path
            else:
                # Use the first available config or create a new one
                try:
                    user_configs = self.app_conf.get_user_config_files()
                    save_path = (
                        user_configs[0]
                        if user_configs
                        else os.path.join(self.app_conf.user_config_dir, "new_config.yaml")
                    )
                except ValueError:
                    # Create default directory if it doesn't exist
                    os.makedirs(self.app_conf.user_config_dir, exist_ok=True)
                    save_path = os.path.join(self.app_conf.user_config_dir, "new_config.yaml")

            self._write_yaml_config(save_path, config_data["data"])
            self._send_json_response(200, {"message": "Configuration saved successfully"})
        except Exception as e:
            self._send_json_response(400, {"error": f"Failed to save configuration: {str(e)}"})

    def _handle_save_as_config(self):
        """Handle saving configuration with a new filename."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            config_data = json.loads(post_data.decode("utf-8"))

            # Validate the configuration first
            validation_errors = self._validate_config_data(config_data["data"])
            if validation_errors:
                self._send_json_response(
                    400, {"error": f"Configuration validation failed: {'; '.join(validation_errors)}"}
                )
                return

            filename = config_data.get("filename", "new_config.yaml")
            if not filename.endswith(".yaml"):
                filename += ".yaml"

            # Ensure the directory exists
            os.makedirs(self.app_conf.user_config_dir, exist_ok=True)
            save_path = os.path.join(self.app_conf.user_config_dir, filename)

            self._write_yaml_config(save_path, config_data["data"])
            self.userconf_path = save_path  # Update current file path
            self._send_json_response(200, {"message": f"Configuration saved as {filename}"})
        except Exception as e:
            self._send_json_response(400, {"error": f"Failed to save configuration: {str(e)}"})

    def _validate_config_data(self, config_data: dict[str, Any]) -> list[str]:
        """Validate configuration data and return list of errors."""
        errors = []

        if not isinstance(config_data, dict):
            errors.append("Configuration must be a dictionary")
            return errors

        if len(config_data) == 0:
            errors.append("Configuration cannot be empty")
            return errors

        # Get valid node types
        valid_node_types = {
            "playlist",
            "liked_tracks",
            "all_tracks",
            "output",
            "combiner",
            "limit",
            "sort",
            "filter_eval",
            "filter_time_added",
            "filter_release_date",
            "dedup",
            "is_liked",
            "dynamic_template",
            "combine_sort_dedup_output",
        }

        # Validate each node
        for node_id, node_data in config_data.items():
            if not isinstance(node_data, dict):
                errors.append(f"Node '{node_id}' must be a dictionary")
                continue

            if "type" not in node_data:
                errors.append(f"Node '{node_id}' is missing required 'type' field")
                continue

            node_type = node_data["type"]
            if node_type not in valid_node_types:
                errors.append(f"Node '{node_id}' has invalid type '{node_type}'")
                continue

            # Validate required properties based on node type
            node_errors = self._validate_node_properties(node_id, node_type, node_data)
            errors.extend(node_errors)

        return errors

    def _validate_node_properties(self, node_id: str, node_type: str, node_data: dict) -> list[str]:
        """Validate properties for a specific node type."""
        errors: list[str] = []

        # Define required and optional properties for each node type
        node_schemas: dict[str, dict[str, list[str]]] = {
            "playlist": {"required": ["uri"], "optional": []},
            "liked_tracks": {"required": [], "optional": []},
            "all_tracks": {"required": [], "optional": []},
            "output": {"required": ["input", "playlist_name"], "optional": ["public"]},
            "combiner": {"required": ["inputs"], "optional": []},
            "limit": {"required": ["input", "size"], "optional": []},
            "sort": {"required": ["input", "sort_key"], "optional": ["sort_desc"]},
            "filter_eval": {"required": ["input", "predicate"], "optional": []},
            "filter_time_added": {"required": ["input"], "optional": ["days_ago", "cutoff_time", "only_before"]},
            "filter_release_date": {"required": ["input"], "optional": ["days_ago", "cutoff_time", "only_before"]},
            "dedup": {"required": ["input"], "optional": ["id_property"]},
            "is_liked": {"required": ["input"], "optional": []},
            "dynamic_template": {"required": [], "optional": []},  # Complex validation needed
            "combine_sort_dedup_output": {
                "required": ["inputs", "playlist_name", "sort_key"],
                "optional": ["sort_desc", "public", "size"],
            },
        }

        if node_type not in node_schemas:
            return errors

        schema = node_schemas[node_type]

        # Check required properties
        for req_prop in schema["required"]:
            if req_prop not in node_data:
                errors.append(f"Node '{node_id}' is missing required property '{req_prop}'")

        # Validate specific property values
        if node_type == "sort" and "sort_key" in node_data:
            valid_sort_keys = ["time_added", "name", "artist", "album", "release_date"]
            if node_data["sort_key"] not in valid_sort_keys:
                valid_keys_str = ", ".join(valid_sort_keys)
                errors.append(
                    f"Node '{node_id}' has invalid sort_key '{node_data['sort_key']}'. Valid values: {valid_keys_str}"
                )

        if "sort_desc" in node_data and not isinstance(node_data["sort_desc"], bool):
            try:
                # Try to convert to boolean
                bool_val = str(node_data["sort_desc"]).lower() in ("true", "1", "yes", "on")
                node_data["sort_desc"] = bool_val
            except Exception:
                errors.append(f"Node '{node_id}' property 'sort_desc' must be a boolean")

        if "public" in node_data and not isinstance(node_data["public"], bool):
            try:
                # Try to convert to boolean
                bool_val = str(node_data["public"]).lower() in ("true", "1", "yes", "on")
                node_data["public"] = bool_val
            except Exception:
                errors.append(f"Node '{node_id}' property 'public' must be a boolean")

        if "size" in node_data:
            try:
                int(node_data["size"])
            except ValueError:
                errors.append(f"Node '{node_id}' property 'size' must be an integer")

        # Special validation for time-based filters
        if node_type in ["filter_time_added", "filter_release_date"]:
            has_days_ago = "days_ago" in node_data
            has_cutoff_time = "cutoff_time" in node_data
            if not has_days_ago and not has_cutoff_time:
                errors.append(f"Node '{node_id}' must have either 'days_ago' or 'cutoff_time' property")
            elif has_days_ago and has_cutoff_time:
                errors.append(f"Node '{node_id}' cannot have both 'days_ago' and 'cutoff_time' properties")

        return errors

    def _write_yaml_config(self, file_path: str, config_data: dict[str, Any]):
        """Write configuration data to a YAML file."""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def _send_json_response(self, status_code: int, data: dict[str, Any]):
        """Send a JSON response."""
        json_data = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(json_data)))
        self.end_headers()
        self.wfile.write(json_data)


class WebConfigurationEditor:
    """Web-based configuration editor that runs a local HTTP server."""

    def __init__(self, app_conf: AppConfig, userconf_path: str | None = None):
        self.app_conf = app_conf
        self.userconf_path = userconf_path
        self.httpd = None
        self.port = 8080

    def run(self):
        """Start the web server and open the browser."""
        # Find an available port
        self.port = self._find_available_port()

        # Set class variables for the handler
        ConfigurationRequestHandler.app_conf = self.app_conf
        ConfigurationRequestHandler.userconf_path = self.userconf_path

        try:
            self.httpd = HTTPServer(("localhost", self.port), ConfigurationRequestHandler)
            print(f"Starting Power Playlists Configuration Editor on http://localhost:{self.port}")

            # Open browser in a separate thread
            browser_thread = threading.Thread(target=self._open_browser)
            browser_thread.daemon = True
            browser_thread.start()

            # Start server
            print("Press Ctrl+C to stop the server")
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
        except Exception as e:
            print(f"Error starting server: {e}")
        finally:
            if self.httpd:
                self.httpd.shutdown()
                self.httpd.server_close()

    def _find_available_port(self) -> int:
        """Find an available port starting from 8080."""
        import socket

        for port in range(8080, 8090):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", port))
                    return port
            except OSError:
                continue
        raise RuntimeError("No available ports found in range 8080-8089")

    def _open_browser(self):
        """Open the web browser after a short delay."""
        import time

        time.sleep(1)  # Give the server time to start
        try:
            webbrowser.open(f"http://localhost:{self.port}")
        except Exception as e:
            print(f"Could not open browser automatically: {e}")
            print(f"Please manually open http://localhost:{self.port} in your web browser")
