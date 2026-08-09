"""Tests for the Configuration module."""

from src.config import Config, get_config


class TestGetConfig:
    """Tests for configuration retrieval."""

    def test_get_config_returns_config_object(self) -> None:
        """Test that get_config returns a Config object."""
        config = get_config()
        assert isinstance(config, Config)

    def test_config_max_document_size(self) -> None:
        """Test that config includes correct MAX_DOCUMENT_SIZE."""
        config = get_config()
        assert hasattr(config, "MAX_DOCUMENT_SIZE")
        assert config.MAX_DOCUMENT_SIZE == 50 * 1024 * 1024

    def test_config_supported_formats(self) -> None:
        """Test that config includes correct SUPPORTED_FORMATS."""
        config = get_config()
        assert hasattr(config, "SUPPORTED_FORMATS")
        assert ".txt" in config.SUPPORTED_FORMATS
        assert ".md" in config.SUPPORTED_FORMATS
        assert len(config.SUPPORTED_FORMATS) == 2
