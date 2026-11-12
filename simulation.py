import math

import numpy as np

from parameters import CEMENT_ID, DEFAULT_INPUTS, Inputs, Parameters, Scenario
from model import CementMill
from results import Result


class MillSimulation:
    """Przechowuje stan procesu i wykonuje kolejne kroki symulacji."""

    def __init__(self, parameters=None, *, rtol=1e-7):
        if not math.isfinite(rtol) or rtol <= 0:
            raise ValueError('rtol musi być dodatnią, skończoną liczbą.')
        self.default_inputs = DEFAULT_INPUTS
        self.model = CementMill(parameters)
        self.cement_id = CEMENT_ID if parameters is None else None
        self.rtol = rtol
        self.reset()

    @property
    def time_min(self):
        return self._time_h * 60

    @property
    def state(self):
        """Zwraca kopię mas klas ziaren oraz liczników produktu, nadawy i energii."""
        return self._state.copy()

    @property
    def terminated(self):
        return self._terminated

    def reset(self, inputs=None, *, start_empty=True):
        """Ustawia stan początkowy i zeruje czas oraz liczniki."""
        inputs = self.default_inputs if inputs is None else inputs
        if not isinstance(inputs, Inputs):
            raise ValueError('Nastawy muszą być obiektem Inputs.')
        state = self.model.initial_state(inputs, empty=start_empty)
        self._state = state
        self.inputs = inputs
        self._time_h = 0.0
        self._terminated = False
        self.initial_mass = float(state[:-3].sum())
        return self.observe()

    def _advance(self, end_h, inputs, times=None):
        if self.terminated:
            raise RuntimeError('Symulacja zakończona po zamieleniu. Uruchom ją od początku.')
        sol = self.model._integrate(self._state, inputs, (self._time_h, end_h), times, self.rtol)
        self._state = sol.y[:, -1].copy()
        self._time_h = float(sol.t[-1])
        self._terminated = sol.status == 1
        self.inputs = inputs
        return sol

    def step(self, dt_min=1.0, inputs=None):
        """Przesuwa proces o podaną liczbę minut przy wybranych nastawach."""
        if not math.isfinite(dt_min) or dt_min <= 0:
            raise ValueError('Długość kroku musi być dodatnią, skończoną liczbą minut.')
        inputs = self.inputs if inputs is None else inputs
        if not isinstance(inputs, Inputs):
            raise ValueError('Nastawy muszą być obiektem Inputs.')
        end_h = self._time_h + dt_min / 60
        if not math.isfinite(end_h) or end_h <= self._time_h:
            raise ValueError('Krok jest zbyt mały lub czas przekracza zakres liczbowy.')
        self._advance(end_h, inputs, [end_h])
        return self.observe()

    def observe(self):
        """Zwraca bieżące pomiary bez przesuwania czasu."""
        return self._snapshot(self._state, self._time_h, self.inputs, terminated=self.terminated)

    def set_inputs(self, inputs):
        """Ustawia nowe nastawy bez przesuwania czasu i zmiany mas oraz liczników."""
        if not isinstance(inputs, Inputs):
            raise ValueError('Nastawy muszą być obiektem Inputs.')
        if self.terminated:
            raise RuntimeError('Symulacja zakończona po zamieleniu. Uruchom ją od początku.')
        self.inputs = inputs
        return self.observe()

    def _snapshot(self, state, time_h, inputs, *, terminated=False):
        terminated = bool(terminated)
        model = self.model
        transfer, product, recycle = model.flows(state, inputs)
        rate = float(product.sum())
        mill_power, separator_power = model.power_components(state, inputs)
        power = mill_power + separator_power
        r45 = 100 * (1 - model.passing(product / rate, 45)) if rate > 1e-8 else math.nan
        d32 = model.sauter_diameter(product / rate) if rate > 1e-8 else math.nan
        blaine = model.blaine(product / rate) if rate > 1e-8 else math.nan
        masses = model.chamber_masses(state)
        filling = model.charge_filling(state)
        jammed_chamber = int(np.argmax(filling)) + 1 if terminated else 0
        reactor_masses = model.inventories(state).sum(axis=1)
        return dict(time_min=time_h*60, feed_tph=inputs.feed_tph,
                    separator_rpm=inputs.separator_rpm, hardness=inputs.hardness,
                    gas_flow_nm3_h=inputs.gas_flow_nm3_h,
                    product_tph=rate, recycle_tph=float(recycle.sum()),
                    transfer_tph=float(transfer.sum()), discharge_tph=rate + float(recycle.sum()),
                    chamber1_t=float(masses[0]), chamber2_t=float(masses[1]),
                    chamber1_fill_pct=float(100 * filling[0]),
                    chamber2_fill_pct=float(100 * filling[1]),
                    terminated=terminated, jammed_chamber=jammed_chamber,
                    termination_reason='mill_overfill' if terminated else '',
                    **{f'cstr{i+1}_t': float(mass) for i, mass in enumerate(reactor_masses)},
                    residue45_pct=r45, product_d32_um=d32, blaine_cm2_g=blaine, power_kw=power,
                    mill_power_kw=mill_power, separator_power_kw=separator_power,
                    specific_energy_kwh_t=power/rate if rate > 1e-8 else math.nan,
                    product_total_t=float(state[-3]), feed_total_t=float(state[-2]),
                    energy_kwh=float(state[-1]),
                    mass_error_t=float(state[:-3].sum() + state[-3] - self.initial_mass - state[-2]))

    def result(self, observations, scenario=None):
        """Łączy zebrane obserwacje i końcowe rozkłady ziaren w wynik symulacji."""
        if not observations:
            raise ValueError('Brak obserwacji do zapisania.')
        if observations[-1]['time_min'] != self.time_min:
            raise ValueError('Ostatnia obserwacja musi odpowiadać bieżącemu czasowi.')
        def normalized(flow):
            total = flow.sum()
            return (flow / total).tolist() if total > 1e-8 else [0.0] * self.model.p.classes
        _, product, recycle = self.model.flows(self._state, self.inputs)
        return Result(scenario, self.model.p,
                      {key: [row[key] for row in observations] for key in observations[0]},
                      {'upper_um': self.model.sizes.tolist(), 'feed': self.model.feed_fractions.tolist(),
                       'product': normalized(product), 'recycle': normalized(recycle)}, self.cement_id)


