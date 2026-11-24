"""Flask front end for the BJT DC bias calculator."""

import math

from flask import Flask, render_template, request

from dc_bias import solve, solve_fixed, solve_emitter
from spice_engine import (
    EngineUnavailable,
    MODEL_NAME,
    SpiceError,
    run_analysis,
)

app = Flask(__name__)

UNITS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}

MODES = ("divider", "fixed", "emitter")
MODE_FIELDS = {
    "divider": ("r1", "r2", "re"),
    "fixed": ("rb",),
    "emitter": ("rb", "re"),
}
MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}
MODE_RESISTOR_ORDER = {
    "divider": ("r1", "r2", "rc", "re"),
    "fixed": ("rb", "rc"),
    "emitter": ("rb", "rc", "re"),
}
SOLVERS = {
    "divider": solve,
    "fixed": solve_fixed,
    "emitter": solve_emitter,
}

COMMON_FIELDS = ("vcc", "rc", "beta", "vbe")
FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "rb": "RB",
    "beta": "β",
    "vbe": "VBE",
}
RESISTOR_LABELS = {
    "r1": "R1 (VCC → Base)",
    "r2": "R2 (Base → GND)",
    "rc": "RC (VCC → Collector)",
    "re": "RE (Emitter → GND)",
    "rb": "RB (VCC → Base)",
}

DEFAULT_VALUES = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rb": "1",
    "beta": "100",
    "vbe": "0.70",
}

DEFAULT_UNITS = {
    "r1_unit": "kohm",
    "r2_unit": "kohm",
    "rc_unit": "kohm",
    "re_unit": "kohm",
    "rb_unit": "mohm",
}

UNIT_CHOICES = (
    ("ohm", "Ω"),
    ("kohm", "kΩ"),
    ("mohm", "MΩ"),
)

# Lab 04 — SPICE analysis selection and fixture inputs.
ANALYSES = ("bias", "dc", "ac", "tran")
ANALYSIS_LABELS = {
    "bias": "Analytical DC Bias (Lab 03)",
    "dc": "SPICE · DC Operating Point",
    "ac": "SPICE · AC Frequency Response",
    "tran": "SPICE · Transient Waveform",
}

