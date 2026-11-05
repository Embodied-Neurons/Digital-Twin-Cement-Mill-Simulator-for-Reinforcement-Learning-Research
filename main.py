"""Uruchamia symulację w konsoli lub oknie i zapisuje wyniki."""
import argparse
import math
import json
from pathlib import Path
import sys


def ask(label, default, minimum, maximum=None):
    while True:
        raw = input(f"{label} [{default:g}]: ").strip()
        try:
            value = float(raw.replace(",", ".")) if raw else default
            if math.isfinite(value) and value >= minimum and (maximum is None or value <= maximum):
                return value
        except ValueError:
            pass
        print(f"Podaj skończoną liczbę nie mniejszą niż {minimum:g}." if maximum is None
              else f"Podaj liczbę od {minimum:g} do {maximum:g}.")


def run_steps(inputs, minutes, step_min):
    """Wykonuje kroki symulacji z ręczną zmianą nastaw."""
    from parameters import Inputs
    from simulation import MillSimulation
    simulation = MillSimulation()
    rows = [simulation.reset(inputs)]
    print(f"\nPraca krokowa: krok {step_min:g} min, koniec po {minutes:g} min.")
    print("Nadawa jest strumieniem w t/h. Nastawy obowiązują przez następny krok.")
    while simulation.time_min < minutes:
        current = simulation.inputs
        print(f"\nt = {simulation.time_min:g} min · nadawa {current.feed_tph:g} t/h"
              f" · separator {current.separator_rpm:g} obr/min · opór {current.hardness:g}"
              f" · gazy {current.gas_flow_nm3_h:g} Nm3/h")
        try:
            command = input("Enter = następny krok, z = zmień nastawy, q = zakończ: ").strip().lower()
            if command == 'q':
                break
            if command == 'z':
                feed = ask('Nadawa [t/h]', current.feed_tph, 0, 200)
                rpm = ask('Obroty separatora [obr/min]', current.separator_rpm, 500, 1800)
                hardness = ask('Opór rozdrabniania', current.hardness, 0.5, 2)
                gas = ask('Przepływ gazów za młynem [Nm3/h]', current.gas_flow_nm3_h, 5000, 30000)
                rows[-1] = simulation.set_inputs(Inputs(feed, rpm, hardness, gas))
            elif command:
                print('Wybierz Enter, z albo q.')
                continue
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


def main():
    parser = argparse.ArgumentParser(description="Prosty symulator młyna cementu")
    parser.add_argument("--feed", type=float, help="Nadawa [t/h], domyślnie 50")
    parser.add_argument("--rpm", type=float, help="Obroty separatora, domyślnie 669,9")
    parser.add_argument("--hardness", type=float, default=1, help="Opór rozdrabniania 0.5–2, domyślnie 1")
    parser.add_argument("--gas-flow", type=float, help="Przepływ gazów za młynem [Nm3/h], domyślnie około 12616")
    parser.add_argument("--minutes", type=float, default=120, help="Czas symulacji [min], domyślnie 120")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--view", action="store_true", help="Otwórz lokalne okno wizualizacji")
    mode.add_argument("--step", nargs='?', const=1.0, type=float, metavar='MIN',
                      help="Praca krokowa w konsoli; długość kroku w minutach, domyślnie 1")
    args = parser.parse_args()
    if args.step is not None and (not math.isfinite(args.step) or args.step <= 0):
        parser.error('Długość kroku --step musi być dodatnią, skończoną liczbą minut.')
    from parameters import DEFAULT_INPUTS
    if args.feed is None:
        args.feed = DEFAULT_INPUTS.feed_tph
    if args.rpm is None:
        args.rpm = DEFAULT_INPUTS.separator_rpm
    if args.gas_flow is None:
        args.gas_flow = DEFAULT_INPUTS.gas_flow_nm3_h
    if args.view:
        from visualization import ask_parameters
        selection = ask_parameters(args.feed, args.rpm, args.hardness, args.minutes, args.gas_flow)
        if selection is None:
            return 0
        args.feed, args.rpm, args.hardness, args.minutes, args.gas_flow = selection
    elif len(sys.argv) == 1:
        print("Symulator młyna cementu. Enter przyjmuje wartość domyślną.\n")
        try:
            args.feed = ask("Nadawa [t/h]", args.feed, 0, 200)
            args.rpm = ask("Obroty separatora [obr/min]", args.rpm, 500, 1800)
            args.hardness = ask("Opór rozdrabniania (1 = bazowy)", 1, 0.5, 2)
            args.gas_flow = ask("Przepływ gazów za młynem [Nm3/h]", args.gas_flow, 5000, 30000)
            args.minutes = ask("Czas symulacji [min]", 120, 1)
        except (EOFError, KeyboardInterrupt):
            print("\nPrzerwano.")
            return 1

    from parameters import Inputs, Scenario
    from simulation import simulate
    from plots import save_plot

    try:
        inputs = Inputs(args.feed, args.rpm, args.hardness, args.gas_flow)
        scenario = Scenario(before=inputs, after=inputs, duration_min=args.minutes,
                            step_min=0, start_empty=True)
        if args.view:
            from visualization import show_live
            result = show_live(inputs, minutes=args.minutes)
        elif args.step is not None:
            result = run_steps(inputs, args.minutes, args.step)
        else:
            result = simulate(scenario)
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))

    output = Path(__file__).resolve().parent / "results"
    output.mkdir(exist_ok=True)
    (output / "wyniki.csv").write_text(result.csv_text(), encoding="utf-8-sig")
    (output / "metadata.json").write_text(json.dumps(result.metadata(), indent=2, ensure_ascii=False), encoding="utf-8")
    save_plot(result, output / "wykres.png")
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
    print(f"\nWykres: {output / 'wykres.png'}\nDane:   {output / 'wyniki.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
