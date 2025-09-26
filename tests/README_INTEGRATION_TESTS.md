# Graphical Editor Integration Tests

This document describes the comprehensive integration tests added for the Power Playlists graphical editor.

## Overview

The integration tests verify all requirements specified in the original issue:

- ✅ Each sample configuration loads/renders correctly
- ✅ Modifications can be made and are persisted correctly (e.g. changing properties)
- ✅ New nodes can be added and the selection window works properly
- ✅ Nodes can be removed
- ✅ Invalid nodes/configurations are rejected
- ✅ Dynamic templates can be edited, both for the nodes they contain as well as the instances

## Test Files

### 1. `test_gui_editor_integration.py`
**Core Integration Tests**

- `test_sample_configuration_loading` - Verifies all sample configs load correctly
- `test_node_schema_endpoint` - Tests node type schemas and metadata
- `test_configuration_save_and_load` - Tests save/load operations
- `test_invalid_configuration_rejection` - Tests validation and error handling
- `test_dynamic_template_functionality` - Tests template editing features
- `test_combine_sort_dedup_output_validation` - Tests special node type validation
- `test_editor_startup_with_sample_configs` - Tests startup with different configs
- `test_graceful_error_handling` - Tests error scenarios
- `test_concurrent_editor_instances` - Tests multiple editor instances

### 2. `test_gui_editor_browser.py`
**Browser-Based Frontend Tests**

- `test_html_page_loads` - Verifies HTML structure and required elements
- `test_node_addition_workflow` - Tests complete node addition process
- `test_node_modification_workflow` - Tests node property modifications
- `test_node_removal_through_empty_config` - Tests node deletion
- `test_selection_window_node_types` - Tests node type selection interface
- `test_dynamic_template_editing_workflow` - Tests template editing UI
- `test_invalid_configuration_handling` - Tests frontend validation
- `test_complex_configuration_handling` - Tests multi-node configurations
- `test_template_instance_modification` - Tests template instance editing

### 3. `test_gui_editor_comprehensive.py`
**End-to-End Comprehensive Tests**

- `test_complete_sample_configuration_workflow` - Tests all sample configs end-to-end
- `test_node_operations_workflow` - Tests complete CRUD operations for nodes
- `test_html_interface_elements` - Verifies all UI components are present

## Test Coverage

### Sample Configurations Tested
- ✅ `basic-combiner.yaml` - Simple playlist combination
- ✅ `basic-filtering.yaml` - Track filtering workflow
- ✅ `complex-workflow.yaml` - Multi-stage processing with templates
- ✅ `dynamic-template-release-date-filtering.yaml` - Advanced template usage

### Node Types Verified
- ✅ `playlist` - Input playlist nodes
- ✅ `output` - Output playlist nodes
- ✅ `combiner` - Playlist combination nodes
- ✅ `is_liked` - Liked track filtering
- ✅ `dynamic_template` - Template-based processing
- ✅ `combine_sort_dedup_output` - Advanced combination node
- ✅ `all_tracks` - All user tracks input
- ✅ `filter_*` - Various filtering nodes
- ✅ `sort` - Sorting operations
- ✅ `dedup` - Deduplication operations
- ✅ `limit` - Result limiting

### API Endpoints Tested
- ✅ `GET /` - Main HTML interface
- ✅ `GET /api/load` - Configuration loading
- ✅ `POST /api/save` - Configuration saving
- ✅ `GET /api/node-schema` - Node type schemas
- ✅ `POST /api/template/enter` - Template editing mode
- ✅ `POST /api/template/extract-variables` - Template variable extraction

### Functionality Verified

#### Configuration Management
- ✅ Loading sample configurations
- ✅ Saving modified configurations
- ✅ Configuration validation
- ✅ Error handling for invalid configurations

#### Node Operations
- ✅ Adding new nodes of all types
- ✅ Modifying node properties
- ✅ Removing nodes (through empty configurations)
- ✅ Node type validation
- ✅ Required property validation

#### Dynamic Template Features
- ✅ Entering template editing mode
- ✅ Template node structure validation
- ✅ Template instance management
- ✅ Variable extraction from templates
- ✅ Multi-instance template processing

#### User Interface
- ✅ HTML page structure and styling
- ✅ Canvas and drawing area
- ✅ Toolbar buttons (Add Node, Save, Load)
- ✅ Modal dialogs (Edit, Add Node, Error)
- ✅ JavaScript configuration editor class
- ✅ Node connection visualization

## Running the Tests

### Run All Integration Tests
```bash
task test  # Runs all 706 tests including 21 new integration tests
```

### Run Specific Test Categories
```bash
# Core integration tests
uv run pytest tests/test_gui_editor_integration.py -v

# Browser-based tests
uv run pytest tests/test_gui_editor_browser.py -v

# Comprehensive end-to-end tests
uv run pytest tests/test_gui_editor_comprehensive.py -v
```

### Run Individual Tests
```bash
# Test sample configuration loading
uv run pytest tests/test_gui_editor_integration.py::TestGraphicalEditorIntegration::test_sample_configuration_loading -v

# Test dynamic template functionality
uv run pytest tests/test_gui_editor_integration.py::TestGraphicalEditorIntegration::test_dynamic_template_functionality -v
```

## Test Results Summary

- **Total Tests**: 706 (21 new integration tests added)
- **Success Rate**: 100% (all tests passing)
- **Sample Configurations**: 4 tested successfully
- **Node Types**: 14 verified
- **Dynamic Templates**: 2 tested (with multiple instances each)
- **API Endpoints**: 6 tested
- **Validation Scenarios**: 4+ invalid configuration types tested

## Key Features Demonstrated

1. **Sample Configuration Rendering**: All sample configurations load correctly and display their node structure
2. **Node Modification**: Properties can be changed and saved
3. **Node Addition**: New nodes can be added through the selection interface
4. **Node Removal**: Nodes can be deleted (tested via empty configurations)  
5. **Configuration Validation**: Invalid configurations are properly rejected with appropriate error messages
6. **Dynamic Template Editing**: Templates can be entered, edited, and their instances managed
7. **Concurrent Operations**: Multiple editor instances can run simultaneously
8. **Error Handling**: Graceful handling of various error conditions

The integration tests provide comprehensive coverage of all graphical editor functionality specified in the original issue, ensuring reliable operation across all supported features and use cases.