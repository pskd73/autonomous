import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    openrouter_api_key: str
    openrouter_model: str
    workspace_path: str
    host: str
    port: int

    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "moonshotai/kimi-k2.5")
        self.workspace_path = os.getenv("WORKSPACE_PATH", os.path.abspath("./workspace"))
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))

        Path(self.workspace_path).mkdir(parents=True, exist_ok=True)
        self._validate()

    def _validate(self):
        if not self.openrouter_api_key:
            raise ValueError("Missing required environment variable: OPENROUTER_API_KEY")