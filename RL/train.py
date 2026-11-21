"""Trening agenta PPO.

    python train.py --timesteps 50000 --seed 0
    python train.py --env-id Acrobot-v1 --timesteps 200000 --save-path models/acrobot
"""
import argparse
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

from config import DEFAULT_POLICY, add_common_args, default_model_path
from envs import make_eval_env, make_train_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Trening PPO (stable-baselines3)")
    add_common_args(p)
    p.add_argument("--timesteps", type=int, default=50_000, help="łączna liczba kroków treningu")
    p.add_argument("--policy", default=DEFAULT_POLICY)
    p.add_argument("--n-envs", type=int, default=4, help="liczba równoległych środowisk")
    p.add_argument("--save-path", default=None, help="ścieżka zapisu (bez .zip)")
    p.add_argument("--eval-episodes", type=int, default=10)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    env = make_train_env(args.env_id, args.n_envs, args.seed, args.env_kwargs)
    model = PPO(args.policy, env, seed=args.seed, device=args.device, verbose=1)
    model.learn(total_timesteps=args.timesteps)

    save_path = Path(args.save_path) if args.save_path else default_model_path(args.env_id, args.seed)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(save_path)  # SB3 dopisuje .zip
    print(f"Zapisano model: {save_path}.zip")

    eval_env = make_eval_env(args.env_id, args.seed + 10_000, args.env_kwargs)
    mean_r, std_r = evaluate_policy(model, eval_env, n_eval_episodes=args.eval_episodes)
    print(f"Ocena ({args.eval_episodes} epizodów): {mean_r:.2f} +/- {std_r:.2f}")


if __name__ == "__main__":
    main()
