"""Agronomic knowledge base for Punjab wheat and rice.

These are MODEL PARAMETERS (like weights in a model), not observations. Every
value below must be traceable to a published source - see `SOURCES`. Before the
final submission, check each number against the cited document and adjust.

Stages are defined by days since sowing (wheat) or transplanting (rice).
`sensitivity[event]` = fraction of yield lost if that event happens at that stage.
"""

SOURCES = {
    "pau_rabi": "PAU Package of Practices for Crops of Punjab - Rabi (Punjab Agricultural University, Ludhiana)",
    "pau_kharif": "PAU Package of Practices for Crops of Punjab - Kharif (Punjab Agricultural University, Ludhiana)",
    "imd_rain": "IMD rainfall intensity classification (India Meteorological Department)",
    "msp": "CACP / Govt. of India Minimum Support Price notification",
}

# Weather event definitions. `per_crop` lets a threshold differ by crop.
EVENTS = {
    "rain": {
        "label": "Rain (any, >= 2.5 mm/day)",
        "variable": "precipitation", "agg": "sum", "op": ">=", "threshold": 2.5,
        "source": "imd_rain",
    },
    "heavy_rain": {
        "label": "Heavy rain (>= 20 mm/day)",
        "variable": "precipitation", "agg": "sum", "op": ">=", "threshold": 20.0,
        "source": "imd_rain",
    },
    "strong_wind": {
        "label": "Strong wind gusts (>= 40 km/h) - lodging risk",
        "variable": "wind_gusts_10m", "agg": "max", "op": ">=", "threshold": 40.0,
        "source": "pau_rabi",
    },
    "heat_stress": {
        "label": "Heat stress (max temp above crop limit)",
        "variable": "temperature_2m", "agg": "max", "op": ">=",
        "per_crop": {"wheat": 34.0, "rice": 35.0},
        "source": "pau_rabi",
    },
    "frost": {
        "label": "Frost / cold injury (min temp <= 2 C)",
        "variable": "temperature_2m", "agg": "min", "op": "<=", "threshold": 2.0,
        "source": "pau_rabi",
    },
}

CROPS = {
    "wheat": {
        "label": "Wheat",
        "season": "rabi",
        "date_label": "sowing date",
        "default_yield_q_per_acre": 19.0,   # Punjab state average (approx.) - verify
        "msp_rs_per_q": 2585,               # MSP RMS 2026-27 - verify against latest CACP notice
        "agmarknet_commodity": "Wheat",
        "source": "pau_rabi",
        "stages": [
            # (name, start_day, end_day, sensitivity per event)
            ("establishment", 0, 25, {"heavy_rain": 0.05, "frost": 0.02}),
            ("tillering", 25, 60, {"heavy_rain": 0.03, "frost": 0.03}),
            ("jointing_booting", 60, 90, {"heavy_rain": 0.04, "strong_wind": 0.03, "frost": 0.08, "heat_stress": 0.03}),
            ("heading_flowering", 90, 110, {"heavy_rain": 0.08, "strong_wind": 0.08, "frost": 0.15, "heat_stress": 0.10}),
            ("grain_filling", 110, 135, {"heavy_rain": 0.12, "strong_wind": 0.15, "frost": 0.05, "heat_stress": 0.12}),
            ("maturity_harvest", 135, 165, {"heavy_rain": 0.15, "strong_wind": 0.12}),
        ],
    },
    "rice": {
        "label": "Rice (Paddy)",
        "season": "kharif",
        "date_label": "transplanting date",
        "default_yield_q_per_acre": 27.0,   # Punjab state average paddy (approx.) - verify
        "msp_rs_per_q": 2369,               # MSP KMS 2025-26 (common paddy) - verify against latest CACP notice
        "agmarknet_commodity": "Paddy(Dhan)(Common)",
        "source": "pau_kharif",
        "stages": [
            ("establishment", 0, 20, {"heavy_rain": 0.03, "heat_stress": 0.02}),
            ("tillering", 20, 50, {"heavy_rain": 0.02, "heat_stress": 0.02}),
            ("panicle_initiation", 50, 75, {"heavy_rain": 0.03, "heat_stress": 0.05, "strong_wind": 0.02}),
            ("flowering", 75, 95, {"heavy_rain": 0.08, "heat_stress": 0.15, "strong_wind": 0.06}),
            ("grain_filling", 95, 120, {"heavy_rain": 0.08, "strong_wind": 0.12, "heat_stress": 0.05}),
            ("maturity_harvest", 120, 150, {"heavy_rain": 0.12, "strong_wind": 0.12}),
        ],
    },
}

# Farm operation costs in Rs per acre. Farmer can override each one in the UI.
DEFAULT_COSTS = {
    "spray_rs_per_acre": 800,          # chemical + labour for one spray
    "irrigation_rs_per_acre": 300,     # power/diesel + labour for one irrigation
    "early_harvest_premium_rs_per_acre": 1500,  # extra combine charge / quality penalty for harvesting early
    "drainage_rs_per_acre": 200,       # labour to open drainage channels
}

# Protective actions. `effectiveness` = share of the expected loss the action avoids.
# kind="protect": avoids crop loss from `events`.
# kind="save_input": avoids wasting an input (spray/irrigation) if `events` happens.
ACTIONS = {
    "postpone_spray": {
        "label": "Postpone pesticide/fertilizer spray until after the rain",
        "kind": "save_input", "events": ["rain"], "window_days": 2,
        "input_cost_key": "spray_rs_per_acre", "action_cost": 0,
        "crops": ["wheat", "rice"], "stages": None,
    },
    "skip_irrigation": {
        "label": "Skip the next planned irrigation - rain expected",
        "kind": "save_input", "events": ["rain"], "window_days": 3,
        "input_cost_key": "irrigation_rs_per_acre", "action_cost": 0,
        "crops": ["wheat"], "stages": None,
    },
    "early_harvest": {
        "label": "Harvest early, before the weather event",
        "kind": "protect", "events": ["heavy_rain", "strong_wind"], "window_days": 5,
        "effectiveness": 0.9, "cost_key": "early_harvest_premium_rs_per_acre",
        "crops": ["wheat", "rice"], "stages": ["maturity_harvest"],
    },
    "drain_field": {
        "label": "Open drainage channels to avoid waterlogging",
        "kind": "protect", "events": ["heavy_rain"], "window_days": 5,
        "effectiveness": 0.3, "cost_key": "drainage_rs_per_acre",
        "crops": ["wheat"], "stages": None,
    },
    "light_irrigation_frost": {
        "label": "Give a light irrigation to protect against frost",
        "kind": "protect", "events": ["frost"], "window_days": 3,
        "effectiveness": 0.5, "cost_key": "irrigation_rs_per_acre",
        "crops": ["wheat"], "stages": None,
    },
    "light_irrigation_heat": {
        "label": "Give a light irrigation to reduce terminal heat stress",
        "kind": "protect", "events": ["heat_stress"], "window_days": 5,
        "effectiveness": 0.3, "cost_key": "irrigation_rs_per_acre",
        "crops": ["wheat"], "stages": ["heading_flowering", "grain_filling"],
    },
    "maintain_standing_water": {
        "label": "Keep 5 cm standing water in the field during the heat spell",
        "kind": "protect", "events": ["heat_stress"], "window_days": 5,
        "effectiveness": 0.3, "cost_key": "irrigation_rs_per_acre",
        "crops": ["rice"], "stages": ["panicle_initiation", "flowering"],
    },
}
