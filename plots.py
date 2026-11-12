"""Zapisuje wykresy przebiegu symulacji w pliku PNG."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def save_plot(result, path):
    s = result.series
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    panels = [
        ("Przepływy", "t/h", [("feed_tph", "Nadawa"), ("product_tph", "Produkt"), ("recycle_tph", "Powrót")]),
        ("Materiał w komorach", "t", [("chamber1_t", "Komora 1"), ("chamber2_t", "Komora 2")]),
        ("Blaine z D32 (szac.)", "cm²/g", [("blaine_cm2_g", "Blaine")]),
        ("Pobór mocy", "kW", [("power_kw", "Młyn + separator")]),
    ]
    for ax, (title, unit, columns) in zip(axes.flat, panels):
        for key, label in columns:
            ax.plot(s["time_min"], s[key], label=label)
        if s['terminated'][-1]:
            ax.axvline(s['time_min'][-1], color="#b52828", ls=":", label="Zamielenie")
        ax.set(title=title, xlabel="Czas [min]", ylabel=unit)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle(f"Nastawy końcowe: nadawa {s['feed_tph'][-1]:g} t/h"
                 f" · separator {s['separator_rpm'][-1]:g} obr/min"
                 f" · opór {s['hardness'][-1]:g} · gazy {s['gas_flow_nm3_h'][-1]:.0f} Nm³/h")
    fig.savefig(path, dpi=140)
    plt.close(fig)