def simulate(scenario: Scenario | None = None, parameters: Parameters | None = None,
             sample_seconds=30.0, rtol=1e-7) -> Result:
    scenario = scenario or Scenario()
    if not math.isfinite(sample_seconds) or sample_seconds < 1:
        raise ValueError("Odstęp zapisu musi wynosić co najmniej 1 s.")
    simulation = MillSimulation(parameters, rtol=rtol)
    simulation.reset(scenario.before, start_empty=scenario.start_empty)
    end, step = scenario.duration_min / 60, scenario.step_min / 60
    grid = np.unique(np.r_[np.arange(0, end, sample_seconds / 3600), step, end])
    all_times, all_states = [0.0], [simulation.state]
    boundaries = sorted(set([0.0, step, end]))
    for a, b in zip(boundaries[:-1], boundaries[1:]):
        inputs = scenario.before if a < step else scenario.after
        times = np.unique(np.r_[a, grid[(grid > a) & (grid < b)], b])
        sol = simulation._advance(b, inputs, times)
        all_times.extend(sol.t[1:])
        all_states.extend(sol.y[:, 1:].T)
        if simulation.terminated:
            break
    rows = []
    for t, y in zip(all_times, all_states):
        inputs = scenario.before if t < step else scenario.after
        if simulation.terminated and t == all_times[-1]:
            inputs = simulation.inputs
        rows.append(simulation._snapshot(y, t, inputs,
                    terminated=simulation.terminated and t == all_times[-1]))
    if not simulation.terminated:
        simulation.inputs = scenario.after
    return simulation.result(rows, scenario)
