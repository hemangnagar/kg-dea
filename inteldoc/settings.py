"""Explicit runtime configuration; offline remains the no-key default."""
import os
from pathlib import Path
import yaml
from .world import ROOT


def load_config(path=None):
    path = Path(path or os.getenv('INTELDOC_MODEL_CONFIG') or ROOT / 'config/corpus.yaml')
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict):
        raise ValueError('Model configuration must be a YAML mapping')
    for key in ['provider', 'query_provider']:
        if config.get(key, 'offline') not in ['offline', 'authored', 'openai', 'ollama']:
            raise ValueError(f'Unsupported {key}')
    if config.get('extraction', 'deterministic') not in ['deterministic', 'model']:
        raise ValueError('Unsupported extraction mode')
    return config
