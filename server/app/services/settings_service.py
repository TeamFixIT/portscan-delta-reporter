"""
Settings Service

Manages application settings with caching for performance.
"""

import os
from functools import lru_cache
from datetime import timedelta
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing application settings"""

    def __init__(self):
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
        self._last_cache_time = None

    def get(self, key: str, default: Any = None, use_env_fallback: bool = True) -> Any:
        """
        Get setting value with fallback to environment variables

        Args:
            key: Setting key
            default: Default value if not found
            use_env_fallback: Whether to check environment variables if not in DB

        Returns:
            Setting value
        """
        try:
            from app.models.setting import Setting

            # Try to get from database
            value = Setting.get_value(key)

            if value is not None:
                return self._convert_value(value)

            # Fallback to environment variable
            if use_env_fallback:
                env_value = os.getenv(key)
                if env_value is not None:
                    return env_value

            return default

        except Exception as e:
            logger.warning(f"Error getting setting {key}: {e}")
            # Fallback to environment variable on error
            if use_env_fallback:
                return os.getenv(key, default)
            return default

    def set(
        self,
        key: str,
        value: Any,
        category: str = "general",
        description: str = None,
        is_sensitive: bool = False,
        user_id: int = None,
    ) -> bool:
        """
        Set setting value

        Args:
            key: Setting key
            value: Setting value
            category: Setting category
            description: Setting description
            is_sensitive: Whether setting contains sensitive data
            user_id: ID of user making the change

        Returns:
            True if successful
        """
        try:
            from app.models.setting import Setting

            # Convert value to string for storage
            str_value = str(value) if value is not None else None

            Setting.set_value(
                key=key,
                value=str_value,
                category=category,
                description=description,
                is_sensitive=is_sensitive,
                user_id=user_id,
            )

            # Clear cache for this key
            self._cache.pop(key, None)

            return True

        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False

    def get_category(self, category: str) -> Dict[str, Any]:
        """Get all settings in a category"""
        try:
            from app.models.setting import Setting

            settings = Setting.get_by_category(category)
            return {
                setting.key: self._convert_value(setting.value) for setting in settings
            }
        except Exception as e:
            logger.error(f"Error getting category {category}: {e}")
            return {}

    def get_all_categories(self) -> Dict[str, Dict[str, Any]]:
        """Get all settings grouped by category"""
        try:
            from app.models.setting import Setting
            from app import db

            settings = Setting.query.all()
            result = {}

            for setting in settings:
                if setting.category not in result:
                    result[setting.category] = {}

                # Mask sensitive values
                if setting.is_sensitive and setting.value:
                    value = "********"
                else:
                    value = setting.value

                result[setting.category][setting.key] = {
                    "value": value,
                    "description": setting.description,
                    "is_sensitive": setting.is_sensitive,
                    "updated_at": setting.updated_at,
                }

            return result

        except Exception as e:
            logger.error(f"Error getting all categories: {e}")
            return {}

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        if value is None:
            return None

        # Try to convert to appropriate type
        value_lower = value.lower()

        # Boolean conversion
        if value_lower in ("true", "yes", "1", "on"):
            return True
        if value_lower in ("false", "no", "0", "off"):
            return False

        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass

        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def initialise_defaults(self):
        """initialise default settings"""
        try:
            from app.models.setting import Setting

            Setting.initialise_defaults()
            logger.info("Default settings initialised")
        except Exception as e:
            logger.error(f"Error initializing defaults: {e}")

    def build_config_dict(self) -> Dict[str, Any]:
        """Build configuration dictionary from database settings"""
        config = {}

        try:
            from app.models.setting import Setting

            settings = Setting.query.all()

            for setting in settings:
                config[setting.key] = self._convert_value(setting.value)

        except Exception as e:
            logger.warning(f"Could not load settings from database: {e}")

        return config


# Global instance
settings_service = SettingsService()
