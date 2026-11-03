"""Wyświetla formularz, symulację krokową i odtwarzanie wyników."""
import math
import time
import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, Rectangle
from parameters import DEFAULT_INPUTS, Inputs, Scenario
from simulation import MillSimulation


COLORS = dict(feed="#526778", transfer="#168d98", discharge="#168d98",
              product="#258354", recycle="#cc7930", text="#243747")


class ParameterWindow:
    """Pobiera i sprawdza parametry symulacji w formularzu."""

    def __init__(self, feed=None, rpm=None, hardness=1, minutes=120):
        self.root = tk.Tk()
        self.root.title("Młyn cementu — parametry")
        self.root.resizable(False, False)
        self.selection = None
        self.initial = (DEFAULT_INPUTS.feed_tph if feed is None else feed,
                        DEFAULT_INPUTS.separator_rpm if rpm is None else rpm, hardness, minutes)
        body = ttk.Frame(self.root, padding=24)
        body.grid()
        ttk.Label(body, text="Parametry symulacji", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(body, text="Zmień wartości lub kliknij Uruchom, aby użyć podanych nastaw.").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 18))
        self.values, self.entries = [], []
        fields = (("Nadawa", "t/h · 0–200"), ("Obroty separatora", "obr/min · 500–1800"),
                  ("Opór rozdrabniania", "0,5–2 · 1 = bazowy"), ("Czas procesu", "min · co najmniej 1"))
        for row, ((label, unit), value) in enumerate(zip(fields, self.initial), start=2):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=7)
            variable = tk.StringVar(value=f"{value:g}")
            entry = ttk.Entry(body, textvariable=variable, width=14)
            entry.grid(row=row, column=1, padx=(0, 12), pady=7)
            ttk.Label(body, text=unit).grid(row=row, column=2, sticky="w", pady=7)
            self.values.append(variable)
            self.entries.append(entry)
        self.error = tk.StringVar()
        ttk.Label(body, textvariable=self.error, foreground="#b52828", wraplength=440).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(8, 12))
        buttons = ttk.Frame(body)
        buttons.grid(row=7, column=0, columnspan=3, sticky="ew")
        ttk.Button(buttons, text="Przywróć domyślne", command=self.defaults).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Anuluj", command=self.root.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        self.run_button = ttk.Button(buttons, text="Uruchom", command=self.submit)
        self.run_button.pack(side=tk.RIGHT)
        self.root.bind("<Return>", lambda event: self.submit())
        self.root.bind("<Escape>", lambda event: self.root.destroy())
        self.entries[0].focus_set()
        self.entries[0].selection_range(0, tk.END)

    def defaults(self):
        self.initial = (DEFAULT_INPUTS.feed_tph, DEFAULT_INPUTS.separator_rpm, DEFAULT_INPUTS.hardness, 120)
        for variable, value in zip(self.values, self.initial):
            variable.set(f"{value:g}")
        self.error.set("")

    def submit(self):
        try:
            values = tuple(float(variable.get().strip().replace(",", "."))
                           if variable.get().strip() else default
                           for variable, default in zip(self.values, self.initial))
        except ValueError:
            self.error.set("Wpisz liczby. Możesz użyć kropki lub przecinka dziesiętnego.")
            return
        try:
            inputs = Inputs(*values[:3])
            Scenario(before=inputs, after=inputs, duration_min=values[3],
                     step_min=0, start_empty=True)
        except ValueError as error:
            message = str(error).replace("feed_tph", "Nadawa").replace(
                "separator_rpm", "Obroty separatora").replace("hardness", "Opór rozdrabniania")
            self.error.set(message)
            return
        self.selection = values
        self.root.destroy()


def ask_parameters(feed=None, rpm=None, hardness=1, minutes=120):
    window = ParameterWindow(feed, rpm, hardness, minutes)
    window.root.mainloop()
    return window.selection


