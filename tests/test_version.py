"""Test version functionality."""

import pytest

from power_playlists._version import __version__


def test_version_available():
    """Test that version is available and is a non-empty string."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0
    # Version should follow semantic versioning pattern
    assert "." in __version__


def test_version_import_in_main():
    """Test that version can be imported in main module."""
    from power_playlists.main import __version__ as main_version
    
    assert main_version is not None
    assert isinstance(main_version, str)
    assert main_version == __version__