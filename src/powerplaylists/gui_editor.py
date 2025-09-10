#!/usr/bin/env python3
"""
Graphical editor for Power Playlists YAML configuration files.

This module provides a tkinter-based GUI for visually editing playlist configurations,
showing nodes as boxes with dependencies as arrows between them.
"""

import os
from typing import Any

from .utils import AppConfig, UserConfig

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk

    import yaml
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    # Create stubs to avoid type errors
    from typing import Any
    tk = Any  # type: ignore
    ttk = Any  # type: ignore
    yaml = Any  # type: ignore


def launch_gui_editor(app_conf: AppConfig):
    """Launch the graphical configuration editor."""
    if not TKINTER_AVAILABLE:
        print("Error: tkinter is not available.")
        print("The graphical editor requires tkinter, which is usually included with Python.")
        print("On some Linux distributions, you may need to install python3-tk:")
        print("  Ubuntu/Debian: sudo apt-get install python3-tk")
        print("  CentOS/RHEL: sudo yum install tkinter")
        print("  Fedora: sudo dnf install python3-tkinter")
        return

    try:
        editor = ConfigurationEditor(app_conf)
        editor.run()
    except Exception as e:
        # If GUI fails, show error message and exit gracefully
        print(f"Error launching graphical editor: {e}")
        print("Make sure you have a display available (X11 forwarding if using SSH)")
        return


