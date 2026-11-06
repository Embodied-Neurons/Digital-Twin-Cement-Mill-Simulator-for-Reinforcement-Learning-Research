import math

import numpy as np
from scipy.integrate import solve_ivp

from parameters import Inputs, Parameters


class CementMill:
    reactors = 5

    def __init__(self, parameters: Parameters | None = None):
        self.p = parameters or Parameters()
        p = self.p
        self.sizes = p.top_size_um / 2.0 ** np.arange(p.classes)
        self.lower = np.r_[self.sizes[1:], 0.0]
        self.screen = (self.sizes <= p.diaphragm_um).astype(float)
        cdf = lambda x: -np.expm1(-(x / p.feed_scale_um) ** 1.1)
        self.feed_fractions = (cdf(self.sizes) - cdf(self.lower)) / cdf(self.sizes[0])
        self.breakage_distribution = self._fragment_distribution()
        self.k1 = self._rate_matrix(p.breakage1_per_h, p.mu1_um,
                                   p.ball_diameter1_mm, p.reference_ball_diameter1_mm)
        self.k2 = self._rate_matrix(p.breakage2_per_h, p.mu2_um,
                                   p.ball_diameter2_mm, p.reference_ball_diameter2_mm)
        volume = math.pi * p.mill_diameter_m**2 / 4 * p.mill_length_m
        self.chamber_volumes_m3 = np.array([2/5, 3/5]) * volume
        self.transport_per_h = 60 * np.array([2, 3]) / np.array([p.residence1_min, p.residence2_min])

    @property
    def state_size(self):
        return self.reactors * self.p.classes + 3

    def inventories(self, state):
        """Zwraca masy klas ziaren w pięciu CSTR [t]."""
        return np.asarray(state)[:-3].reshape(self.reactors, self.p.classes)

    def chamber_masses(self, state):
        w = self.inventories(state)
        return np.array([w[:2].sum(), w[2:].sum()])

    def _fragment_distribution(self):
        """Tworzy macierz udziałów masowych fragmentów po rozdrobnieniu."""
        p = self.p
        b = np.zeros((p.classes, p.classes))
        for j in range(p.classes - 1):
            ratio = self.sizes[j + 1:] / self.sizes[j + 1]
            cumulative = p.phi * ratio ** p.gamma + (1 - p.phi) * ratio ** p.beta
            b[j + 1:, j] = cumulative - np.r_[cumulative[1:], 0.0]
        return b

    def _rate_matrix(self, a, mu, diameter_mm, reference_diameter_mm):
        c1 = (diameter_mm / reference_diameter_mm)**2
        c2 = (reference_diameter_mm / diameter_mm)**self.p.ball_size_exponent
        rate = (a * (self.sizes / 1000.0) ** self.p.alpha * c2
                / (1 + (self.sizes / (c1 * mu)) ** self.p.breakage_lambda))
        rate[-1] = 0.0
        return self.breakage_distribution * rate[np.newaxis, :] - np.diag(rate)

    def void_filling(self, state):
        """Oblicza stosunek objętości materiału do przestrzeni między kulami."""
        p = self.p
        void_volume = self.chamber_volumes_m3 * np.array([p.ball_fill1, p.ball_fill2]) * p.ball_void_fraction
        return np.maximum(self.chamber_masses(state), 0) / p.material_density_t_m3 / void_volume

    def breakage_factors(self, state, inputs):
        """Oblicza korekty szybkości rozdrabniania z wypełnienia i oporu materiału."""
        p = self.p
        filling = np.array([p.ball_fill1, p.ball_fill2])
        packing = (1 + 6.6 * p.reference_ball_fill**2.3) / (1 + 6.6 * filling**2.3)
        exponent = -p.load_sensitivity * (self.void_filling(state) - p.reference_void_filling)
        return packing * np.exp(np.clip(exponent, -700, 700)) / inputs.hardness

    def acceptance(self, inputs: Inputs):
        """Oblicza udział każdej klasy ziaren kierowany do produktu."""
        p = self.p
        gas_ratio = inputs.gas_flow_nm3_h / p.gas_reference_nm3_h
    
        cut_size = p.cut_size_um * 1000.0 / inputs.separator_rpm * math.sqrt(gas_ratio)
        decay = np.exp(-p.sharpness * self.sizes / cut_size)
        e = np.expm1(p.sharpness)
        return (1 - p.bypass) * e * decay / (1 + (e - 1) * decay)

    def flows(self, state, inputs):
        w = np.maximum(self.inventories(state), 0)
        transfer = self.transport_per_h[0] * self.screen * w[1]
        discharge = self.transport_per_h[1] * w[4]
        product = self.acceptance(inputs) * discharge
        return transfer, product, discharge - product

    def power(self, state, inputs):
        """Oblicza łączną moc młyna i separatora [kW]."""
        return sum(self.power_components(state, inputs))

    def power_components(self, state, inputs):
        """Oblicza osobno moc młyna i separatora [kW]."""
        load = max(float(np.sum(state[:-3])), 0.0)
        p = self.p
        mill = p.power_scale * (p.idle_power_kw + p.load_power_kw * load / (load + 40.0))
        separator = p.power_scale * (p.separator_idle_power_kw
                                    + p.separator_power_kw * (inputs.separator_rpm / 1000.0) ** 3)
        return mill, separator

    def rhs(self, _time, state, inputs):
        p = self.p
        w = self.inventories(state)
        transfer, product, recycle = self.flows(state, inputs)
        factor1, factor2 = self.breakage_factors(state, inputs)
        dw = np.empty_like(w)
        dw[:2] = factor1 * (w[:2] @ self.k1.T)
        dw[2:] = factor2 * (w[2:] @ self.k2.T)
        for a, b, rate in ((0, 1, self.transport_per_h[0]),
                           (2, 3, self.transport_per_h[1]), (3, 4, self.transport_per_h[1])):
            net = rate * ((1 + p.backmixing_ratio) * w[a] - p.backmixing_ratio * w[b])
            dw[a] -= net
            dw[b] += net
        dw[0] += inputs.feed_tph * self.feed_fractions + recycle
        dw[1] -= transfer
        dw[2] += transfer
        dw[4] -= product + recycle
        return np.r_[dw.ravel(), product.sum(), inputs.feed_tph, self.power(state, inputs)]

    def initial_state(self, inputs, empty=False):
        state = np.zeros(self.state_size)
        if empty or inputs.feed_tph == 0:
            return state
        for _ in range(12):
            solution = self._integrate(state, inputs, (0, 4))
            state = solution.y[:, -1]
            residual = np.max(np.abs(self.rhs(0, state, inputs)[:-3]))
            if residual < 1e-6 * max(inputs.feed_tph, 1):
                state[-3:] = 0
                return state
        raise ValueError("Nie uzyskano stanu ustalonego. Zmniejsz nadawę lub wybierz start z pustego młyna.")

    def _integrate(self, state, inputs, interval, times=None, rtol=1e-7):
        solution = solve_ivp(lambda t, y: self.rhs(t, y, inputs), interval,
                             state, t_eval=times, method="BDF", rtol=rtol,
                             atol=1e-9, max_step=1/30)
        if not solution.success or not np.isfinite(solution.y).all():
            raise RuntimeError("Nie udało się rozwiązać równań modelu.")
        if np.min(solution.y[:-3]) < -1e-6:
            raise RuntimeError("Solver zwrócił ujemne masy poza tolerancją numeryczną.")
        return solution

    def passing(self, fractions, sieve_um):
        """Oblicza udział materiału przechodzącego przez sito."""
        weights = np.zeros(self.p.classes)
        weights[self.sizes <= sieve_um] = 1.0
        for i, (upper, lower) in enumerate(zip(self.sizes, self.lower)):
            if lower < sieve_um < upper:
                weights[i] = (math.log(sieve_um / lower) / math.log(upper / lower)
                              if lower > 0 else sieve_um / upper)
        return float(np.dot(fractions, weights))

    def sauter_diameter(self, fractions):
        """Oblicza średnicę Sautera D[3,2] z udziałów masowych ziaren [µm]."""
        fractions = np.asarray(fractions, dtype=float)
        if (fractions.shape != self.sizes.shape or not np.isfinite(fractions).all()
                or (fractions < 0).any()):
            raise ValueError('Rozkład musi zawierać nieujemne, skończone udziały klas.')
        total = float(fractions.sum())
        if total == 0:
            return math.nan
        diameters = np.sqrt(self.sizes * np.where(self.lower > 0, self.lower,
                                                 self.sizes / 4))
        return total / float(np.dot(fractions, 1 / diameters))

    def blaine(self, fractions):
        """Szacuje powierzchnię właściwą z gęstości i średnicy Sautera [cm²/g]."""
        return 60000.0 / (self.p.material_density_t_m3 * self.sauter_diameter(fractions))
