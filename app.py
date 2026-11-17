"""Flask front end for the BJT DC bias calculator."""

import math

from flask import Flask, render_template, request

from dc_bias import solve, solve_fixed, solve_emitter

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


def render_page(values, units, mode, result=None, errors=None, status=200):
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
        ),
        status,
    )


@app.get("/")
def index():
    mode = request.args.get("mode", "divider")
    if mode not in MODES:
        return render_page(
            DEFAULT_VALUES, DEFAULT_UNITS, "divider",
            errors={"mode": "โหมดไม่ถูกต้อง"}, status=400,
        )
    return render_page(DEFAULT_VALUES, DEFAULT_UNITS, mode)


@app.post("/calculate")
def calculate():
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


if __name__ == "__main__":
    app.run(debug=True)
