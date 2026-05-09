import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from pathlib import Path

from .config import Config

class TShellClient:
    def __init__(self, config: Config):
        self.config = config
        self.client: TelegramClient | None = None
        self.session_path = Path.home() / ".t-shell" / "session"

    async def start(self):
        if not self.config.has_credentials():
            print("Missing credentials. Please provide API_ID, API_HASH, and PHONE.")
            sys.exit(1)

        self.client = TelegramClient(
            str(self.session_path),
            int(self.config.api_id),
            self.config.api_hash
        )

        await self.client.start(phone=self.config.phone)
        me = await self.client.get_me()
        print(f"Logged in as {me.first_name} {me.last_name or ''} ({me.username})")

    async def get_dialogs(self, limit: int = 10):
        if not self.client:
            raise RuntimeError("Client not initialized. Call start() first.")

        dialogs = await self.client.get_dialogs(limit=limit)
        return dialogs

    async def close(self):
        if self.client:
            await self.client.disconnect()