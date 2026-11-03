from dataclasses import dataclass, asdict
import math


CEMENT_ID = 6
CEMENT_NAME = "CEM I 52,5R-NA"
MODEL_STATUS = "model roboczy · wymaga kalibracji"


@dataclass(frozen=True)
class Inputs:
    feed_tph: float = 80.0
    separator_rpm: float = 1000.0
    hardness: float = 1.0

    def __post_init__(self):
        for name, low, high in (("feed_tph", 0, 200),
                                ("separator_rpm", 500, 1800),
                                ("hardness", 0.5, 2.0)):
            value = getattr(self, name)
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{name}: wymagana wartość od {low} do {high}.")


@dataclass(frozen=True)
class Scenario:
    before: Inputs = Inputs()
    after: Inputs = Inputs(feed_tph=100.0)
    duration_min: float = 240.0
    step_min: float = 60.0
    start_empty: bool = False

    def __post_init__(self):
        if not math.isfinite(self.duration_min) or self.duration_min < 1:
            raise ValueError("Czas symulacji musi być skończoną liczbą wynoszącą co najmniej 1 min.")
        if not math.isfinite(self.step_min) or not 0 <= self.step_min <= self.duration_min:
            raise ValueError("Moment zmiany musi mieścić się w czasie symulacji.")


@dataclass(frozen=True)
class Parameters:
    classes: int = 14
    top_size_um: float = 25000.0
    diaphragm_um: float = 6250.0
    mixing_per_h: float = 180.0
    availability_time_h: float = 1/3600
    transport1_per_h: float = 0.0171 * 3600
    transport2_per_h: float = 0.00705 * 3600
    transport1_offset_tph: float = 0.0981 * 3.6
    transport2_offset_tph: float = 0.0717 * 3.6
    breakage1_per_h: float = 20.672535429875705
    breakage2_per_h: float = 29.532193471251006
    mu1_um: float = 8000.0
    mu2_um: float = 1200.0
    alpha: float = 0.6
    breakage_lambda: float = 2.0
    phi: float = 0.35
    gamma: float = 0.6
    beta: float = 3.0
    mill_diameter_m: float = 4.5
    mill_length_m: float = 16.0
    material_density_t_m3: float = 3.0549
    ball_void_fraction: float = 0.4
    ball_fill1: float = 0.284
    ball_fill2: float = 0.35
    reference_ball_fill: float = 0.3
    reference_void_filling: float = 0.6
    ball_diameter1_mm: float = 100.0
    ball_diameter2_mm: float = 25.0
    reference_ball_diameter1_mm: float = 80.0
    reference_ball_diameter2_mm: float = 25.0
    ball_size_exponent: float = 1.0
    load_sensitivity: float = 1.2
    cut_size_um: float = 75.99022120380447
    sharpness: float = 3.0
    bypass: float = 0.0922
    feed_scale_um: float = 4000.0
    idle_power_kw: float = 2653.762288141352
    load_power_kw: float = 453.42110023069813
    separator_power_kw: float = 223.74079930202274
    separator_idle_power_kw: float = 10.471630935880448
    power_scale: float = 1.0

    @classmethod
    def demonstration(cls):
        """Tworzy zestaw parametrów demonstracyjnych."""
        return cls(breakage1_per_h=35.0, breakage2_per_h=50.0,
                   cut_size_um=45.0, idle_power_kw=1000., load_power_kw=1200.,
                   separator_power_kw=80., separator_idle_power_kw=0., power_scale=1.0)

    def __post_init__(self):
        if not isinstance(self.classes, int) or not 4 <= self.classes <= 40:
            raise ValueError("Liczba klas musi być całkowita, od 4 do 40.")
        for name, value in asdict(self).items():
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Niepoprawny parametr: {name}.")
            if name not in ("bypass", "phi", "idle_power_kw", "load_power_kw",
                            "separator_power_kw", "separator_idle_power_kw", "mixing_per_h",
                            "transport1_offset_tph", "transport2_offset_tph",
                            "reference_void_filling", "load_sensitivity") and value == 0:
                raise ValueError(f"Parametr {name} musi być dodatni.")
        if not 0 <= self.phi <= 1 or not 0 <= self.bypass < 1:
            raise ValueError("phi musi być w [0, 1], bypass w [0, 1).")
        for name in ('ball_fill1', 'ball_fill2', 'reference_ball_fill', 'ball_void_fraction'):
            if not 0 < getattr(self, name) < 1:
                raise ValueError(f'{name} musi należeć do (0, 1).')
        if self.diaphragm_um < self.top_size_um / 2 ** (self.classes - 1):
            raise ValueError("Przepona musi przepuszczać co najmniej najmniejszą klasę.")


DEFAULT_INPUTS = Inputs(50, 669.9, 1)
