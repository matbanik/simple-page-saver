"""
Settings management with encrypted API key storage
Stores configuration in settings.json
"""

import json
import base64
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SettingsManager:
    """Manage application settings with encrypted API key"""

    def __init__(self, settings_file: str = 'settings.json'):
        self.settings_file = Path(settings_file)
        self.settings = self._load_settings()
        self._cipher = self._get_cipher()

    def _get_cipher(self) -> Fernet:
        """Get encryption cipher using machine-specific key"""
        # Use machine-specific salt (stored in settings or generated)
        salt = self.settings.get('_salt')
        if not salt:
            salt = base64.urlsafe_b64encode(Fernet.generate_key()[:16]).decode()
            self.settings['_salt'] = salt
            self._save_settings()

        # Derive key from salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b'simple_page_saver_key'))
        return Fernet(key)

    def _load_settings(self) -> dict:
        """Load settings from JSON file"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f'Error loading settings: {e}')
                return self._default_settings()
        return self._default_settings()

    def _default_settings(self) -> dict:
        """Return default settings"""
        return {
            'server_port': 8077,
            'default_model': 'deepseek/deepseek-chat',
            'max_tokens': 32000,
            'log_level': 'INFO',
            'worker_count': 4,
            'overlap_percentage': 10,
            'extraction_strategy': 'markdown',
            'openrouter_api_key_encrypted': None,
            '_salt': None
        }

    def _save_settings(self):
        """Save settings to JSON file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f'Error saving settings: {e}')

    def get(self, key: str, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value"""
        self.settings[key] = value
        self._save_settings()

    def get_api_key(self) -> Optional[str]:
        """Get decrypted API key"""
        encrypted = self.settings.get('openrouter_api_key_encrypted')
        if not encrypted:
            return None

        try:
            decrypted_bytes = self._cipher.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            print(f'Error decrypting API key: {e}')
            return None

    def set_api_key(self, api_key: str):
        """Set encrypted API key"""
        if not api_key:
            self.settings['openrouter_api_key_encrypted'] = None
        else:
            try:
                encrypted_bytes = self._cipher.encrypt(api_key.encode())
                self.settings['openrouter_api_key_encrypted'] = encrypted_bytes.decode()
            except Exception as e:
                print(f'Error encrypting API key: {e}')
                return

        self._save_settings()

    def get_all_settings(self) -> dict:
        """Get all settings (with masked API key)"""
        settings_copy = self.settings.copy()
        if settings_copy.get('openrouter_api_key_encrypted'):
            settings_copy['openrouter_api_key'] = '***MASKED***'
            del settings_copy['openrouter_api_key_encrypted']
        if '_salt' in settings_copy:
            del settings_copy['_salt']
        return settings_copy

    def export_for_env(self) -> dict:
        """Export settings in format suitable for environment variables"""
        api_key = self.get_api_key()
        return {
            'OPENROUTER_API_KEY': api_key or '',
            'DEFAULT_MODEL': self.get('default_model', 'deepseek/deepseek-chat'),
            'MAX_TOKENS': str(self.get('max_tokens', 32000)),
            'SERVER_PORT': str(self.get('server_port', 8077)),
            'LOG_LEVEL': self.get('log_level', 'INFO')
        }
