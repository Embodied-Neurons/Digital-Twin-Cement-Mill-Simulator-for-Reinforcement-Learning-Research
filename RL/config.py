"""Wspólne ustawienia domyślne i argumenty CLI dla train.py i play.py."""
import argparse
import json
from pathlib import Path

DEFAULT_ENV_ID = "CartPole-v1"   # <- tu (lub przez --env-id) zmieniasz środowisko
DEFAULT_POLICY = "MlpPolicy"     # dla obserwacji-obrazów: "CnnPolicy"
DEFAULT_SEED = 0

MODELS_DIR = Path(__file__).resolve().parent / "models"


def default_model_path(env_id: str, seed: int) -> Path:
    """Domyślna ścieżka zapisu/odczytu (bez rozszerzenia .zip)."""
    return MODELS_DIR / f"ppo_{env_id}_seed{seed}"


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env-id", default=DEFAULT_ENV_ID, help="id środowiska Gymnasium")
    parser.add_argument(
        "--env-kwargs", type=json.loads, default={},
        help='argumenty środowiska jako JSON, np. \'{"gravity": 5.0}\'',
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--device", default="auto", help="auto / cpu / cuda")
