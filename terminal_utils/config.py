import os
import argparse
from pathlib import Path
import json

class AiderConfig:
    def __init__(self):
        self.config_path = Path.home() / '.aider.conf.json'
        self.models = {
            'gemini': {
                'name': 'gemini-1.5-pro',
                'env_var': 'GOOGLE_API_KEY',
                'provider': 'google'
            },
            'sonnet': {
                'name': 'claude-3-sonnet-20240229',
                'env_var': 'ANTHROPIC_API_KEY',
                'provider': 'anthropic'
            }
        }
        self.load_config()

    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.saved_config = json.load(f)
        else:
            self.saved_config = {}

    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.saved_config, f, indent=2)

    def setup_api_keys(self):
        for model_info in self.models.values():
            env_var = model_info['env_var']
            if env_var not in os.environ:
                key = input(f"Enter {env_var}: ").strip()
                if key:
                    os.environ[env_var] = key
                    self.saved_config[env_var] = key

    def configure_model(self, model_name):
        if model_name not in self.models:
            print(f"Invalid model selection. Available models: {', '.join(self.models.keys())}")
            return None
        
        model_info = self.models[model_name]
        return {
            'model': model_info['name'],
            'provider': model_info['provider']
        }

    def set_dark_mode(self, enabled=True):
        os.environ['AIDER_DARK_MODE'] = '1' if enabled else '0'
        self.saved_config['dark_mode'] = enabled

def main():
    parser = argparse.ArgumentParser(description='Configure aider settings and model selection')
    parser.add_argument('--model', choices=['gemini', 'sonnet'], help='Select the model to use')
    parser.add_argument('--dark-mode', action='store_true', help='Enable dark mode')
    parser.add_argument('--light-mode', action='store_true', help='Enable light mode')
    args = parser.parse_args()

    config = AiderConfig()
    
    # Setup API keys
    config.setup_api_keys()

    # Handle dark/light mode
    if args.dark_mode:
        config.set_dark_mode(True)
    elif args.light_mode:
        config.set_dark_mode(False)

    # Configure selected model
    if args.model:
        model_config = config.configure_model(args.model)
        if model_config:
            config.saved_config['last_model'] = model_config
    
    # Save configuration
    config.save_config()

    # Print current configuration
    print("\nCurrent Configuration:")
    print(f"Dark Mode: {'Enabled' if config.saved_config.get('dark_mode', False) else 'Disabled'}")
    if 'last_model' in config.saved_config:
        print(f"Selected Model: {config.saved_config['last_model']['model']}")
    
    # Generate the aider command
    cmd_parts = ['aider']
    if 'last_model' in config.saved_config:
        model_config = config.saved_config['last_model']
        cmd_parts.extend(['--model', model_config['model']])
        if model_config['provider'] != 'openai':
            cmd_parts.extend(['--provider', model_config['provider']])
    
    print("\nTo start aider with these settings, run:")
    print(' '.join(cmd_parts))

if __name__ == '__main__':
    main()