"""Loads system configuration from a YAML file."""

import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "settings.yaml")

def get_config(config=None):
    """Loads configuration from settings.yaml."""
    try:
        with open(CONFIG_PATH, "r") as file:
            settings = yaml.safe_load(file)
        return settings if config is None else settings.get(config, {})
    except Exception as e:
        print(f"⚠️ Error loading config: {e}")
        return {}

# Load API Key from settings.yaml
OPENAI_API_KEY = get_config().get("openai_api_key", "")
