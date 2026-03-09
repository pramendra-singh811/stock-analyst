import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECTS_DIR = BASE_DIR / "projects"
OUTPUTS_DIR = BASE_DIR / "outputs"
CONFIG_FILE = BASE_DIR / "config.yaml"


def load_config() -> dict:
    """Load the main config.yaml."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f) or {}


def save_config(cfg: dict) -> None:
    """Write config back to config.yaml."""
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)


def get_project_dir(ticker: str) -> Path:
    """Return (and create) the project directory for a given ticker."""
    project_dir = PROJECTS_DIR / ticker.upper()
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "documents").mkdir(exist_ok=True)
    (project_dir / "outputs").mkdir(exist_ok=True)
    return project_dir


def load_project_meta(ticker: str) -> dict:
    """Load per-project metadata."""
    meta_file = get_project_dir(ticker) / "meta.yaml"
    if not meta_file.exists():
        return {}
    with open(meta_file, "r") as f:
        return yaml.safe_load(f) or {}


def save_project_meta(ticker: str, meta: dict) -> None:
    """Save per-project metadata."""
    meta_file = get_project_dir(ticker) / "meta.yaml"
    with open(meta_file, "w") as f:
        yaml.dump(meta, f, default_flow_style=False, sort_keys=False)


def get_api_key() -> str:
    """Retrieve the Anthropic API key from config or environment."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    cfg = load_config()
    key = cfg.get("anthropic_api_key")
    if not key:
        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY env var or add "
            "'anthropic_api_key' to config.yaml"
        )
    return key
