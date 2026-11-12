"""Zapisuje wykresy przebiegu symulacji w pliku PNG."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def save_plot(result, path):
    s = result.series
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    panels = [
        ("Przepływy", "t/h", [("feed_tph", "Nadawa"), ("product_tph", "Produkt"), ("recycle_tph", "Powrót")]),
        ("Materiał w młynie", "t", [("chamber1_t", "Komora 1"), ("chamber2_t", "Komora 2")]),
        ("Blaine z D32 (szac.)", "cm²/g", [("blaine_cm2_g", "Blaine")]),
        ("Pobór mocy", "kW", [("power_kw", "Młyn + separator")]),
    ]
    for ax, (title, unit, columns) in zip(axes.flat, panels):
        for key, label in columns:
            ax.plot(s["time_min"], s[key], label=label)
        ax.set(title=title, xlabel="Czas [min]", ylabel=unit)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle(f"Nastawy końcowe: nadawa {s['feed_tph'][-1]:g} t/h"
                 f" · separator {s['separator_rpm'][-1]:g} obr/min"
                 f" · opór {s['hardness'][-1]:g}")
    fig.savefig(path, dpi=140)
    plt.close(fig)

def save_hardness_comparison_plots(result_custom_hardness, result_constant_hardness, path):
    s_custom = result_custom_hardness.series
    s_constant = result_constant_hardness.series
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    panels = [
            ("Opór Mielenia", "jedn.", "hardness"),
            ("Produkcja", "t/h", "product_tph"),
            ("Blaine z D32 (szac.)", "cm²/g", "blaine_cm2_g"),
            ("Pobór mocy", "kW", "power_kw"),
        ]
    for ax, (title, unit, columns) in zip(axes.flat, panels):
        ax.plot(s_custom["time_min"], s_custom[columns], label="opór zmienny")
        ax.plot(s_constant["time_min"], s_constant[columns], label="opór stały")
        ax.set(title=title, xlabel="Czas [min]", ylabel=unit)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle("Porównanie przebiegu symulacji dla oporu zmiennego i stałego")
    fig.savefig(path, dpi=140)
    plt.close(fig)