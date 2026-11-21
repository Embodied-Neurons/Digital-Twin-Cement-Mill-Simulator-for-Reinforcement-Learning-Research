"""Wczytanie zapisanego agenta i uruchomienie go w środowisku.

    python play.py --model-path models/ppo_CartPole-v1_seed0 --episodes 5 Dla wbudowanych środowisk Gymnasium wizualizacja wymaga biblioteki pygame
    python play.py --no-render      # bez okna, np. na serwerze
"""
import argparse

from stable_baselines3 import PPO

from config import add_common_args, default_model_path
from envs import make_play_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Uruchom zapisanego agenta PPO")
    add_common_args(p)
    p.add_argument("--model-path", default=None, help="domyślnie models/ppo_<env>_seed<seed>")
    p.add_argument("--episodes", type=int, default=5)
    p.add_argument("--no-render", action="store_true", help="bez okna")
    p.add_argument("--stochastic", action="store_true", help="losuj akcje zamiast deterministycznych")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    model_path = args.model_path or default_model_path(args.env_id, args.seed)
    model = PPO.load(model_path, device=args.device)
    env = make_play_env(args.env_id, render=not args.no_render, env_kwargs=args.env_kwargs)

    returns = []
    for ep in range(args.episodes):
        obs, _ = env.reset(seed=args.seed + ep)
        done, total = False, 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=not args.stochastic or False)
            obs, reward, terminated, truncated, _ = env.step(action)
            total += reward
            done = terminated or truncated
        returns.append(total)
        print(f"Epizod {ep + 1}: nagroda = {total:.2f}")
    env.close()
    print(f"Średnia nagroda: {sum(returns) / len(returns):.2f}")


if __name__ == "__main__":
    main()
