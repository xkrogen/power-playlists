// Power Playlists Configuration Editor
// Using Cytoscape.js for graph visualization

class ConfigurationEditor {
    constructor() {
        this.cy = null;
        this.currentConfig = null;
        this.nodeSchemas = null;
        this.selectedNode = null;
        
        // Template view state
        this.isInTemplateView = false;
        this.currentTemplateNodeId = null;
        this.templateCy = null;
        
        this.initializeElements();
        this.initializeCytoscape();
        this.setupEventListeners();
        this.loadNodeSchemas().then(() => {
            this.loadInitialConfiguration();
        });
    }

    initializeElements() {
        this.statusText = document.getElementById('statusText');
        this.editModal = document.getElementById('editModal');
        this.modalTitle = document.getElementById('modalTitle');
        this.modalForm = document.getElementById('modalForm');
        this.errorModal = document.getElementById('errorModal');
        this.errorMessage = document.getElementById('errorMessage');
        this.addNodeModal = document.getElementById('addNodeModal');
        
        // Template view elements
        this.templateView = document.getElementById('templateView');
        this.templateBreadcrumb = document.getElementById('templateBreadcrumb');
        this.templateCanvas = document.getElementById('templateCanvas');
        this.templateVariables = document.getElementById('templateVariables');
        this.templateInstances = document.getElementById('templateInstances');
    }

