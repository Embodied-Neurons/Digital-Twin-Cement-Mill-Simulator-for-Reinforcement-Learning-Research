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
                "model": "five_cstr_residence_v1",
                "power": {"unit": "kW", "scope": "mill and separator drives; fans excluded",
                          "mill_method": "torque arm of ball bed, powder in its voids and separate excess-powder segment",
                          "mill_equation": "P = lift_coefficient * [sum((ball_mass + inside_powder_mass) * ball_centroid_radius) + excess_powder_first_moment]",
                          "mill_speed_and_charge_angle_assumed_constant": True,
                          "ball_density_assumed": True,
                          "separator_method": "effective angular momentum transfer to gas and solids",
                          "separator_equation": "P = (gas_power * Q/Qref + material_power * D/Dref) * (rpm/1000)^2",
                          "zero_inlet_swirl_and_fixed_effective_radius_assumed": True,
                          "gas_and_material_coefficients_not_independently_identified": True,
                          "electrical_power_coefficients_empirical": True,
                          "causal_response_validated": False},
                "charge_filling": {"method": "ball bed plus powder exceeding ball-bed voids",
                                   "method_is_approximation": True,
                                   "powder_bulk_density_t_m3": self.parameters.material_density_t_m3
                                       * (1 - self.parameters.powder_void_fraction),
                                   "powder_void_fraction_assumed": True,
                                   "limit": self.parameters.max_charge_filling,
                                   "limit_plant_confirmed": False,
                                   "terminated": bool(self.series['terminated'][-1]),
                                   "end_time_min": float(self.series['time_min'][-1]),
                                   "reason": self.series['termination_reason'][-1],
                                   "jammed_chamber": int(self.series['jammed_chamber'][-1])},
                "transport": {"method": "cells in series with axial backmixing",
                              "residence_time_unit": "min", "rtd_measurement_available": False,
                              "nominal_times_for_passing_material": True},
                "gas_flow": {"unit": "Nm3/h", "meaning": "gas flow after the mill",
                             "reference_nm3_h": self.parameters.gas_reference_nm3_h,
                             "method": "separator cut-size scaling from Stokes drag and centrifugal force",
                             "separator_flow_assumed_equal": True,
                             "separator_flow_mapping_confirmed": False,
                             "constant_gas_temperature_and_pressure_assumed": True,
                             "stokes_regime_validated": False,
                             "causal_response_validated": False},
                "state_layout": "CSTR1..5 size-class masses [t], cumulative product [t], feed [t], energy [kWh]",
                "blaine": {"unit": "cm2/g", "unit_assumed": False,
                           "historical_measurement_unit_confirmed": False,
                           "method": "60000 / (material_density_t_m3 * product_d32_um)",
                           "density_t_m3": self.parameters.material_density_t_m3,
                           "density_assumed": True, "calibrated": False,
                           "spherical_particles": True,
                           "estimated": True},
                "max_mass_error_t": float(max(abs(x) for x in self.series["mass_error_t"]))}
