"""An explicit single model request; never run by setup or corpus generation."""
import argparse
from pathlib import Path

import yaml

from inteldoc.providers import provider_from_config


def main():
    parser = argparse.ArgumentParser(description='Make one optional, budget-accounted model call')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--prompt-file', type=Path, required=True)
    parser.add_argument('--max-output-tokens', type=int, default=1600)
    args = parser.parse_args()
    try:
        config = yaml.safe_load(args.config.read_text())
        if not isinstance(config, dict):
            raise ValueError('Config must be a YAML mapping')
        prompt = args.prompt_file.read_text()
        provider = provider_from_config(config)
        print(provider.complete(prompt, max_tokens=args.max_output_tokens))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Model request configuration error: {exc}\n')


if __name__ == '__main__':
    main()
