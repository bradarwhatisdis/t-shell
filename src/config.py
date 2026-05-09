import os
import sys
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.config_path = Path.home() / ".t-shell" / ".env"
        self._ensure_config_dir()
        load_dotenv(self.config_path)

    def _ensure_config_dir(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            self.config_path.write_text("")

    @property
    def api_id(self) -> str:
        return os.getenv("API_ID", "")

    @property
    def api_hash(self) -> str:
        return os.getenv("API_HASH", "")

    @property
    def phone(self) -> str:
        return os.getenv("PHONE", "")

    def save_credentials(self, api_id: str, api_hash: str, phone: str):
        with open(self.config_path, "w") as f:
            f.write(f"API_ID={api_id}\n")
            f.write(f"API_HASH={api_hash}\n")
            f.write(f"PHONE={phone}\n")
        os.environ["API_ID"] = api_id
        os.environ["API_HASH"] = api_hash
        os.environ["PHONE"] = phone

    def has_credentials(self) -> bool:
        return bool(self.api_id and self.api_hash and self.phone)