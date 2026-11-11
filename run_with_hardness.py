"""Uruchamia symulację w konsoli lub oknie i zapisuje wyniki."""
import math
import json
from pathlib import Path
from main import ask
from hardness_controller import HardnessController

def run_auto_steps(inputs, minutes, step_min, hardness_controller):
    """Wykonuje kroki symulacji z automatyczną zmianą oporu."""
    
    from parameters import Inputs
    from simulation import MillSimulation
    
    simulation = MillSimulation()
    rows = [simulation.reset(inputs)]
    print(f"\nPraca krokowa: krok {step_min:g} min, koniec po {minutes:g} min.")
    print("Nadawa jest strumieniem w t/h. Nastawy obowiązują przez następny krok.")
    while simulation.time_min < minutes:
        current = simulation.inputs
        print(f"\nt = {simulation.time_min:g} min · nadawa {current.feed_tph:g} t/h"
              f" · separator {current.separator_rpm:g} obr/min · opór {current.hardness:g}")
        try:
            feed = inputs.feed_tph
            rpm = inputs.separator_rpm
            hardness = hardness_controller.get_hardness(simulation.time_min)
            rows[-1] = simulation.set_inputs(Inputs(feed, rpm, hardness))
        except (EOFError, KeyboardInterrupt):
            print('\nZakończono pracę krokową.')
            break
        observation = simulation.step(min(step_min, minutes - simulation.time_min))
        rows.append(observation)
        print(f"  Produkt {observation['product_tph']:.2f} t/h"
              f" · zwrot {observation['recycle_tph']:.2f} t/h"
              f" · Blaine z D32 (szac.) {observation['blaine_cm2_g']:.0f} cm2/g"
              f" · moc {observation['power_kw']:.0f} kW")
    return simulation.result(rows)

def summary(result, title=""):
    from plots import save_plot

    print("\nPODSUMOWANIE SYMULACJI:" + title)
    output = Path(__file__).resolve().parent / "results_comparison"
    output.mkdir(exist_ok=True)
    title = title+"_"
    (output / (title + "wyniki.csv")).write_text(result.csv_text(), encoding="utf-8-sig")
    (output / (title + "metadata.json")).write_text(json.dumps(result.metadata(), indent=2, ensure_ascii=False), encoding="utf-8")
    save_plot(result, output / (title + "wykres.png"))

    s = result.series
    print(f"\nPo {s['time_min'][-1]:g} min:")
    print(f"  Produkt: {s['product_tph'][-1]:.2f} t/h")
    blaine = s['blaine_cm2_g'][-1]
    print(f"  Blaine z D32 (szac.): {blaine:.0f} cm2/g" if math.isfinite(blaine)
            else "  Blaine: brak produktu")
    residue = s['residue45_pct'][-1]
    print(f"  Pozostałość na sicie 45 µm: {residue:.2f}%" if math.isfinite(residue)
            else "  Pozostałość na sicie: brak produktu")
    print(f"  Moc: {s['power_kw'][-1]:.0f} kW")
    print(f"  Wyprodukowano: {s['product_total_t'][-1]:.2f} t")
    print(f"  Zużyto energii: {s['energy_kwh'][-1]:.2f} kWh")
    print(f"\nWykres: {output / (title + 'wykres.png')}\nDane:   {output / (title + 'wyniki.csv')}")

def main():
    print("Symulator młyna cementu. Enter przyjmuje wartość domyślną.\n")
    try:
        args_feed = ask("Nadawa [t/h]", 50, 0, 200)
        args_rpm = ask("Obroty separatora [obr/min]", 700, 500, 1800)
        args_hardness = ask("Opór rozdrabniania (1 = bazowy)", 1, 0.5, 2)
        args_minutes = ask("Czas symulacji [min]", 120, 1)
        args_interval = ask("Długość kroku [min]", 1.0, 0.02, 10.0)
    except (EOFError, KeyboardInterrupt):
        print("\nPrzerwano.")
        return 1

    from parameters import Inputs
    
    try:
        inputs = Inputs(args_feed, args_rpm, args_hardness)
        hardness_controller = HardnessController(initial_hardness=inputs.hardness, hardness_data_path="hardnessData.json")
        result_custom_hardness = run_auto_steps(inputs, args_minutes, args_interval, hardness_controller)
        inputs = Inputs(args_feed, args_rpm, args_hardness)
        hardness_controller = HardnessController(initial_hardness=inputs.hardness, hardness_data_path=None)
        result_constant_hardness = run_auto_steps(inputs, args_minutes, args_interval, hardness_controller)
    except (ValueError, RuntimeError) as error:
        print(f"\nBłąd: {error}")
        return 1

    summary(result_custom_hardness, title="zmienny_opor")
    summary(result_constant_hardness, title="staly_opor")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())