    initializeCytoscape() {
        // Initialize main canvas with Cytoscape.js
        this.cy = cytoscape({
            container: document.getElementById('canvas'),
            style: this.getCytoscapeStyle(),
            layout: {
                name: 'preset'
            },
            wheelSensitivity: 0.2,
            minZoom: 0.5,
            maxZoom: 2
        });

        // Set up event handlers
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            this.selectedNode = node.id();
        });

        this.cy.on('dbltap', 'node', (evt) => {
            const node = evt.target;
            const nodeData = node.data();
            
            if (nodeData.nodeType === 'dynamic_template') {
                this.enterTemplateView(node.id());
            } else {
                this.editNode(node.id());
            }
        });

        // Add context menu on right-click
        this.cy.on('cxttap', 'node', (evt) => {
            const node = evt.target;
            this.showNodeContextMenu(node, evt);
        });
    }

    getCytoscapeStyle() {
        return [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'background-color': 'data(color)',
                    'border-width': 2,
                    'border-color': '#d1d5db',
                    'width': 'data(width)',
                    'height': 'data(height)',
                    'shape': 'roundrectangle',
                    'font-size': '12px',
                    'text-wrap': 'wrap',
                    'text-max-width': '140px',
                    'color': '#333'
                }
            },
            {
                selector: 'node:selected',
                style: {
                    'border-color': '#007acc',
                    'border-width': 3
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#9ca3af',
                    'target-arrow-color': '#9ca3af',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.5
                }
            },
            {
                selector: 'edge:selected',
                style: {
                    'line-color': '#007acc',
                    'target-arrow-color': '#007acc'
                }
            }
        ];
    }

    getNodeColor(nodeType) {
        const colors = {
            'playlist': '#8E44AD',
            'liked_tracks': '#E74C3C',
            'all_tracks': '#9B59B6',
            'output': '#2ECC71',
            'combiner': '#F39C12',
            'limit': '#34495E',
            'sort': '#3498DB',
            'filter_eval': '#E67E22',
            'filter_time_added': '#16A085',
            'filter_release_date': '#8E44AD',
            'dedup': '#95A5A6',
            'is_liked': '#E91E63',
            'dynamic_template': '#17A2B8',
            'combine_sort_dedup_output': '#9B59B6'
        };
        return colors[nodeType] || '#7f8c8d';
    }

    getNodeIcon(nodeType) {
        if (this.nodeSchemas && this.nodeSchemas[nodeType]) {
            return this.nodeSchemas[nodeType].icon;
        }
        const icons = {
            'playlist': '♫',
            'output': '📤',
            'liked_tracks': '❤️',
            'combiner': '➕',
            'limit': '🔢',
            'sort': '🔀',
            'filter_eval': '🔍',
            'filter_time_added': '⏰',
            'filter_release_date': '📅',
            'dedup': '🎯',
            'is_liked': '💖',
            'dynamic_template': '🔄'
        };
        return icons[nodeType] || '📦';
    }

    setupEventListeners() {
        // Toolbar buttons
        document.getElementById('loadBtn').addEventListener('click', () => this.loadConfiguration());
        document.getElementById('saveBtn').addEventListener('click', () => this.saveConfiguration());
        document.getElementById('saveAsBtn').addEventListener('click', () => this.saveAsConfiguration());
        document.getElementById('addNodeBtn').addEventListener('click', () => this.showAddNodeModal());

        // Modal buttons
        document.getElementById('cancelBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('saveNodeBtn').addEventListener('click', () => this.saveNodeChanges());
        document.getElementById('deleteNodeBtn').addEventListener('click', () => this.deleteNode());
        document.getElementById('errorOkBtn').addEventListener('click', () => this.closeErrorModal());
        document.getElementById('addNodeCancelBtn').addEventListener('click', () => this.closeAddNodeModal());
        document.getElementById('addNodeConfirmBtn').addEventListener('click', () => this.confirmAddNode());

        // Node type selection
        document.getElementById('newNodeType').addEventListener('change', (e) => {
            this.updateNodeTypeDescription(e.target.value);
        });

        // Template view buttons
        document.getElementById('exitTemplateBtn').addEventListener('click', () => this.exitTemplateView());
        document.getElementById('saveTemplateBtn').addEventListener('click', () => this.saveTemplate());
        document.getElementById('addTemplateNodeBtn').addEventListener('click', () => this.showAddTemplateNodeModal());
        document.getElementById('addInstanceBtn').addEventListener('click', () => this.addTemplateInstance());
    }

    async loadNodeSchemas() {
        try {
            const response = await fetch('/api/node-schema');
            if (response.ok) {
                const data = await response.json();
                this.nodeSchemas = data.schemas;
                this.populateNodeTypeSelector();
            } else {
                console.error('Failed to load node schemas');
            }
        } catch (error) {
            console.error('Error loading node schemas:', error);
        }
    }

    populateNodeTypeSelector() {
        const selector = document.getElementById('newNodeType');
        selector.innerHTML = '<option value="">Select node type...</option>';
        
        if (this.nodeSchemas) {
            Object.entries(this.nodeSchemas).forEach(([type, schema]) => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = `${schema.icon} ${schema.name}`;
                selector.appendChild(option);
            });
        }
    }

    updateNodeTypeDescription(nodeType) {
        const descElement = document.getElementById('nodeTypeDescription');
        if (nodeType && this.nodeSchemas && this.nodeSchemas[nodeType]) {
            descElement.textContent = this.nodeSchemas[nodeType].description;
        } else {
            descElement.textContent = '';
        }
    }

    async loadInitialConfiguration() {
        try {
            const response = await fetch('/api/load');
            if (response.ok) {
                const config = await response.json();
                this.displayConfiguration(config);
                this.statusText.textContent = `Loaded: ${config.filename || 'configuration'}`;
            } else {
                this.statusText.textContent = 'No configuration loaded - use Load button';
            }
        } catch (error) {
            console.error('Failed to load initial configuration:', error);
            this.statusText.textContent = 'Failed to load initial configuration';
        }
    }

    async loadConfiguration() {
        try {
            const response = await fetch('/api/load');
            if (response.ok) {
                const config = await response.json();
                this.displayConfiguration(config);
                this.statusText.textContent = `Loaded: ${config.filename || 'configuration'}`;
            } else {
                this.statusText.textContent = 'Failed to load configuration';
            }
        } catch (error) {
            console.error('Failed to load configuration:', error);
            this.statusText.textContent = 'Error loading configuration';
        }
    }

    displayConfiguration(config) {
        this.currentConfig = config;
        this.cy.elements().remove();

        const nodeEntries = Object.entries(config.data || {});
        const nodesPerRow = 4;
        const nodeSpacing = { x: 220, y: 180 };
        const startPos = { x: 100, y: 100 };

        // Add all nodes first
        nodeEntries.forEach(([nodeId, nodeData], index) => {
            const row = Math.floor(index / nodesPerRow);
            const col = index % nodesPerRow;
            const x = startPos.x + col * nodeSpacing.x;
            const y = startPos.y + row * nodeSpacing.y;

            const icon = this.getNodeIcon(nodeData.type);
            const color = this.getNodeColor(nodeData.type);
            const label = `${icon} ${nodeId}`;

            this.cy.add({
                group: 'nodes',
                data: {
                    id: nodeId,
                    label: label,
                    nodeType: nodeData.type,
                    nodeData: nodeData,
                    color: color,
                    width: 180,
                    height: 80
                },
                position: { x, y }
            });
        });

        // Add edges based on connections
        nodeEntries.forEach(([nodeId, nodeData]) => {
            this.addEdgesForNode(nodeId, nodeData);
        });
    }

    addEdgesForNode(nodeId, nodeData) {
        const connections = this.extractConnections(nodeData);
        connections.forEach(targetId => {
            if (this.cy.getElementById(targetId).length > 0) {
                this.cy.add({
                    group: 'edges',
                    data: {
                        id: `${nodeId}-${targetId}`,
                        source: nodeId,
                        target: targetId
                    }
                });
            }
        });
    }

    extractConnections(nodeData) {
        const connections = [];
        
        if (nodeData.input) {
            connections.push(nodeData.input);
        }
        if (nodeData.inputs && Array.isArray(nodeData.inputs)) {
            connections.push(...nodeData.inputs);
        }
        if (nodeData.input_nodes && Array.isArray(nodeData.input_nodes)) {
            connections.push(...nodeData.input_nodes);
        }
        
        return connections;
    }

    showAddNodeModal() {
        document.getElementById('newNodeId').value = '';
        document.getElementById('newNodeType').value = '';
        this.updateNodeTypeDescription('');
        this.addNodeModal.classList.remove('hidden');
    }

    closeAddNodeModal() {
        this.addNodeModal.classList.add('hidden');
    }

    confirmAddNode() {
        const nodeId = document.getElementById('newNodeId').value.trim();
        const nodeType = document.getElementById('newNodeType').value;
        
        if (!nodeId) {
            this.showError('Please enter a node ID');
            return;
        }
        
        if (!nodeType) {
            this.showError('Please select a node type');
            return;
        }
        
        if (this.cy.getElementById(nodeId).length > 0) {
            this.showError('Node ID already exists!');
            return;
        }

        this.createNewNode(nodeId, nodeType);
        this.closeAddNodeModal();
    }

    createNewNode(nodeId, nodeType) {
        if (!this.nodeSchemas || !this.nodeSchemas[nodeType]) {
            this.showError('Invalid node type');
            return;
        }

        const schema = this.nodeSchemas[nodeType];
        const nodeData = { type: nodeType };

        // Set default values for properties
        Object.entries(schema.properties).forEach(([prop, config]) => {
            if (config.default !== undefined) {
                nodeData[prop] = config.default;
            }
        });

        // Find position for new node
        const existingNodes = this.cy.nodes();
        const col = existingNodes.length % 4;
        const row = Math.floor(existingNodes.length / 4);
        const x = 100 + col * 220;
        const y = 100 + row * 180;

        const icon = this.getNodeIcon(nodeType);
        const color = this.getNodeColor(nodeType);
        const label = `${icon} ${nodeId}`;

        this.cy.add({
            group: 'nodes',
            data: {
                id: nodeId,
                label: label,
                nodeType: nodeType,
                nodeData: nodeData,
                color: color,
                width: 180,
                height: 80
            },
            position: { x, y }
        });

        this.statusText.textContent = `Added new ${schema.name} node: ${nodeId}`;
    }

    editNode(nodeId) {
        const node = this.cy.getElementById(nodeId);
        if (node.length === 0) return;

        const nodeData = node.data('nodeData');
        const nodeType = node.data('nodeType');
        const schema = this.nodeSchemas[nodeType];

        this.selectedNode = nodeId;
        this.modalTitle.textContent = `Edit Node: ${nodeId}`;
        this.modalForm.innerHTML = '';

        // Create form fields based on schema
        if (schema && schema.properties) {
            Object.entries(schema.properties).forEach(([prop, config]) => {
                const value = nodeData[prop] || config.default || '';
                this.addFormField(prop, value, config);
            });
        }

        this.editModal.classList.remove('hidden');
    }

    addFormField(name, value, config) {
        const formGroup = document.createElement('div');
        formGroup.className = 'form-group';

        const label = document.createElement('label');
        label.textContent = name;
        formGroup.appendChild(label);

        let input;
        if (config.type === 'boolean') {
            input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = value === true || value === 'true';
        } else if (config.type === 'select') {
            input = document.createElement('select');
            config.options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt;
                option.selected = value === opt;
                input.appendChild(option);
            });
        } else if (config.type === 'node_list' || config.type === 'text_list') {
            input = document.createElement('textarea');
            input.value = Array.isArray(value) ? value.join(', ') : value;
        } else {
            input = document.createElement('input');
            input.type = config.type === 'integer' ? 'number' : 'text';
            input.value = value;
        }

        input.name = name;
        formGroup.appendChild(input);

        if (config.description) {
            const desc = document.createElement('div');
            desc.className = 'form-description';
            desc.textContent = config.description;
            formGroup.appendChild(desc);
        }

        this.modalForm.appendChild(formGroup);
    }

    closeModal() {
        this.editModal.classList.add('hidden');
    }

    saveNodeChanges() {
        if (!this.selectedNode) return;

        const node = this.cy.getElementById(this.selectedNode);
        const nodeData = { ...node.data('nodeData') };
        const formData = new FormData(this.modalForm);

        // Update node data from form
        for (const [key, value] of formData.entries()) {
            const input = this.modalForm.querySelector(`[name="${key}"]`);
            if (input.type === 'checkbox') {
                nodeData[key] = input.checked;
            } else if (input.tagName === 'TEXTAREA' && (key === 'inputs' || key === 'input_nodes' || key === 'input_uris')) {
                // Parse comma-separated lists
                nodeData[key] = value.split(',').map(v => v.trim()).filter(v => v);
            } else if (input.type === 'number') {
                nodeData[key] = parseInt(value);
            } else {
                nodeData[key] = value;
            }
        }

        // Update node
        node.data('nodeData', nodeData);

        // Update edges if input connections changed
        this.cy.edges(`[source="${this.selectedNode}"]`).remove();
        this.addEdgesForNode(this.selectedNode, nodeData);

        this.closeModal();
        this.statusText.textContent = `Updated node: ${this.selectedNode}`;
    }

    deleteNode() {
        if (!this.selectedNode) return;

        if (confirm(`Delete node "${this.selectedNode}"?`)) {
            this.cy.getElementById(this.selectedNode).remove();
            this.closeModal();
            this.statusText.textContent = `Deleted node: ${this.selectedNode}`;
            this.selectedNode = null;
        }
    }

    async saveConfiguration() {
        try {
            const config = this.serializeConfiguration();
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            if (response.ok) {
                this.statusText.textContent = 'Configuration saved successfully';
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Failed to save configuration');
                this.statusText.textContent = 'Failed to save configuration';
            }
        } catch (error) {
            console.error('Failed to save configuration:', error);
            this.showError('Error saving configuration');
        }
    }

    async saveAsConfiguration() {
        const filename = prompt('Enter filename (without .yaml extension):');
        if (!filename) return;

        try {
            const config = this.serializeConfiguration();
            config.filename = filename;
            
            const response = await fetch('/api/save-as', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            if (response.ok) {
                this.statusText.textContent = `Configuration saved as ${filename}.yaml`;
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Failed to save configuration');
            }
        } catch (error) {
            console.error('Failed to save configuration:', error);
            this.showError('Error saving configuration');
        }
    }

    serializeConfiguration() {
        const data = {};
        
        this.cy.nodes().forEach(node => {
            const nodeId = node.id();
            const nodeData = node.data('nodeData');
            data[nodeId] = { ...nodeData };
        });

        return {
            filename: this.currentConfig?.filename || 'config.yaml',
            data: data
        };
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorModal.classList.remove('hidden');
    }

    closeErrorModal() {
        this.errorModal.classList.add('hidden');
    }

    // Template view methods
    enterTemplateView(nodeId) {
        const node = this.cy.getElementById(nodeId);
        if (node.length === 0) return;

        const nodeData = node.data('nodeData');
        if (nodeData.type !== 'dynamic_template') return;

        this.currentTemplateNodeId = nodeId;
        this.isInTemplateView = true;
        this.templateView.classList.remove('hidden');
        this.templateBreadcrumb.textContent = `Editing Template: ${nodeId}`;

        // Load template nodes
        const templateNodes = nodeData.template || {};
        const instances = nodeData.instances || [];

        this.displayTemplateVariables(templateNodes);
        this.displayTemplateInstances(instances);
        this.displayTemplateCanvas(templateNodes);
    }

    displayTemplateVariables(templateNodes) {
        const variables = this.extractTemplateVariables(templateNodes);
        this.templateVariables.innerHTML = '';
        
        if (variables.length === 0) {
            this.templateVariables.innerHTML = '<div class="template-variable">No variables defined</div>';
        } else {
            variables.forEach(varName => {
                const div = document.createElement('div');
                div.className = 'template-variable';
                div.textContent = `{${varName}}`;
                this.templateVariables.appendChild(div);
            });
        }
    }

    extractTemplateVariables(obj) {
        const variables = new Set();
        const extract = (value) => {
            if (typeof value === 'string') {
                const matches = value.match(/\{([^{}]+)\}/g);
                if (matches) {
                    matches.forEach(match => {
                        variables.add(match.slice(1, -1));
                    });
                }
            } else if (Array.isArray(value)) {
                value.forEach(extract);
            } else if (typeof value === 'object' && value !== null) {
                Object.values(value).forEach(extract);
            }
        };
        extract(obj);
        return Array.from(variables).sort();
    }

    displayTemplateInstances(instances) {
        this.templateInstances.innerHTML = '';
        
        instances.forEach((instance, index) => {
            const div = document.createElement('div');
            div.className = 'template-instance';
            
            const header = document.createElement('div');
            header.className = 'template-instance-header';
            
            const title = document.createElement('div');
            title.className = 'template-instance-title';
            title.textContent = `Instance ${index + 1}`;
            header.appendChild(title);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-danger btn-sm';
            deleteBtn.textContent = 'Delete';
            deleteBtn.onclick = () => this.deleteTemplateInstance(index);
            header.appendChild(deleteBtn);
            
            div.appendChild(header);
            
            Object.entries(instance).forEach(([key, value]) => {
                const varDiv = document.createElement('div');
                varDiv.className = 'instance-variable';
                
                const label = document.createElement('label');
                label.textContent = key;
                varDiv.appendChild(label);
                
                const input = document.createElement('input');
                input.type = 'text';
                input.value = value;
                input.onchange = () => this.updateTemplateInstance(index, key, input.value);
                varDiv.appendChild(input);
                
                div.appendChild(varDiv);
            });
            
            this.templateInstances.appendChild(div);
        });
    }

    displayTemplateCanvas(templateNodes) {
        // Initialize template canvas with Cytoscape
        this.templateCanvas.innerHTML = '<div id="templateCy" style="width: 100%; height: 100%;"></div>';
        
        this.templateCy = cytoscape({
            container: document.getElementById('templateCy'),
            style: this.getCytoscapeStyle(),
            layout: {
                name: 'preset'
            }
        });

        const nodeEntries = Object.entries(templateNodes);
        const nodeSpacing = { x: 220, y: 180 };
        const startPos = { x: 100, y: 100 };

        nodeEntries.forEach(([nodeId, nodeData], index) => {
            const x = startPos.x + (index % 3) * nodeSpacing.x;
            const y = startPos.y + Math.floor(index / 3) * nodeSpacing.y;

            const icon = this.getNodeIcon(nodeData.type);
            const color = this.getNodeColor(nodeData.type);
            const label = `${icon} ${nodeId}`;

            this.templateCy.add({
                group: 'nodes',
                data: {
                    id: nodeId,
                    label: label,
                    nodeType: nodeData.type,
                    nodeData: nodeData,
                    color: color,
                    width: 180,
                    height: 80
                },
                position: { x, y }
            });
        });

        // Add edges
        nodeEntries.forEach(([nodeId, nodeData]) => {
            const connections = this.extractConnections(nodeData);
            connections.forEach(targetId => {
                if (this.templateCy.getElementById(targetId).length > 0) {
                    this.templateCy.add({
                        group: 'edges',
                        data: {
                            id: `${nodeId}-${targetId}`,
                            source: nodeId,
                            target: targetId
                        }
                    });
                }
            });
        });

        // Allow editing template nodes
        this.templateCy.on('dbltap', 'node', (evt) => {
            // Template node editing would go here
        });
    }

    updateTemplateInstance(index, key, value) {
        const node = this.cy.getElementById(this.currentTemplateNodeId);
        const nodeData = node.data('nodeData');
        
        if (nodeData.instances && nodeData.instances[index]) {
            nodeData.instances[index][key] = value;
            node.data('nodeData', nodeData);
        }
    }

    deleteTemplateInstance(index) {
        if (!confirm('Delete this instance?')) return;

        const node = this.cy.getElementById(this.currentTemplateNodeId);
        const nodeData = node.data('nodeData');
        
        if (nodeData.instances) {
            nodeData.instances.splice(index, 1);
            node.data('nodeData', nodeData);
            this.displayTemplateInstances(nodeData.instances);
        }
    }

    addTemplateInstance() {
        const node = this.cy.getElementById(this.currentTemplateNodeId);
        const nodeData = node.data('nodeData');
        
        const variables = this.extractTemplateVariables(nodeData.template || {});
        const newInstance = {};
        variables.forEach(varName => {
            newInstance[varName] = '';
        });
        
        if (!nodeData.instances) {
            nodeData.instances = [];
        }
        nodeData.instances.push(newInstance);
        node.data('nodeData', nodeData);
        
        this.displayTemplateInstances(nodeData.instances);
    }

    showAddTemplateNodeModal() {
        this.showAddNodeModal();
    }

    saveTemplate() {
        // Save template changes back to main configuration
        this.exitTemplateView();
        this.statusText.textContent = 'Template saved';
    }

    exitTemplateView() {
        this.isInTemplateView = false;
        this.templateView.classList.add('hidden');
        this.currentTemplateNodeId = null;
        
        if (this.templateCy) {
            this.templateCy.destroy();
            this.templateCy = null;
        }
    }

    showNodeContextMenu(node, evt) {
        // Context menu functionality would go here
    }
}

// Initialize the editor when the page loads
let editor;
document.addEventListener('DOMContentLoaded', () => {
    editor = new ConfigurationEditor();
});
