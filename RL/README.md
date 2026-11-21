# PPO + stable-baselines3 + Gymnasium

Struktura:

| plik | rola |
|---|---|
| `config.py` | domyślne ustawienia (środowisko, polityka, seed), ścieżki modeli, wspólne argumenty CLI |
| `envs.py` | fabryki środowisk – tu zmieniasz/rejestrujesz środowisko |
| `train.py` | trening, zapis modelu, szybka ocena |
| `play.py` | wczytanie zapisanego modelu i uruchomienie |

## Instalacja
    pip install -r requirements.txt

## Użycie
    python train.py --timesteps 50000 --seed 0
    python play.py --seed 0                       # okno z renderem
    python play.py --seed 0 --no-render --episodes 10

Model trafia do `models/ppo_<env>_seed<seed>.zip`; `play.py` domyślnie szuka
tej samej ścieżki dla podanych `--env-id` i `--seed`. Własną ścieżkę podajesz
przez `--save-path` (train) i `--model-path` (play).

## Zmiana środowiska
    python train.py --env-id Acrobot-v1 --timesteps 200000
    python play.py  --env-id Acrobot-v1

Własne środowisko: zarejestruj je w `envs.py` (`gym.register`) i podaj jego id.
Dla obserwacji-obrazów dodaj `--policy CnnPolicy`.
