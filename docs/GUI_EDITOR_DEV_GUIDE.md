# GUI Editor Developer Guide

This guide explains how the new Cytoscape.js-based GUI editor works and how to extend it.

## Architecture

The GUI editor is now built on three separate files:

- **index.html** (120 lines): Page structure and layout
- **styles.css** (305 lines): Visual styling
- **app.js** (838 lines): Application logic using Cytoscape.js

## Key Components

### ConfigurationEditor Class

The main class in `app.js` that manages the entire editor:

```javascript
class ConfigurationEditor {
    constructor() {
        this.cy = null;              // Main Cytoscape instance
        this.nodeSchemas = null;     // Node type schemas
        this.templateCy = null;      // Template view Cytoscape instance
        // ... more properties
    }
}
```

### Cytoscape.js Instance

The `cy` object is the Cytoscape.js graph instance that handles:
- Node rendering and positioning
- Edge (connection) drawing
- User interactions (drag, zoom, pan)
- Graph layout

## How to Add a New Node Type

1. **Update the backend schema** in `gui_editor.py`:
   ```python
   "my_new_type": {
       "name": "My Node Type",
       "description": "What this node does",
       "icon": "🎨",
       "color": "#FF5733",
       "properties": {
           "input": {"type": "node_reference", "required": True},
           "my_param": {"type": "text", "required": False}
       }
   }
   ```

2. **Add color mapping** in `app.js` (optional):
   ```javascript
   getNodeColor(nodeType) {
       const colors = {
           // ... existing types
           'my_new_type': '#FF5733'
       };
       return colors[nodeType] || '#7f8c8d';
   }
   ```

That's it! The framework handles the rest automatically.

## How to Customize Node Appearance

Modify the Cytoscape style in `getCytoscapeStyle()`:

```javascript
getCytoscapeStyle() {
    return [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'background-color': 'data(color)',
                'width': 'data(width)',
                'height': 'data(height)',
                // Add your custom styles here
            }
        }
    ];
}
```

## How to Add New Layouts

Cytoscape.js supports many layout algorithms. To use a different layout:

```javascript
this.cy.layout({
    name: 'circle',  // or 'grid', 'breadthfirst', 'cose', etc.
    // layout-specific options
}).run();
```

See [Cytoscape.js layouts](https://js.cytoscape.org/#layouts) for all options.

## How to Add Custom Interactions

Add event listeners to the Cytoscape instance:

```javascript
// Right-click on node
this.cy.on('cxttap', 'node', (evt) => {
    const node = evt.target;
    // Your custom logic
});

// Hover over node
this.cy.on('mouseover', 'node', (evt) => {
    const node = evt.target;
    // Your custom logic
});
```

## How to Access Node Data

```javascript
// Get all nodes
const nodes = this.cy.nodes();

// Get a specific node
const node = this.cy.getElementById('node_id');

// Get node data
const nodeData = node.data('nodeData');

// Update node data
node.data('nodeData', updatedData);
```

## How to Add Custom Validation

Update the form validation in `saveNodeChanges()`:

```javascript
saveNodeChanges() {
    // ... existing code
    
    // Add custom validation
    if (nodeData.my_param && nodeData.my_param.length < 3) {
        this.showError('my_param must be at least 3 characters');
        return;
    }
    
    // ... rest of the code
}
```

## Debugging Tips

1. **Access the editor object in browser console:**
   ```javascript
   editor.cy.nodes()  // See all nodes
   editor.cy.edges()  // See all edges
   editor.currentConfig  // See current configuration
   ```

2. **Enable Cytoscape.js debugging:**
   Add this to see what Cytoscape is doing:
   ```javascript
   this.cy.on('*', (evt) => {
       console.log('Cytoscape event:', evt.type);
   });
   ```

3. **Check node data:**
   ```javascript
   this.cy.nodes().forEach(node => {
       console.log(node.id(), node.data('nodeData'));
   });
   ```

## Performance Considerations

- Cytoscape.js is optimized for graphs with thousands of nodes
- For very large graphs, consider using the `cose-bilkent` layout extension
- Batch updates for better performance:
  ```javascript
  this.cy.batch(() => {
      // Multiple operations here
  });
  ```

## Further Resources

- [Cytoscape.js Documentation](https://js.cytoscape.org/)
- [Cytoscape.js Examples](https://js.cytoscape.org/#demos)
- [Cytoscape.js Extensions](https://js.cytoscape.org/#extensions)

## Migration Notes

If you need to reference the old implementation, it's available in git history:
```bash
git show HEAD~2:src/power_playlists/web_ui/index.html
```

The old implementation had all code in a single file, making it harder to maintain but possibly useful for understanding the original logic.