# Only define GUI classes if tkinter is available
if TKINTER_AVAILABLE:

    class NodeBox:
        """Represents a visual node in the editor."""

        def __init__(self, canvas: tk.Canvas, node_id: str, node_data: dict[str, Any], x: int, y: int):
            self.canvas = canvas
            self.node_id = node_id
            self.node_data = node_data.copy()
            self.x = x
            self.y = y
            self.width = 150
            self.height = 100

            # Create visual elements
            self.rect_id = canvas.create_rectangle(
                x, y, x + self.width, y + self.height, fill="lightblue", outline="black", width=2
            )

            # Node name (large font)
            self.name_id = canvas.create_text(
                x + self.width // 2, y + 20, text=node_id, font=("Arial", 12, "bold"), width=self.width - 10
            )

            # Node properties (smaller font)
            props_text = self._format_properties()
            self.props_id = canvas.create_text(
                x + self.width // 2, y + 50, text=props_text, font=("Arial", 8), width=self.width - 10
            )

            # Bind events
            canvas.tag_bind(self.rect_id, "<Double-Button-1>", self._on_double_click)
            canvas.tag_bind(self.name_id, "<Double-Button-1>", self._on_double_click)
            canvas.tag_bind(self.props_id, "<Double-Button-1>", self._on_double_click)

        def _format_properties(self) -> str:
            """Format node properties for display."""
            props = []
            for key, value in self.node_data.items():
                if key not in ["inputs", "input"]:  # Skip inputs, they're shown as arrows
                    if isinstance(value, str) and len(value) > 20:
                        value = value[:17] + "..."
                    props.append(f"{key}: {value}")
            return "\n".join(props[:4])  # Limit to 4 lines

        def _on_double_click(self, event):
            """Handle double-click to edit properties."""
            editor = NodePropertiesEditor(self.canvas.master, self.node_id, self.node_data)
            if editor.result:
                self.node_data = editor.result
                # Update display
                props_text = self._format_properties()
                self.canvas.itemconfig(self.props_id, text=props_text)

        def get_center(self) -> tuple[int, int]:
            """Get the center point of the node box."""
            return (self.x + self.width // 2, self.y + self.height // 2)

        def contains_point(self, x: int, y: int) -> bool:
            """Check if a point is within this node box."""
            return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

        def move_to(self, x: int, y: int):
            """Move the node box to a new position."""
            dx = x - self.x
            dy = y - self.y
            self.x = x
            self.y = y

            self.canvas.move(self.rect_id, dx, dy)
            self.canvas.move(self.name_id, dx, dy)
            self.canvas.move(self.props_id, dx, dy)

    class DependencyArrow:
        """Represents a dependency arrow between nodes."""

        def __init__(self, canvas: tk.Canvas, from_node: NodeBox, to_node: NodeBox):
            self.canvas = canvas
            self.from_node = from_node
            self.to_node = to_node

            # Calculate arrow position
            from_x, from_y = from_node.get_center()
            to_x, to_y = to_node.get_center()

            # Create arrow line
            self.arrow_id = canvas.create_line(from_x, from_y, to_x, to_y, arrow=tk.LAST, fill="red", width=2)

        def update_position(self):
            """Update arrow position based on node positions."""
            from_x, from_y = self.from_node.get_center()
            to_x, to_y = self.to_node.get_center()
            self.canvas.coords(self.arrow_id, from_x, from_y, to_x, to_y)

        def delete(self):
            """Remove the arrow from the canvas."""
            self.canvas.delete(self.arrow_id)

    class NodePropertiesEditor:
        """Dialog for editing node properties."""

        def __init__(self, parent, node_id: str, node_data: dict[str, Any]):
            self.result = None

            # Create dialog window
            self.dialog = tk.Toplevel(parent)
            self.dialog.title(f"Edit Node: {node_id}")
            self.dialog.geometry("400x500")
            self.dialog.resizable(True, True)

            # Make dialog modal
            self.dialog.transient(parent)
            self.dialog.grab_set()

            # Create form elements
            self._create_widgets(node_data)

            # Center dialog
            self.dialog.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

            # Wait for dialog to close
            self.dialog.wait_window()

        def _create_widgets(self, node_data: dict[str, Any]):
            """Create form widgets for editing properties."""
            main_frame = ttk.Frame(self.dialog, padding="10")
            main_frame.grid(row=0, column=0, sticky="nsew")

            # Configure grid weights
            self.dialog.columnconfigure(0, weight=1)
            self.dialog.rowconfigure(0, weight=1)
            main_frame.columnconfigure(1, weight=1)

            self.entries = {}
            row = 0

            for key, value in node_data.items():
                if key in ["inputs", "input"]:  # Skip inputs - handled separately
                    continue

                ttk.Label(main_frame, text=f"{key}:").grid(row=row, column=0, sticky=tk.W, pady=2)

                entry = ttk.Entry(main_frame, width=40)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, sticky="ew", pady=2)

                self.entries[key] = entry
                row += 1

            # Add new property section
            ttk.Separator(main_frame, orient="horizontal").grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=10
            )
            row += 1

            ttk.Label(main_frame, text="Add new property:").grid(row=row, column=0, columnspan=2, sticky=tk.W)
            row += 1

            ttk.Label(main_frame, text="Key:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.new_key_entry = ttk.Entry(main_frame, width=40)
            self.new_key_entry.grid(row=row, column=1, sticky="ew", pady=2)
            row += 1

            ttk.Label(main_frame, text="Value:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.new_value_entry = ttk.Entry(main_frame, width=40)
            self.new_value_entry.grid(row=row, column=1, sticky="ew", pady=2)
            row += 1

            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=row, column=0, columnspan=2, pady=20)

            ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

        def _on_ok(self):
            """Handle OK button click."""
            result = {}

            # Get existing properties
            for key, entry in self.entries.items():
                value = entry.get().strip()
                if value:
                    # Try to convert to appropriate type
                    if value.lower() in ["true", "false"]:
                        result[key] = value.lower() == "true"
                    elif value.isdigit():
                        result[key] = int(value)
                    else:
                        try:
                            result[key] = float(value)
                        except ValueError:
                            result[key] = value

            # Add new property if specified
            new_key = self.new_key_entry.get().strip()
            new_value = self.new_value_entry.get().strip()
            if new_key and new_value:
                # Try to convert value to appropriate type
                if new_value.lower() in ["true", "false"]:
                    result[new_key] = new_value.lower() == "true"
                elif new_value.isdigit():
                    result[new_key] = int(new_value)
                else:
                    try:
                        result[new_key] = float(new_value)
                    except ValueError:
                        result[new_key] = new_value

            self.result = result
            self.dialog.destroy()

        def _on_cancel(self):
            """Handle Cancel button click."""
            self.dialog.destroy()

    class ConfigurationEditor:
        """Main configuration editor window."""

        def __init__(self, app_conf: AppConfig):
            self.app_conf = app_conf
            self.current_file = None
            self.nodes: dict[str, NodeBox] = {}
            self.arrows: list[DependencyArrow] = []
            self.drag_start = None
            self.drag_from_node = None

            # Create main window
            self.root = tk.Tk()
            self.root.title("Power Playlists Configuration Editor")
            self.root.geometry("1000x700")

            self._create_widgets()
            self._setup_bindings()

        def _create_widgets(self):
            """Create the main UI widgets."""
            # Menu bar
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)

            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Open", command=self._open_file)
            file_menu.add_command(label="Save", command=self._save_file)
            file_menu.add_command(label="Save As", command=self._save_as_file)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.root.quit)

            # Toolbar
            toolbar = ttk.Frame(self.root)
            toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

            ttk.Button(toolbar, text="Open", command=self._open_file).pack(side=tk.LEFT, padx=2)
            ttk.Button(toolbar, text="Save", command=self._save_file).pack(side=tk.LEFT, padx=2)
            ttk.Button(toolbar, text="Add Node", command=self._add_node).pack(side=tk.LEFT, padx=10)

            # Status bar
            self.status_var = tk.StringVar()
            self.status_var.set("Ready - Open a configuration file to begin editing")
            status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
            status_bar.pack(side=tk.BOTTOM, fill=tk.X)

            # Main canvas
            canvas_frame = ttk.Frame(self.root)
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Add scrollbars
            v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
            h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)

            self.canvas = tk.Canvas(
                canvas_frame,
                bg="white",
                scrollregion=(0, 0, 2000, 2000),
                yscrollcommand=v_scrollbar.set,
                xscrollcommand=h_scrollbar.set,
            )

            v_scrollbar.config(command=self.canvas.yview)
            h_scrollbar.config(command=self.canvas.xview)

            # Pack scrollbars and canvas
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _setup_bindings(self):
            """Setup event bindings."""
            self.canvas.bind("<Button-1>", self._on_canvas_click)
            self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        def _open_file(self):
            """Open and load a configuration file."""
            if not hasattr(self.app_conf, "user_config_dir") or not os.path.exists(self.app_conf.user_config_dir):
                config_dir = os.path.expanduser("~/.power-playlists/userconf")
            else:
                config_dir = self.app_conf.user_config_dir

            filename = filedialog.askopenfilename(
                title="Open Configuration File",
                initialdir=config_dir,
                filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            )

            if filename:
                try:
                    self._load_configuration(filename)
                    self.current_file = filename
                    self.status_var.set(f"Loaded: {os.path.basename(filename)}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load file: {str(e)}")

        def _load_configuration(self, filename: str):
            """Load configuration from file and create visual representation."""
            # Clear existing nodes and arrows
            self._clear_canvas()

            # Load YAML
            user_conf = UserConfig(filename)

            # Create nodes in a grid layout
            nodes_per_row = 4
            node_spacing_x = 200
            node_spacing_y = 150
            start_x = 50
            start_y = 50

            for i, (node_id, node_data) in enumerate(user_conf.node_dicts.items()):
                row = i // nodes_per_row
                col = i % nodes_per_row
                x = start_x + col * node_spacing_x
                y = start_y + row * node_spacing_y

                self.nodes[node_id] = NodeBox(self.canvas, node_id, node_data, x, y)

            # Create dependency arrows
            self._create_dependency_arrows()

        def _create_dependency_arrows(self):
            """Create arrows showing dependencies between nodes."""
            for _node_id, node_box in self.nodes.items():
                node_data = node_box.node_data

                # Handle single input
                if "input" in node_data and node_data["input"] in self.nodes:
                    from_node = self.nodes[node_data["input"]]
                    arrow = DependencyArrow(self.canvas, from_node, node_box)
                    self.arrows.append(arrow)

                # Handle multiple inputs
                if "inputs" in node_data:
                    inputs = node_data["inputs"]
                    if isinstance(inputs, list):
                        for input_id in inputs:
                            if input_id and input_id in self.nodes:
                                from_node = self.nodes[input_id]
                                arrow = DependencyArrow(self.canvas, from_node, node_box)
                                self.arrows.append(arrow)

        def _clear_canvas(self):
            """Clear all nodes and arrows from canvas."""
            self.canvas.delete("all")
            self.nodes.clear()
            for arrow in self.arrows:
                arrow.delete()
            self.arrows.clear()

        def _save_file(self):
            """Save current configuration to file."""
            if not self.current_file:
                self._save_as_file()
                return

            try:
                self._write_configuration(self.current_file)
                self.status_var.set(f"Saved: {os.path.basename(self.current_file)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

        def _save_as_file(self):
            """Save configuration to a new file."""
            if not hasattr(self.app_conf, "user_config_dir") or not os.path.exists(self.app_conf.user_config_dir):
                config_dir = os.path.expanduser("~/.power-playlists/userconf")
            else:
                config_dir = self.app_conf.user_config_dir

            filename = filedialog.asksaveasfilename(
                title="Save Configuration File",
                initialdir=config_dir,
                defaultextension=".yaml",
                filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            )

            if filename:
                try:
                    self._write_configuration(filename)
                    self.current_file = filename
                    self.status_var.set(f"Saved: {os.path.basename(filename)}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file: {str(e)}")

        def _write_configuration(self, filename: str):
            """Write current configuration to YAML file."""
            config_data = {}

            for node_id, node_box in self.nodes.items():
                config_data[node_id] = node_box.node_data.copy()

            with open(filename, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        def _add_node(self):
            """Add a new node to the configuration."""
            node_id = simpledialog.askstring("New Node", "Enter node ID:")
            if not node_id:
                return

            if node_id in self.nodes:
                messagebox.showerror("Error", f"Node '{node_id}' already exists!")
                return

            # Create a basic node
            node_data = {"type": "playlist", "uri": "spotify:playlist:YOUR_PLAYLIST_ID"}

            # Find a good position for the new node
            x = 50 + (len(self.nodes) % 4) * 200
            y = 50 + (len(self.nodes) // 4) * 150

            self.nodes[node_id] = NodeBox(self.canvas, node_id, node_data, x, y)
            self.status_var.set(f"Added new node: {node_id}")

        def _on_canvas_click(self, event):
            """Handle canvas click events."""
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

            # Check if clicking on a node
            clicked_node = None
            for _node_id, node_box in self.nodes.items():
                if node_box.contains_point(x, y):
                    clicked_node = node_box
                    break

            if clicked_node:
                self.drag_start = (x, y)
                self.drag_from_node = clicked_node

        def _on_canvas_drag(self, event):
            """Handle canvas drag events."""
            if self.drag_start and self.drag_from_node:
                x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
                dx = x - self.drag_start[0]
                dy = y - self.drag_start[1]

                # Move the node
                new_x = self.drag_from_node.x + dx
                new_y = self.drag_from_node.y + dy
                self.drag_from_node.move_to(new_x, new_y)

                # Update arrow positions
                for arrow in self.arrows:
                    arrow.update_position()

                self.drag_start = (x, y)

        def _on_canvas_release(self, event):
            """Handle canvas release events."""
            if self.drag_start and self.drag_from_node:
                x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

                # Check if released over another node (for creating dependencies)
                target_node = None
                for _node_id, node_box in self.nodes.items():
                    if node_box != self.drag_from_node and node_box.contains_point(x, y):
                        target_node = node_box
                        break

                if target_node:
                    # Create dependency from drag_from_node to target_node
                    self._create_dependency(self.drag_from_node.node_id, target_node.node_id)

            self.drag_start = None
            self.drag_from_node = None

        def _create_dependency(self, from_node_id: str, to_node_id: str):
            """Create a dependency between two nodes."""
            to_node_box = self.nodes[to_node_id]

            # Add input to target node
            if "input" in to_node_box.node_data:
                # Convert single input to inputs list
                current_input = to_node_box.node_data["input"]
                if current_input != from_node_id:
                    to_node_box.node_data["inputs"] = [current_input, from_node_id]
                    del to_node_box.node_data["input"]
            elif "inputs" in to_node_box.node_data:
                # Add to existing inputs list
                if from_node_id not in to_node_box.node_data["inputs"]:
                    to_node_box.node_data["inputs"].append(from_node_id)
            else:
                # Create new input
                to_node_box.node_data["input"] = from_node_id

            # Recreate arrows
            for arrow in self.arrows:
                arrow.delete()
            self.arrows.clear()
            self._create_dependency_arrows()

            # Update display
            props_text = to_node_box._format_properties()
            self.canvas.itemconfig(to_node_box.props_id, text=props_text)

            self.status_var.set(f"Created dependency: {from_node_id} -> {to_node_id}")

        def run(self):
            """Start the GUI editor."""
            self.root.mainloop()