class ProcessFigure:
    """Rysuje schemat procesu, bieżące wartości i wykresy."""

    def __init__(self, result, *, end_min=None, live=False):
        self.result = result
        self.s = {key: np.asarray(value) for key, value in result.series.items()}
        self.times = self.s["time_min"]
        self.end_min = float(self.times[-1] if end_min is None else end_min)
        self.figure = Figure(figsize=(12, 8), dpi=100, facecolor="#f4f7fa")
        self.figure.text(.05, .965, "Młyn cementu · podgląd procesu",
                         fontsize=19, weight="bold", color=COLORS["text"])
        self.caption = self.figure.text(.05, .927, "", fontsize=10, color="#526778")
        self.scheme = self.figure.add_axes([.025, .605, .745, .29])
        self.scheme.set(xlim=(0, 12), ylim=(0, 4))
        self.scheme.axis("off")
        self.level_scale = max(1., float(max(self.s["chamber1_t"].max(),
                                             self.s["chamber2_t"].max()) * 1.15))
        self.fills, self.mass_labels = [], []
        for x, title in ((2., "Komora 1"), (5.1, "Komora 2")):
            self.scheme.add_patch(Rectangle((x, 1.3), 1.7, 1.8,
                                            facecolor="#e7eef3", edgecolor="none"))
            fill = Rectangle((x + .06, 1.36), 1.58, 0,
                             facecolor="#77bbc5", edgecolor="none")
            self.scheme.add_patch(fill)
            self.scheme.add_patch(Rectangle((x, 1.3), 1.7, 1.8,
                                            fill=False, edgecolor="#40576a", lw=1.6))
            self.scheme.text(x + .85, 3.35, title, ha="center", weight="bold",
                             color=COLORS["text"], fontsize=11)
            self.fills.append(fill)
            for position in ([.5] if x == 2. else [1/3, 2/3]):
                self.scheme.plot([x+1.7*position]*2, [1.3, 3.1],
                                 color='#40576a', lw=.8, ls='--')
            self.mass_labels.append(self.scheme.text(x + .85, 2.15, "",
                                    ha="center", va="center", weight="bold", fontsize=13))
        self.scheme.text(4.4, 3.35, "Przepona", ha="center", fontsize=9, color="#526778")
        self.scheme.add_patch(Rectangle((4.27, 1.75), .15, .9,
                                        facecolor="#91a2b0", hatch="///"))
        self.scheme.add_patch(Rectangle((8.1, 1.5), 1.45, 1.5,
                                        facecolor="#e7eef3", edgecolor="#40576a", lw=1.6))
        self.scheme.text(8.825, 2.25, "Separator", ha="center", va="center",
                         weight="bold", color=COLORS["text"], fontsize=11)
        self.flow_labels, self.paths, self.dots = {}, {}, {}
        self._flow("feed_tph", "Nadawa", [(0.1, 2.2), (2., 2.2)], (.95, 2.8), COLORS["feed"])
        self._flow("transfer_tph", "Transfer", [(3.7, 2.2), (5.1, 2.2)], (4.4, 1.2), COLORS["transfer"])
        self._flow("discharge_tph", "Odpływ", [(6.8, 2.2), (8.1, 2.2)], (7.45, 2.8), COLORS["discharge"])
        self._flow("product_tph", "Produkt", [(9.55, 2.2), (11.8, 2.2)], (10.75, 2.8), COLORS["product"])
        self._flow("recycle_tph", "Powrót", [(8.825, 1.5), (8.825, .6),
                   (2.85, .6), (2.85, 1.3)], (5.8, .05), COLORS["recycle"])
        self.level_note = self.figure.text(.05, .573, f"Skala masy komór: 0–{self.level_scale:.1f} t. "
                         "Poziom i znaczniki przepływu są umowne. Linie przerywane: obszary modelu.",
                         fontsize=8, color="#657786")
        self.metrics = self.figure.add_axes([.79, .62, .19, .28])
        self.metrics.axis("off")
        self.metrics.text(0, 1, "W WYBRANEJ CHWILI", weight="bold", fontsize=10,
                          color="#526778", va="top")
        self.metric_text = []
        for y, label in ((.78, "Wydajność"), (.57, "Blaine z D32 (szac.)"),
                         (.36, "Moc"), (.15, "Wyprodukowano")):
            self.metrics.text(0, y + .045, label, fontsize=9, color="#657786")
            self.metric_text.append(self.metrics.text(0, y - .045, "",
                                    fontsize=16, weight="bold", color=COLORS["text"]))
        panels = [
            ("Przepływy", "t/h", [("feed_tph", "Nadawa", COLORS["feed"]),
              ("product_tph", "Produkt", COLORS["product"]), ("recycle_tph", "Powrót", COLORS["recycle"])]),
            ("Materiał w młynie", "t", [("chamber1_t", "Komora 1", "#168d98"),
              ("chamber2_t", "Komora 2", "#556eac")]),
            ("Blaine z D32 (szac.)", "cm²/g", [("blaine_cm2_g", "Blaine", "#556eac")]),
            ("Pobór mocy", "kW", [("power_kw", "Młyn + separator", "#168d98")]),
        ]
        self.traces, self.cursors, self.plot_axes = [], [], []
        for panel, (x, y) in zip(panels, ((.07, .345), (.57, .345), (.07, .075), (.57, .075))):
            title, unit, columns = panel
            ax = self.figure.add_axes([x, y, .39, .17], facecolor="white")
            ax.set(title=title, xlabel="Czas [min]", ylabel=unit,
                   xlim=(0, max(1., self.end_min)))
            self.plot_axes.append((ax, [key for key, _, _ in columns]))
            finite = np.concatenate([self.s[key][np.isfinite(self.s[key])] for key, _, _ in columns])
            high = max(1., float(finite.max()) * 1.12) if finite.size else 1.
            ax.set_ylim(0, high)
            ax.tick_params(labelsize=8)
            ax.title.set_fontsize(10)
            ax.xaxis.label.set_size(8)
            ax.yaxis.label.set_size(8)
            ax.grid(alpha=.15)
            for key, label, color in columns:
                line, = ax.plot([], [], color=color, label=label, lw=1.8)
                self.traces.append((line, key))
            ax.legend(loc="upper right", fontsize=7, framealpha=.85)
            self.cursors.append(ax.axvline(0, color="#718493", lw=1, ls="--"))
        self.footer = self.figure.text(.05, .008, '', fontsize=8, color="#657786")
        self.footer.set_text("Symulacja krokowa" if live else "Odtwarzanie obliczonego przebiegu")
        self.index = -1
        self.update(0)

    def set_result(self, result):
        """Aktualizuje historię i skale wykresów dla nowego wyniku."""
        self.result = result
        self.s = {key: np.asarray(value) for key, value in result.series.items()}
        self.times = self.s['time_min']
        self.level_scale = max(1., float(max(self.s['chamber1_t'].max(),
                                             self.s['chamber2_t'].max()) * 1.15))
        self.level_note.set_text(f"Skala masy komór: 0–{self.level_scale:.1f} t. "
                                 "Poziom i znaczniki przepływu są umowne. Linie przerywane: obszary modelu.")
        for ax, keys in self.plot_axes:
            finite = np.concatenate([self.s[key][np.isfinite(self.s[key])] for key in keys])
            high = max(1., float(finite.max()) * 1.12) if finite.size else 1.
            ax.set_ylim(0, high)
        self.index = -1

    def _flow(self, key, label, points, label_position, color):
        points = np.asarray(points, dtype=float)
        self.paths[key] = points
        for index, (start, end) in enumerate(zip(points[:-1], points[1:])):
            arrow = FancyArrowPatch(start, end, arrowstyle="-|>" if index == len(points) - 2 else "-",
                                    mutation_scale=13, color=color, lw=2)
            self.scheme.add_patch(arrow)
        self.flow_labels[key] = self.scheme.text(*label_position, "", ha="center",
                                                fontsize=9, color=color)
        dot, = self.scheme.plot([], [], "o", color=color, ms=5)
        self.dots[key] = dot
        self.flow_labels[key].flow_name = label

    def update(self, minute, phase=0):
        """Wyświetla próbkę wyniku najbliższą wybranemu czasowi."""
        minute = float(np.clip(minute, self.times[0], self.times[-1]))
        index = int(np.searchsorted(self.times, minute))
        index = min(index, len(self.times) - 1)
        if index and abs(self.times[index - 1] - minute) < abs(self.times[index] - minute):
            index -= 1
        if index != self.index:
            self.index = index
            at = lambda key: float(self.s[key][index])
            self.caption.set_text(f"Czas: {self.times[index]:.1f} / {self.end_min:g} min   ·   "
                                  f"Nadawa: {at('feed_tph'):g} t/h   ·   "
                                  f"Separator: {at('separator_rpm'):g} obr/min   ·   Opór: {at('hardness'):g}")
            for fill, label, key in zip(self.fills, self.mass_labels, ("chamber1_t", "chamber2_t")):
                fill.set_height(1.68 * max(0., at(key)) / self.level_scale)
                label.set_text(f"{at(key):.2f} t")
            for key, label in self.flow_labels.items():
                label.set_text(f"{label.flow_name}\n{at(key):.1f} t/h")
            blaine = at("blaine_cm2_g")
            values = (f"{at('product_tph'):.2f} t/h",
                      f"{blaine:.0f} cm²/g" if math.isfinite(blaine) else "Brak produktu",
                      f"{at('power_kw'):.0f} kW", f"{at('product_total_t'):.2f} t")
            for label, value in zip(self.metric_text, values):
                label.set_text(value)
            for line, key in self.traces:
                line.set_data(self.times[:index + 1], self.s[key][:index + 1])
            for cursor in self.cursors:
                cursor.set_xdata([self.times[index], self.times[index]])
        for key, dot in self.dots.items():
            flow = max(0., float(self.s[key][index]))
            dot.set_visible(flow > 1e-8)
            points = self.paths[key]
            lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
            distance = (phase % 1) * lengths.sum()
            segment = min(int(np.searchsorted(np.cumsum(lengths), distance)), len(lengths) - 1)
            previous = lengths[:segment].sum()
            point = points[segment] + (points[segment + 1] - points[segment]) * ((distance - previous) / lengths[segment])
            dot.set_data([point[0]], [point[1]])


