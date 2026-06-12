import json
import os
from datetime import datetime

from env import Env
from logger_config import logger


class BanHandler:
    def __init__(self):
        self.env = Env()
        self.db_path = os.path.join(self.env.CONFIG_PATH, "banned_users.json")
        self.banned = self._load()

    def _load(self) -> dict:
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"BanHandler _load error: {e}")
        return {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, "w") as f:
                json.dump(self.banned, f, indent=2)
        except Exception as e:
            logger.error(f"BanHandler _save error: {e}")

    def ban(self, user_id: int, reason: str = "") -> bool:
        uid = str(user_id)
        if uid in self.banned:
            return False
        self.banned[uid] = {
            "banned_at": str(datetime.now()),
            "reason": reason,
        }
        self._save()
        return True

    def unban(self, user_id: int) -> bool:
        uid = str(user_id)
        if uid not in self.banned:
            return False
        del self.banned[uid]
        self._save()
        return True

    def is_banned(self, user_id: int) -> bool:
        return str(user_id) in self.banned

    def get_info(self, user_id: int) -> dict:
        return self.banned.get(str(user_id), {})

    def all_banned(self) -> dict:
        return self.banned
