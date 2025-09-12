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

    def __init__(self, app_conf: AppConfig, userconf_path: str | None, *args, **kwargs):
        self.app_conf = app_conf
        self.userconf_path = userconf_path
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

    def _handle_save_config(self):
        """Handle saving current configuration."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            config_data = json.loads(post_data.decode("utf-8"))

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
            self._send_json_response(500, {"error": f"Failed to save configuration: {str(e)}"})

    def _handle_save_as_config(self):
        """Handle saving configuration with a new filename."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            config_data = json.loads(post_data.decode("utf-8"))

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
            self._send_json_response(500, {"error": f"Failed to save configuration: {str(e)}"})

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

        # Create server with partial application to pass parameters
        def handler(*args, **kwargs):
            return ConfigurationRequestHandler(self.app_conf, self.userconf_path, *args, **kwargs)

        try:
            self.httpd = HTTPServer(("localhost", self.port), handler)
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
