from dataclasses import replace
import math

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box

from parameters import DEFAULT_INPUTS, MAX_SEPARATOR_RPM, MIN_SEPARATOR_RPM, Inputs
from simulation import MillSimulation


class CementMillEnv(gym.Env):
    """Sterowanie obrotami separatora w celu utrzymania zadanego Blaine’a."""

    metadata = {"render_modes": []}

    observation_fields = (
        "blaine_cm2_g", "product_tph", "recycle_tph", "power_kw",
        "chamber1_fill_pct", "chamber2_fill_pct", "separator_rpm",
        "feed_tph", "hardness", "gas_flow_nm3_h", "blaine_available",
    )
    observation_scales = (3000, 100, 100, 3000, 100, 100, 1000, 100, 1, 10000, 1)

    def __init__(self, *, target_blaine=3000.0, initial_inputs=DEFAULT_INPUTS,
                 step_minutes=1.0, rpm_step=10.0):
        if not isinstance(initial_inputs, Inputs):
            raise ValueError("initial_inputs musi być obiektem Inputs.")
        for name, value in (("target_blaine", target_blaine),
                            ("step_minutes", step_minutes), ("rpm_step", rpm_step)):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} musi być dodatnią, skończoną liczbą.")
        self.target_blaine = float(target_blaine)
        self.initial_inputs = initial_inputs
        self.step_minutes = step_minutes
        self.rpm_step = rpm_step
        self.action_space = Box(-1.0, 1.0, shape=(1,), dtype=np.float32)
        self.observation_space = Box(
            low=np.zeros(len(self.observation_fields), dtype=np.float32),
            high=np.array([np.inf] * (len(self.observation_fields) - 1) + [1], dtype=np.float32),
        )
        self.render_mode = None
        self._simulation = MillSimulation()
        self._needs_reset = True

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        options = {} if options is None else options
        snapshot = self._simulation.reset(
            options.get("inputs", self.initial_inputs),
            start_empty=options.get("start_empty", False),
        )
        self._needs_reset = False
        return self._observe(snapshot)

    def step(self, action):
        if self._needs_reset:
            raise gym.error.ResetNeeded("Wywołaj reset() przed rozpoczęciem epizodu.")
        action = np.asarray(action, dtype=np.float64)
        if action.shape != self.action_space.shape or not -1 <= action[0] <= 1:
            raise ValueError("Akcja musi zawierać jedną liczbę z przedziału [-1, 1].")

        inputs = self._simulation.inputs
        rpm = float(np.clip(inputs.separator_rpm + action[0] * self.rpm_step,
                            MIN_SEPARATOR_RPM, MAX_SEPARATOR_RPM))
        snapshot = self._simulation.step(self.step_minutes, replace(inputs, separator_rpm=rpm))
        terminated = snapshot["terminated"]
        self._needs_reset = terminated

        observation, info = self._observe(snapshot)
        blaine = info["blaine_cm2_g"]
        reward = -abs(blaine - self.target_blaine) / 1000 if blaine is not None else -1.0
        if terminated:
            reward -= 5.0
        return observation, reward, terminated, False, info

    def _observe(self, snapshot):
        info = {
            key: None if isinstance(value, float) and math.isnan(value) else value
            for key, value in snapshot.items()
        }
        info["blaine_available"] = info["blaine_cm2_g"] is not None
        info["target_blaine_cm2_g"] = self.target_blaine
        observation = np.array([
            (info[field] or 0) / scale
            for field, scale in zip(self.observation_fields, self.observation_scales)
        ], dtype=np.float32)
        return observation, info


gym.register(
    id="CementMill-v0",
    entry_point="mill_env:CementMillEnv",
    max_episode_steps=120,
)
