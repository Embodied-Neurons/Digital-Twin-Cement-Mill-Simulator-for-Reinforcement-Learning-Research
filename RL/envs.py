"""Fabryki środowisk – JEDYNE miejsce, które trzeba ruszyć przy zmianie środowiska.

Własne środowisko zarejestruj tutaj (gym.register(...)) albo zaimportuj moduł,
który to robi – wtedy będzie dostępne przez --env-id we wszystkich skryptach.
"""
import gymnasium as gym
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecEnv

# Przykład rejestracji własnego środowiska:
# import my_package.my_env  
# wywołanie gym.register(id="MyEnv-v0", ...)


def make_train_env(env_id: str, n_envs: int, seed: int, env_kwargs: dict | None = None) -> VecEnv:
    return make_vec_env(env_id, n_envs=n_envs, seed=seed, env_kwargs=env_kwargs or {})


def make_eval_env(env_id: str, seed: int, env_kwargs: dict | None = None) -> VecEnv:
    return make_vec_env(env_id, n_envs=1, seed=seed, env_kwargs=env_kwargs or {})


def make_play_env(env_id: str, render: bool, env_kwargs: dict | None = None) -> gym.Env:
    render_mode = "human" if render else None
    return gym.make(env_id, render_mode=render_mode, **(env_kwargs or {}))