class LiveWindow:
    """Obsługuje sterowanie krokami symulacji i zmianę nastaw w oknie."""

    def __init__(self, inputs, minutes=120):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        Scenario(before=inputs, after=inputs, duration_min=minutes, step_min=0)
        self.simulation = MillSimulation()
        self.initial_inputs = inputs
        self.rows = [self.simulation.reset(inputs)]
        self.result = self.simulation.result(self.rows)
        self.end = minutes
        self.step_min = 1.
        self.playing = False
        self.timer = None
        self.phase = 0.
        self.root = tk.Tk()
        self.root.title('Młyn cementu — symulacja krokowa')
        self.root.geometry('1200x950')
        self.root.minsize(960, 800)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.view = ProcessFigure(self.result, end_min=minutes, live=True)
        controls = ttk.Frame(self.root, padding=(12, 8))
        controls.pack(side=tk.BOTTOM, fill=tk.X)
        settings = ttk.Frame(controls)
        settings.pack(fill=tk.X)
        self.values = []
        for column, (label, value) in enumerate((('Nadawa [t/h]', inputs.feed_tph),
                ('Separator [obr/min]', inputs.separator_rpm), ('Opór [0,5–2]', inputs.hardness),
                ('Krok [min]', self.step_min))):
            ttk.Label(settings, text=label).grid(row=0, column=column, sticky='w', padx=(0, 12))
            variable = tk.StringVar(value=f'{value:g}')
            ttk.Entry(settings, textvariable=variable, width=16).grid(
                row=1, column=column, sticky='ew', padx=(0, 12))
            self.values.append(variable)
        self.apply_button = ttk.Button(settings, text='Zastosuj nastawy', command=self.apply_settings)
        self.apply_button.grid(row=1, column=4, padx=(0, 12))
        ttk.Label(controls, text='Zmiany obowiązują po Zastosuj nastawy lub Krok. '
                  'Po zamknięciu okna przebieg zostanie zapisany.').pack(anchor='w', pady=(5, 6))
        buttons = ttk.Frame(controls)
        buttons.pack(fill=tk.X)
        self.step_button = ttk.Button(buttons, text='Krok', command=self.step_once)
        self.step_button.pack(side=tk.LEFT)
        self.play_button = ttk.Button(buttons, text='Start', command=self.toggle)
        self.play_button.pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text='Od początku', command=self.reset).pack(side=tk.LEFT)
        self.clock = ttk.Label(buttons)
        self.clock.pack(side=tk.RIGHT)
        self.error = tk.StringVar()
        ttk.Label(controls, textvariable=self.error, foreground='#b52828').pack(anchor='w', pady=(4, 0))
        self.canvas = FigureCanvasTkAgg(self.view.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.render()

    def apply_settings(self):
        try:
            feed, rpm, hardness, duration = (float(value.get().strip().replace(',', '.'))
                                             for value in self.values)
            inputs = Inputs(feed, rpm, hardness)
            if not math.isfinite(duration) or not 0.01 <= duration <= 60:
                raise ValueError('Krok musi wynosić od 0,01 do 60 minut.')
        except ValueError as error:
            self.pause()
            self.error.set(str(error).replace('feed_tph', 'Nadawa').replace(
                'separator_rpm', 'Obroty separatora').replace('hardness', 'Opór rozdrabniania'))
            return False
        self.rows[-1] = self.simulation.set_inputs(inputs)
        self.step_min = duration
        self.error.set('')
        self.render()
        return True

    def step_once(self):
        self.pause()
        if self.simulation.time_min < self.end and self.apply_settings():
            self.advance()

    def advance(self):
        remaining = self.end - self.simulation.time_min
        if remaining <= 0:
            self.pause()
            return
        try:
            self.rows.append(self.simulation.step(min(self.step_min, remaining)))
        except (ValueError, RuntimeError) as error:
            self.pause()
            self.error.set(str(error))
            return
        self.phase += .2
        if self.simulation.time_min >= self.end:
            self.pause()
        self.render()

    def toggle(self):
        if self.playing:
            self.pause()
        elif self.simulation.time_min < self.end and self.apply_settings():
            self.playing = True
            self.play_button.configure(text='Pauza')
            self.timer = self.root.after(200, self.tick)

    def tick(self):
        self.timer = None
        if self.playing:
            self.advance()
            if self.playing:
                self.timer = self.root.after(200, self.tick)

    def pause(self):
        self.playing = False
        self.play_button.configure(text='Start')
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None

    def reset(self):
        self.pause()
        self.rows = [self.simulation.reset(self.initial_inputs)]
        for variable, value in zip(self.values, (self.initial_inputs.feed_tph,
                self.initial_inputs.separator_rpm, self.initial_inputs.hardness, 1)):
            variable.set(f'{value:g}')
        self.step_min = 1.
        self.phase = 0.
        self.error.set('')
        self.render()

    def render(self):
        self.result = self.simulation.result(self.rows)
        self.view.set_result(self.result)
        self.view.update(self.simulation.time_min, self.phase)
        self.clock.configure(text=f'{self.simulation.time_min:.2f} / {self.end:g} min')
        state = 'disabled' if self.simulation.time_min >= self.end else 'normal'
        for button in (self.step_button, self.play_button, self.apply_button):
            button.configure(state=state)
        self.canvas.draw_idle()

    def close(self):
        self.pause()
        for callback in self.root.tk.call('after', 'info'):
            self.root.tk.call('after', 'cancel', callback)
        self.root.destroy()


def show_live(inputs, minutes=120):
    window = LiveWindow(inputs, minutes=minutes)
    window.root.mainloop()
    return window.result


class PlaybackWindow:
    def __init__(self, result):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.root = tk.Tk()
        self.root.title("Symulator młyna cementu")
        self.root.geometry("1200x900")
        self.root.minsize(960, 760)
        self.view = ProcessFigure(result)
        self.end = float(self.view.times[-1])
        self.minute = 0.
        self.playing = False
        self.timer = None
        self.last_tick = time.perf_counter()
        self.phase = 0.
        self._setting_slider = False
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        controls = ttk.Frame(self.root, padding=(12, 8))
        controls.pack(side=tk.BOTTOM, fill=tk.X)
        self.play_button = ttk.Button(controls, text="▶ Odtwórz", command=self.toggle)
        self.play_button.pack(side=tk.LEFT)
        ttk.Button(controls, text="↺ Od początku", command=self.reset).pack(side=tk.LEFT, padx=8)
        ttk.Label(controls, text="Tempo:").pack(side=tk.LEFT)
        self.speed = tk.StringVar(value="120")
        ttk.Combobox(controls, textvariable=self.speed, width=5, state="readonly",
                     values=("1", "10", "30", "60", "120", "600")).pack(side=tk.LEFT, padx=4)
        ttk.Label(controls, text="×").pack(side=tk.LEFT)
        self.clock = ttk.Label(controls, text=f"0.0 / {self.end:g} min", width=20)
        self.clock.pack(side=tk.RIGHT)
        self.slider = ttk.Scale(controls, from_=0, to=self.end, command=self.seek)
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)
        self.canvas = FigureCanvasTkAgg(self.view.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.root.bind("<space>", lambda event: self.toggle())
        self.canvas.draw()

    def toggle(self):
        if self.playing:
            self.pause()
            return
        if self.minute >= self.end:
            self.minute = 0.
        self.playing = True
        self.play_button.configure(text="⏸ Pauza")
        self.last_tick = time.perf_counter()
        self.tick()

    def pause(self):
        self.playing = False
        self.play_button.configure(text="▶ Odtwórz")
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None

    def reset(self):
        self.pause()
        self.minute, self.phase = 0., 0.
        self.render()

    def seek(self, value):
        if self._setting_slider:
            return
        self.pause()
        self.minute = float(value)
        self.render()

    def render(self):
        self.view.update(self.minute, self.phase)
        self.clock.configure(text=f"{self.view.times[self.view.index]:.1f} / {self.end:g} min")
        self._setting_slider = True
        try:
            self.slider.set(self.minute)
        finally:
            self._setting_slider = False
        self.canvas.draw_idle()

    def tick(self):
        self.timer = None
        if not self.playing:
            return
        now = time.perf_counter()
        elapsed = now - self.last_tick
        self.last_tick = now
        self.minute = min(self.end, self.minute + elapsed * float(self.speed.get()) / 60)
        self.phase += elapsed * .6
        self.render()
        if self.minute >= self.end:
            self.pause()
        else:
            self.timer = self.root.after(80, self.tick)

    def close(self):
        self.pause()
        self.root.destroy()


def show(result):
    window = PlaybackWindow(result)
    window.root.mainloop()
