# Digital-Twin-Cement-Mill-Simulator-for-Reinforcement-Learning-Research

Symulator opisuje dwukomorowy młyn z separatorem i powrotem materiału.
Śledzi masy w 14 klasach wielkości ziaren, w pięciu obszarach mieszania.
Z nich oblicza przepływy, uziarnienie produktu, powierzchnię i moc.

## Co podajemy

- `feed_tph` — świeża nadawa [t/h], zakres 0–200.
- `separator_rpm` — obroty separatora [obr/min], zakres 500–1800.
- `hardness` — względny opór rozdrabniania, zakres 0,5–2; 1 oznacza wartość bazową.
- `dt_min` — o ile minut przesunąć proces; musi być dodatnie.


## Co dostajemy

`reset()`, `step()`, `observe()` i `set_inputs()` zwracają słownik z bieżącymi wartościami:

| Klucz | Znaczenie |
|---|---|
| `time_min` | Czas procesu [min] |
| `feed_tph`, `separator_rpm`, `hardness` | Zastosowane nastawy |
| `product_tph` | Strumień produktu [t/h] |
| `recycle_tph` | Powrót z separatora [t/h] |
| `transfer_tph` | Transfer z pierwszej komory do drugiej [t/h] |
| `discharge_tph` | Odpływ z drugiej komory na separator [t/h] |
| `chamber1_t`, `chamber2_t` | Masy materiału w komorach [t] |
| `cstr1_t` … `cstr5_t` | Masy w poszczególnych obszarach mieszania [t] |
| `product_d32_um` | Średnica Sautera D32 produktu [µm] |
| `blaine_cm2_g` | Powierzchnia oszacowana z D32 [cm²/g] |
| `residue45_pct` | Udział produktu powyżej 45 µm [%] |
| `mill_power_kw`, `separator_power_kw` | Moce młyna i separatora [kW] |
| `power_kw` | Łączna moc [kW] |
| `specific_energy_kwh_t` | Chwilowy iloraz mocy i wydajności [kWh/t] |
| `product_total_t`, `feed_total_t` | Produkt i świeża nadawa od początku [t] |
| `energy_kwh` | Energia zużyta od początku [kWh] |
| `mass_error_t` | Błąd bilansu masy [t], powinien być bliski zeru |