SPICE_FIELDS = (
    "vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout",
    "source_amp", "source_freq",
)
SPICE_FIELD_LABELS = {
    "vcc": "VCC", "r1": "R1", "r2": "R2", "rc": "RC", "re": "RE",
    "rl": "RL", "cin": "Cin", "cout": "Cout",
    "source_amp": "Source amplitude", "source_freq": "Source frequency",
}
SPICE_UNIT_KEYS = {
    "r1": "r1_unit", "r2": "r2_unit", "rc": "rc_unit", "re": "re_unit",
    "rl": "rl_unit", "cin": "cin_unit", "cout": "cout_unit",
    "source_amp": "amp_unit", "source_freq": "freq_unit",
}
SPICE_UNIT_MAPS = {
    "r1_unit": UNITS, "r2_unit": UNITS, "rc_unit": UNITS,
    "re_unit": UNITS, "rl_unit": UNITS,
    "cin_unit": {"pf": 1e-12, "nf": 1e-9, "uf": 1e-6},
    "cout_unit": {"pf": 1e-12, "nf": 1e-9, "uf": 1e-6},
    "amp_unit": {"mv": 1e-3, "v": 1.0},
    "freq_unit": {"hz": 1.0, "khz": 1e3, "mhz": 1e6},
}
SPICE_UNIT_CHOICES = {
    "r1_unit": (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ")),
    "r2_unit": (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ")),
    "rc_unit": (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ")),
    "re_unit": (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ")),
    "rl_unit": (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ")),
    "cin_unit": (("pf", "pF"), ("nf", "nF"), ("uf", "µF")),
    "cout_unit": (("pf", "pF"), ("nf", "nF"), ("uf", "µF")),
    "amp_unit": (("mv", "mV"), ("v", "V")),
    "freq_unit": (("hz", "Hz"), ("khz", "kHz"), ("mhz", "MHz")),
}
SPICE_RESISTOR_SPECS = (
    ("r1", "R1 (VCC → Base)", "r1_unit"),
    ("r2", "R2 (Base → GND)", "r2_unit"),
    ("rc", "RC (VCC → Collector)", "rc_unit"),
    ("re", "RE (Emitter → GND)", "re_unit"),
    ("rl", "RL (Collector → GND)", "rl_unit"),
)
SPICE_CAP_SPECS = (
    ("cin", "Cin (input coupling)", "cin_unit"),
    ("cout", "Cout (output coupling)", "cout_unit"),
)
SPICE_DEFAULT_VALUES = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "rl": "10", "cin": "10", "cout": "10",
    "source_amp": "10", "source_freq": "1",
}
SPICE_DEFAULT_UNITS = {
    "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm",
    "re_unit": "kohm", "rl_unit": "kohm",
    "cin_unit": "uf", "cout_unit": "uf",
    "amp_unit": "mv", "freq_unit": "khz",
}
SPICE_ENGINE_KEYS = {
    "source_amp": "source_amp_v",
    "source_freq": "source_freq_hz",
}


def parse_spice_form(form) -> tuple[dict[str, float], dict[str, str]]:
    """Convert SPICE fixture inputs to SI values, collecting per-field errors."""
    errors: dict[str, str] = {}
    numbers: dict[str, float] = {}

    for key in SPICE_FIELDS:
        raw = (form.get(key) or "").strip()
        try:
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(raw)
        except ValueError:
            errors[key] = f"กรุณากรอกตัวเลข: {SPICE_FIELD_LABELS[key]}"
            continue
        if value <= 0:
            errors[key] = f"{SPICE_FIELD_LABELS[key]} ต้องมากกว่า 0"
        else:
            numbers[key] = value

    values_si = dict(numbers)
    for key, unit_key in SPICE_UNIT_KEYS.items():
        unit = form.get(unit_key, "")
        if unit not in SPICE_UNIT_MAPS[unit_key]:
            errors[unit_key] = "หน่วยไม่ถูกต้อง"
        elif key in values_si:
            values_si[key] = values_si[key] * SPICE_UNIT_MAPS[unit_key][unit]

    engine_values = {
        SPICE_ENGINE_KEYS.get(key, key): value for key, value in values_si.items()
    }
    return engine_values, errors


def parse_form(form, mode: str) -> tuple[dict[str, float], dict[str, str]]:
    """Convert only the fields this mode uses into SI values, collecting errors."""
    if mode not in MODES:
        return {}, {"mode": "โหมดไม่ถูกต้อง"}

    errors: dict[str, str] = {}
    numbers: dict[str, float] = {}
    required = COMMON_FIELDS + MODE_FIELDS[mode]

    for key in required:
        raw = (form.get(key) or "").strip()
        try:
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(raw)
        except ValueError:
            errors[key] = f"กรุณากรอกตัวเลข: {FIELD_LABELS[key]}"
        else:
            numbers[key] = value

    if "vcc" in numbers and numbers["vcc"] <= 0:
        errors["vcc"] = "VCC ต้องมากกว่า 0 V"

    resistor_keys = ("rc",) + MODE_FIELDS[mode]
    for key in resistor_keys:
        if key in numbers and numbers[key] <= 0:
            errors[key] = "ความต้านทานต้องมากกว่า 0 Ω"

    if "beta" in numbers and numbers["beta"] <= 0:
        errors["beta"] = "β ต้องมากกว่า 0"

    if "vbe" in numbers and "vcc" in numbers:
        if numbers["vbe"] < 0 or numbers["vbe"] >= numbers["vcc"]:
            errors["vbe"] = "VBE ต้องอยู่ระหว่าง 0 ถึง VCC"

    values_si = dict(numbers)
    for key in resistor_keys:
        unit_key = f"{key}_unit"
        unit = form.get(unit_key, "")
        if unit not in UNITS:
            errors[unit_key] = "หน่วยไม่ถูกต้อง"
        elif key in values_si:
            values_si[key] = values_si[key] * UNITS[unit]

    return values_si, errors


def format_current(amps: float) -> str:
    """Format a current with the unit that keeps three significant decades."""
    magnitude = abs(amps)
    if magnitude >= 1e-3:
        return f"{amps * 1e3:.3f} mA"
    if magnitude >= 1e-6:
        return f"{amps * 1e6:.3f} µA"
    return f"{amps * 1e9:.3f} nA"


def build_display(result: dict) -> dict[str, str]:
    """Pre-format every displayed value so the template holds no math."""
    return {
        "vb": f"{result['vb_v']:.3f} V",
        "ve": f"{result['ve_v']:.3f} V",
        "vc": f"{result['vc_v']:.3f} V",
        "vce": f"{result['vce_v']:.3f} V",
        "ic": format_current(result["ic_a"]),
        "ib": format_current(result["ib_a"]),
        "ie": format_current(result["ie_a"]),
    }


def _format_voltage(value) -> str:
    return f"{value:.3f} V" if isinstance(value, (int, float)) else "—"


def _format_frequency(value) -> str:
    return f"{value:g} Hz" if isinstance(value, (int, float)) else "—"


def build_spice_display(spice_result: dict | None) -> dict:
    """Pre-format SPICE values so the template holds no engineering math."""
    if not spice_result:
        return {}
    analysis = spice_result.get("analysis")
    rows: list[tuple[str, str]] = []
    note = ""

    if analysis == "dc":
        op = spice_result.get("op") or {}
        for key, label, formatter in (
            ("vb_v", "VB", _format_voltage),
            ("ve_v", "VE", _format_voltage),
            ("vc_v", "VC", _format_voltage),
            ("vce_v", "VCE", _format_voltage),
            ("ic_a", "IC", format_current),
            ("ib_a", "IB", format_current),
            ("ie_a", "IE", format_current),
        ):
            if key in op:
                rows.append((label, formatter(op[key])))
        note = ("IE uses the ngspice terminal-current sign convention "
                "(negative means current leaving the emitter).")
    elif analysis == "ac":
        ac = spice_result.get("ac") or {}
        marker = ac.get("marker")
        if marker:
            rows = [
                ("Frequency", _format_frequency(marker.get("freq_hz"))),
                ("Gain", f"{marker['gain_db']:.2f} dB" if "gain_db" in marker else "—"),
                ("Phase", f"{marker['phase_deg']:.1f}°" if "phase_deg" in marker else "—"),
            ]
        else:
            note = ac.get("marker_note", "")
    elif analysis == "tran":
        tran = spice_result.get("tran") or {}
        measurement_note = str(tran.get("measurement_note", "") or "")
        peak_label = ("Vout peak (available window)" if measurement_note
                      else "Vout peak (last cycle)")
        rows = [
            ("Vout peak-to-peak", _format_voltage(tran.get("vout_pp_v"))),
            (peak_label, _format_voltage(tran.get("vout_peak_v"))),
            ("Phase relationship", str(tran.get("phase_note", "—"))),
        ]
        note = measurement_note
    return {"rows": rows, "note": note}


def build_provenance_rows(spice_result: dict | None) -> list[tuple[str, str]]:
    if not spice_result:
        return []
    prov = spice_result.get("provenance") or {}
    engine_text = " ".join(
        str(part) for part in (prov.get("engine", ""), prov.get("version", "")) if part
    ).strip()
    fixture = prov.get("fixture") or {}
    fixture_text = ", ".join(f"{key}={value:g}" for key, value in fixture.items())
    return [
        ("Engine / version", engine_text or "—"),
        ("BJT model", str(prov.get("model", MODEL_NAME))),
        ("Model source", str(prov.get("model_path", "—"))),
        ("Analysis", str(prov.get("analysis", spice_result.get("analysis", "—")))),
        ("SPICE rows", str(prov.get("rows", spice_result.get("rows", "—")))),
        ("Fixture (SI)", fixture_text or "—"),
    ]


SVG_WIDTH = 680
SVG_HEIGHT = 260
SVG_LEFT = 64
SVG_RIGHT = 660
SVG_TOP = 24
SVG_BOTTOM = 214


def _svg_x(value: float, x_min: float, x_max: float) -> float:
    span = x_max - x_min or 1.0
    return SVG_LEFT + (value - x_min) / span * (SVG_RIGHT - SVG_LEFT)


def _svg_y(value: float, y_min: float, y_max: float) -> float:
    span = y_max - y_min or 1.0
    return SVG_BOTTOM - (value - y_min) / span * (SVG_BOTTOM - SVG_TOP)


def _svg_polyline(pairs, x_min: float, x_max: float,
                  y_min: float, y_max: float) -> str:
    return " ".join(
        f"{_svg_x(x, x_min, x_max):.1f},{_svg_y(y, y_min, y_max):.1f}"
        for x, y in pairs
    )


def _chart_frame() -> dict:
    return {
        "width": SVG_WIDTH, "height": SVG_HEIGHT,
        "left": SVG_LEFT, "right": SVG_RIGHT,
        "top": SVG_TOP, "bottom": SVG_BOTTOM,
    }


def build_charts(spice_result: dict | None) -> dict[str, dict]:
    """Map parsed SPICE samples to SVG coordinates; no engineering math in Jinja."""
    if not spice_result:
        return {}
    charts: dict[str, dict] = {}

    ac = spice_result.get("ac") or {}
    ac_points = ac.get("points") or []
    if ac_points:
        x_values = [math.log10(p["freq_hz"]) for p in ac_points
                    if p.get("freq_hz", 0) > 0]
        y_values = [p["gain_db"] for p in ac_points if "gain_db" in p]
        if x_values and y_values:
            x_min, x_max = min(x_values), max(x_values)
            y_min, y_max = min(y_values), max(y_values)
            padding = max((y_max - y_min) * 0.05, 1.0)
            y_min -= padding
            y_max += padding
            marker_data = None
            marker = ac.get("marker")
            if marker and marker.get("freq_hz", 0) > 0 and "gain_db" in marker:
                marker_data = {
                    "x": round(_svg_x(math.log10(marker["freq_hz"]), x_min, x_max), 1),
                    "y": round(_svg_y(marker["gain_db"], y_min, y_max), 1),
                    "label": (f"{marker['gain_db']:.2f} dB @ "
                              f"{marker['freq_hz']:g} Hz"),
                }
            charts["ac"] = {
                **_chart_frame(),
                "polyline": _svg_polyline(zip(x_values, y_values),
                                          x_min, x_max, y_min, y_max),
                "x_label": "Frequency (Hz)",
                "y_label": "Gain (dB)",
                "x_ticks": [
                    {
                        "x": round(_svg_x(x_min + fraction * (x_max - x_min),
                                          x_min, x_max), 1),
                        "label": f"{10 ** (x_min + fraction * (x_max - x_min)):.3g}",
                    }
                    for fraction in (0.0, 0.5, 1.0)
                ],
                "y_ticks": [
                    {
                        "y": round(_svg_y(y_min + fraction * (y_max - y_min),
                                          y_min, y_max), 1),
                        "label": f"{y_min + fraction * (y_max - y_min):.1f}",
                    }
                    for fraction in (0.0, 0.5, 1.0)
                ],
                "marker": marker_data,
            }

    tran = spice_result.get("tran") or {}
    tran_points = tran.get("points") or []
    if tran_points:
        times = [p["time_s"] for p in tran_points]
        volts = ([p["vout_v"] for p in tran_points if "vout_v" in p]
                 + [p["vin_v"] for p in tran_points if "vin_v" in p])
        if times and volts:
            x_min, x_max = min(times), max(times)
            y_min, y_max = min(volts), max(volts)
            padding = max((y_max - y_min) * 0.05, 0.01)
            y_min -= padding
            y_max += padding
            charts["tran"] = {
                **_chart_frame(),
                "vin_polyline": _svg_polyline(
                    ((p["time_s"], p["vin_v"]) for p in tran_points),
                    x_min, x_max, y_min, y_max,
                ),
                "vout_polyline": _svg_polyline(
                    ((p["time_s"], p["vout_v"]) for p in tran_points),
                    x_min, x_max, y_min, y_max,
                ),
                "x_label": "Time (ms)",
                "y_label": "Voltage (V)",
                "x_ticks": [
                    {
                        "x": round(_svg_x(x_min + fraction * (x_max - x_min),
                                          x_min, x_max), 1),
                        "label": f"{(x_min + fraction * (x_max - x_min)) * 1e3:.2f}",
                    }
                    for fraction in (0.0, 0.5, 1.0)
                ],
                "y_ticks": [
                    {
                        "y": round(_svg_y(y_min + fraction * (y_max - y_min),
                                          y_min, y_max), 1),
                        "label": f"{y_min + fraction * (y_max - y_min):.3f}",
                    }
                    for fraction in (0.0, 0.5, 1.0)
                ],
            }
    return charts


def render_page(values, units, mode, result=None, errors=None, status=200, *,
                analysis="bias", spice_values=None, spice_units=None,
                spice_result=None, engine=None, charts=None):
    if mode not in MODES:
        mode = "divider"
    if analysis not in ANALYSES:
        analysis = "bias"

    return (
        render_template(
            "index.html",
            values=values,
            units=units,
            unit_choices=UNIT_CHOICES,
            modes=MODES,
            mode=mode,
            mode_labels=MODE_LABELS,
            resistor_specs=[
                (key, RESISTOR_LABELS[key], f"{key}_unit")
                for key in MODE_RESISTOR_ORDER[mode]
            ],
            result=result,
            display=build_display(result) if result else None,
            errors=errors or {},
            analysis=analysis,
            analyses=ANALYSES,
            analysis_labels=ANALYSIS_LABELS,
            spice_values=spice_values or dict(SPICE_DEFAULT_VALUES),
            spice_units=spice_units or dict(SPICE_DEFAULT_UNITS),
            spice_resistor_specs=SPICE_RESISTOR_SPECS,
            spice_cap_specs=SPICE_CAP_SPECS,
            spice_unit_choices=SPICE_UNIT_CHOICES,
            spice_result=spice_result,
            spice_display=build_spice_display(spice_result),
            provenance_rows=build_provenance_rows(spice_result),
            engine=engine,
            charts=build_charts(spice_result) if charts is None else charts,
        ),
        status,
    )


@app.get("/")
def index():
    analysis = request.args.get("analysis", "bias")
    if analysis not in ANALYSES:
        return render_page(
            DEFAULT_VALUES, DEFAULT_UNITS, "divider",
            errors={"analysis": "การวิเคราะห์ไม่ถูกต้อง"}, status=400,
        )
    mode = request.args.get("mode", "divider")
    if analysis == "bias":
        if mode not in MODES:
            return render_page(
                DEFAULT_VALUES, DEFAULT_UNITS, "divider",
                errors={"mode": "โหมดไม่ถูกต้อง"}, status=400,
            )
        return render_page(DEFAULT_VALUES, DEFAULT_UNITS, mode)
    if mode not in MODES:
        mode = "divider"
    return render_page(
        DEFAULT_VALUES, DEFAULT_UNITS, mode, analysis=analysis,
        spice_values=dict(SPICE_DEFAULT_VALUES),
        spice_units=dict(SPICE_DEFAULT_UNITS),
    )


@app.post("/calculate")
def calculate():
    analysis = request.form.get("analysis", "bias")
    if analysis not in ANALYSES:
        return render_page(
            DEFAULT_VALUES, DEFAULT_UNITS, "divider",
            errors={"analysis": "การวิเคราะห์ไม่ถูกต้อง"}, status=400,
        )

    if analysis == "bias":
        mode = request.form.get("mode", "")
        values = {key: request.form.get(key, "") for key in DEFAULT_VALUES}
        units = {key: request.form.get(key, "") for key in DEFAULT_UNITS}

        values_si, errors = parse_form(request.form, mode)
        if errors:
            render_mode = mode if mode in MODES else "divider"
            return render_page(values, units, render_mode, errors=errors, status=400)

        return render_page(
            values, units, mode, result=SOLVERS[mode](**values_si).to_dict(),
        )

    values = {
        key: request.form.get(key, SPICE_DEFAULT_VALUES[key]) for key in SPICE_FIELDS
    }
    units = {
        key: request.form.get(key, SPICE_DEFAULT_UNITS[key]) for key in SPICE_UNIT_KEYS.values()
    }
    values_si, errors = parse_spice_form(request.form)
    if errors:
        return render_page(
            values, units, "divider", errors=errors, status=400, analysis=analysis,
            spice_values=values, spice_units=units,
        )

    try:
        spice_result = run_analysis(analysis, values_si)
    except SpiceError as exc:
        status_name = "UNAVAILABLE" if isinstance(exc, EngineUnavailable) else "ERROR"
        engine = {"status": status_name, "message": str(exc)}
        spice_result = None
    else:
        engine = {"status": "OK", "message": ""}

    return render_page(
        values, units, "divider", analysis=analysis,
        spice_values=values, spice_units=units,
        spice_result=spice_result, engine=engine,
    )


if __name__ == "__main__":
    app.run(debug=True)
