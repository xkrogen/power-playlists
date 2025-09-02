import inspect
import re
import sys
from pathlib import Path

# Add the src directory to the Python path to allow importing powerplaylists
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from powerplaylists.nodes import Node, TimeBasedFilterNode


def get_all_subclasses(cls):
    """Recursively get all subclasses of a class."""
    all_subclasses = set()
    for subclass in cls.__subclasses__():
        all_subclasses.add(subclass)
        all_subclasses.update(get_all_subclasses(subclass))
    return all_subclasses


def parse_docstring(docstring):
    """Parses the docstring of a node class."""
    if not docstring:
        return None

    # Extract the main description, which is everything before "Type:" or "Properties:"
    # or the end of the string.
    description_end = re.search(r"\n\s*(Type:|Properties:|Required properties:)", docstring)
    description = docstring[:description_end.start()] if description_end else docstring
    description = description.strip()


    type_match = re.search(r"Type: ``(.+?)``", docstring, re.DOTALL)
    node_type = type_match.group(1) if type_match else None

    properties = []
    props_section_match = re.search(r"(?:Properties|Required properties):\s*\n\n(.+)", docstring, re.DOTALL)
    if not props_section_match:
        props_section_match = re.search(r"(?:Properties|Required properties):\s*(.+)", docstring, re.DOTALL)

    if props_section_match:
        props_text = props_section_match.group(1).strip()
        # Split properties based on the ``prop_name`` format
        prop_blocks = re.split(r'\n\s*\n', props_text)
        for block in prop_blocks:
            if not block.strip():
                continue

            # Regex to capture property name, type, requirement, and description
            match = re.match(r"``(.+?)``\s+\[(.+?)\]\s+\[(.+?)\]\n(.+)", block.strip(), re.DOTALL)
            if match:
                name, prop_type, required, prop_desc = match.groups()
                # Clean up the description
                prop_desc = ' '.join(line.strip() for line in prop_desc.strip().split('\n'))
                properties.append({
                    "name": name,
                    "type": prop_type,
                    "required": required,
                    "description": prop_desc,
                })

    return {
        "description": description,
        "type": node_type,
        "properties": properties,
    }

def get_docs_for_class(cls):
    """
    Gets all documentation for a class, including from its parents.
    """
    if not inspect.isclass(cls):
        return {}

    # Get the docstring for the current class
    docstring = inspect.getdoc(cls)
    parsed_docs = parse_docstring(docstring) or {"properties": [], "description": "", "type": None}

    # For TimeBasedFilterNode children, we need to manually inherit the parent's properties
    if issubclass(cls, TimeBasedFilterNode) and cls is not TimeBasedFilterNode:
        parent_docstring = inspect.getdoc(TimeBasedFilterNode)
        parent_docs = parse_docstring(parent_docstring)
        if parent_docs and parent_docs["properties"]:
            # Prepend parent properties to child properties
            parsed_docs["properties"] = parent_docs["properties"] + parsed_docs["properties"]

    return parsed_docs


def main():
    """
    Generates a Markdown file with a table of all supported node types
    and their properties.
    """
    output_dir = Path(__file__).parent.parent / "docs"
    output_file = output_dir / "NODE_REFERENCE.md"

    # Ensure the output directory exists
    output_dir.mkdir(exist_ok=True)

    node_classes = [
        cls
        for cls in get_all_subclasses(Node)
        if (
            not inspect.isabstract(cls)
            and hasattr(cls, "ntype")
            and cls.ntype() is not None
        )
    ]

    # Exclude template nodes that are not meant to be used directly
    # and the base private node
    excluded_nodes = ["template", None]
    node_classes = [n for n in node_classes if n.ntype() not in excluded_nodes]


    node_docs = []
    for node_class in node_classes:
        docs = get_docs_for_class(node_class)
        if docs and docs["type"]:
            node_docs.append(docs)

    # Sort nodes by type
    node_docs.sort(key=lambda x: x["type"])

    with open(output_file, "w") as f:
        f.write("# Node Reference\n\n")
        f.write("This page provides a reference for all supported node types in `power-playlists`.\n\n")

        for doc in node_docs:
            f.write(f"## `{doc['type']}`\n\n")
            f.write(f"{doc['description']}\n\n")

            if doc["properties"]:
                f.write("| Property | Type | Required | Description |\n")
                f.write("|----------|------|----------|-------------|\n")
                for prop in doc["properties"]:
                    # Escape pipe characters in the description
                    description = prop['description'].replace('|', '\|')
                    f.write(f"| `{prop['name']}` | {prop['type']} | {prop['required']} | {description} |\n")
                f.write("\n")

    print(f"Successfully generated node reference at {output_file}")


if __name__ == "__main__":
    main()
