"""Flask front end for the BJT DC bias calculator."""

import math

from flask import Flask, render_template, request

from dc_bias import solve

app = Flask(__name__)

UNITS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}

VALUE_FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
RESISTOR_UNITS = {
    "r1": "r1_unit",
    "r2": "r2_unit",
    "rc": "rc_unit",
    "re": "re_unit",
}

FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "β",
    "vbe": "VBE",
}

DEFAULT_VALUES = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
}

DEFAULT_UNITS = {
    "r1_unit": "kohm",
    "r2_unit": "kohm",
    "rc_unit": "kohm",
    "re_unit": "kohm",
}

UNIT_CHOICES = (
    ("ohm", "Ω"),
    ("kohm", "kΩ"),
    ("mohm", "MΩ"),
)


def parse_form(form) -> tuple[dict[str, float], dict[str, str]]:
    """Convert submitted text and units into SI values, collecting errors."""
    errors: dict[str, str] = {}
    numbers: dict[str, float] = {}

    for key in VALUE_FIELDS:
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

    for key in RESISTOR_UNITS:
        if key in numbers and numbers[key] <= 0:
            errors[key] = "ความต้านทานต้องมากกว่า 0 Ω"

    if "beta" in numbers and numbers["beta"] <= 0:
        errors["beta"] = "β ต้องมากกว่า 0"

    if "vbe" in numbers and "vcc" in numbers:
        if numbers["vbe"] < 0 or numbers["vbe"] >= numbers["vcc"]:
            errors["vbe"] = "VBE ต้องอยู่ระหว่าง 0 ถึง VCC"

    values_si = dict(numbers)
    for key, unit_key in RESISTOR_UNITS.items():
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


def build_display(result) -> dict[str, str]:
    """Pre-format every displayed value so the template holds no math."""
    return {
        "vb": f"{result.vb:.3f} V",
        "ve": f"{result.ve:.3f} V",
        "vc": f"{result.vc:.3f} V",
        "vce": f"{result.vce:.3f} V",
        "ic": format_current(result.ic),
        "ib": format_current(result.ib),
        "ie": format_current(result.ie),
    }


def render_page(values, units, result=None, errors=None, status=200):
    return (
        render_template(
            "index.html",
            values=values,
            units=units,
            unit_choices=UNIT_CHOICES,
            result=result,
            display=build_display(result) if result else None,
            errors=errors or {},
        ),
        status,
    )


@app.get("/")
def index():
    return render_page(DEFAULT_VALUES, DEFAULT_UNITS)


@app.post("/calculate")
def calculate():
    values = {key: request.form.get(key, "") for key in VALUE_FIELDS}
    units = {key: request.form.get(key, "") for key in RESISTOR_UNITS.values()}

    values_si, errors = parse_form(request.form)
    if errors:
        return render_page(values, units, errors=errors, status=400)

    return render_page(values, units, result=solve(**values_si))


if __name__ == "__main__":
    app.run(debug=True)
