from dataclasses import dataclass, asdict
import csv
import io

from parameters import CEMENT_ID, CEMENT_NAME, MODEL_STATUS, Parameters, Scenario


@dataclass
class Result:
    scenario: Scenario | None
    parameters: Parameters
    series: dict
    psd: dict
    cement_id: int | None = CEMENT_ID

    def csv_text(self):
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(self.series)
        writer.writerows(zip(*self.series.values()))
        return buffer.getvalue()

    def metadata(self):
        return {"scenario": asdict(self.scenario) if self.scenario is not None else None,
                "parameters": asdict(self.parameters),
                "parameter_status": MODEL_STATUS if self.parameters == Parameters() else "parametry własne",
                "cement_id": self.cement_id,
                "cement_name": CEMENT_NAME if self.cement_id == CEMENT_ID else None,
                "model": "five_cstr_v1",
                "state_layout": "CSTR1..5 size-class masses [t], cumulative product [t], feed [t], energy [kWh]",
                "blaine": {"unit": "cm2/g", "unit_assumed": False,
                           "historical_measurement_unit_confirmed": False,
                           "method": "60000 / (material_density_t_m3 * product_d32_um)",
                           "density_t_m3": self.parameters.material_density_t_m3,
                           "density_assumed": True, "calibrated": False,
                           "spherical_particles": True,
                           "estimated": True},
                "max_mass_error_t": float(max(abs(x) for x in self.series["mass_error_t"]))}
