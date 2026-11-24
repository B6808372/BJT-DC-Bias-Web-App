"""Adapter for real ngspice DC, AC and transient runs.

This module owns netlist generation, executable discovery, subprocess
execution and parsing of ngspice output files. It never fabricates results.
"""

import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

MODEL_NAME = "QT_NPN teaching model"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "bjt_teaching.lib"


class SpiceError(Exception):
    """Base class for engine failures."""


class EngineUnavailable(SpiceError):
    """ngspice executable was not found."""


class EngineRunError(SpiceError):
    """ngspice exited unsuccessfully or did not write the expected file."""


class EngineTimeout(SpiceError):
    """ngspice exceeded the allowed run time."""


class EngineOutputError(SpiceError):
    """ngspice output was empty, malformed or incomplete."""


def find_engine() -> str | None:
    """Return the ngspice executable path, preferring NGSPICE_CMD."""
    configured = os.environ.get("NGSPICE_CMD", "").strip()
    if configured:
        return configured
    return shutil.which("ngspice_con") or shutil.which("ngspice")


def _trim(number: float) -> str:
    return f"{number:.6g}"


def format_spice_value(value: float) -> str:
    """Format an SI value with an SPICE engineering suffix."""
    magnitude = abs(value)
    sign = "-" if value < 0 else ""
    for scale, suffix in (
        (1e6, "meg"),
        (1e3, "k"),
        (1.0, ""),
        (1e-3, "m"),
        (1e-6, "u"),
        (1e-9, "n"),
        (1e-12, "p"),
    ):
        if magnitude >= scale:
            scaled = value / scale
            return f"{sign}{_trim(abs(scaled))}{suffix}"
    return f"{value:.3g}"


def _model_include() -> str:
    # Quote the path: ngspice stops an unquoted filename at the first space.
    return f'"{MODEL_PATH.resolve().as_posix()}"'


def _common_netlist(values_si: dict[str, float]) -> str:
    amp = format_spice_value(values_si["source_amp_v"])
    freq = format_spice_value(values_si["source_freq_hz"])
    return "\n".join(
        [
            "* Lab 04 CE voltage-divider amplifier",
            f".include {_model_include()}",
            f"VCC VCC 0 DC {format_spice_value(values_si['vcc'])}",
            f"VIN IN 0 DC 0 AC {amp} SIN(0 {amp} {freq} 0 0)",
            f"R1 VCC B {format_spice_value(values_si['r1'])}",
            f"R2 B 0 {format_spice_value(values_si['r2'])}",
            f"RC VCC C {format_spice_value(values_si['rc'])}",
            f"RE E 0 {format_spice_value(values_si['re'])}",
            f"RL OUT 0 {format_spice_value(values_si['rl'])}",
            f"Cin IN B {format_spice_value(values_si['cin'])}",
            f"Cout C OUT {format_spice_value(values_si['cout'])}",
            "Q1 C B E QT_NPN",
        ]
    )


def _control_block(analysis: str, values_si: dict[str, float]) -> str:
    if analysis == "dc":
        vectors = "v(b) v(e) v(c) v(c,e) @q1[ic] @q1[ib] @q1[ie]"
        return f".control\nop\nwrdata op.csv {vectors}\n.endc"
    if analysis == "ac":
        return (
            ".control\n"
            "ac dec 10 10 10meg\n"
            "wrdata ac.csv vm(in) vp(in) vm(out) vp(out)\n"
            ".endc"
        )
    if analysis == "tran":
        frequency = values_si["source_freq_hz"]
        stop = min(max(5.0 / frequency, 1e-3), 20e-3)
        step = stop / 2000.0
        return (
            ".control\n"
            f"tran {format_spice_value(step)} {format_spice_value(stop)}\n"
            "wrdata tran.csv v(in) v(out)\n"
            ".endc"
        )
    raise ValueError(f"unknown analysis: {analysis}")


def build_netlist(analysis: str, values_si: dict[str, float]) -> str:
    """Return a complete netlist for one analysis."""
    return f"{_common_netlist(values_si)}\n{_control_block(analysis, values_si)}\n.end\n"


def parse_wrdata(text: str, series_count: int) -> list[list[tuple[float, float]]]:
    """Parse ngspice `wrdata` files into one (x, y) series per vector."""
    if series_count < 1 or not text or not text.strip():
        raise EngineOutputError("wrdata output is empty")
    rows: list[list[tuple[float, float]]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        tokens = line.split()
        if len(tokens) != series_count * 2:
            raise EngineOutputError("wrdata row has the wrong number of columns")
        try:
            values = [float(token) for token in tokens]
        except ValueError as exc:
            raise EngineOutputError("wrdata contains a non-numeric value") from exc
        if not all(math.isfinite(value) for value in values):
            raise EngineOutputError("wrdata contains a non-finite value")
        rows.append([(values[i], values[i + 1]) for i in range(0, len(values), 2)])
    if not rows:
        raise EngineOutputError("wrdata output has no rows")
    return [[row[index] for row in rows] for index in range(series_count)]


def parse_op(csv_text: str) -> dict[str, float]:
    """Read DC operating-point values written by @q1 device queries."""
    series = parse_wrdata(csv_text, 7)
    keys = ("vb_v", "ve_v", "vc_v", "vce_v", "ic_a", "ib_a", "ie_a")
    return {key: series[index][0][1] for index, key in enumerate(keys)}


def _wrap_phase(degrees: float) -> float:
    while degrees >= 180.0:
        degrees -= 360.0
    while degrees < -180.0:
        degrees += 360.0
    return degrees


def parse_ac(csv_text: str, frequency_hz: float) -> dict:
    """Parse AC samples; ngspice `vp()` is in radians, output is in degrees."""
    if frequency_hz <= 0 or not math.isfinite(frequency_hz):
        raise EngineOutputError("AC marker frequency must be positive")
    series = parse_wrdata(csv_text, 4)
    points = []
    for vm_in_series, vp_in_series, vm_out_series, vp_out_series in zip(*series):
        _, vm_in = vm_in_series
        _, vp_in = vp_in_series
        _, vm_out = vm_out_series
        _, vp_out = vp_out_series
        if vm_in <= 0 or vm_out <= 0:
            raise EngineOutputError("AC magnitude must be positive")
        points.append(
            {
                "freq_hz": vm_in_series[0],
                "vm_in": vm_in,
                "vm_out": vm_out,
                "gain_db": 20.0 * math.log10(vm_out / vm_in),
                "phase_deg": _wrap_phase(math.degrees(vp_out - vp_in)),
            }
        )
    frequencies = [point["freq_hz"] for point in points]
    if frequency_hz < min(frequencies) or frequency_hz > max(frequencies):
        return {"points": points, "marker": None,
                "marker_note": "not determined in sweep range"}
    marker = min(
        points,
        key=lambda point: abs(math.log10(point["freq_hz"]) - math.log10(frequency_hz)),
    )
    return {"points": points, "marker": marker, "marker_note": ""}


def _downsample(points: list[dict], limit: int = 1200) -> list[dict]:
    if len(points) <= limit:
        return points
    count = len(points)
    indices = sorted({round(i * (count - 1) / (limit - 1)) for i in range(limit)})
    return [points[i] for i in indices]


def parse_tran(csv_text: str, frequency_hz: float) -> dict:
    """Parse transient samples and measure the final cycle of v(out)."""
    if frequency_hz <= 0 or not math.isfinite(frequency_hz):
        raise EngineOutputError("transient frequency must be positive")
    series = parse_wrdata(csv_text, 2)
    points = [
        {"time_s": vin_sample[0], "vin_v": vin_sample[1], "vout_v": vout_sample[1]}
        for vin_sample, vout_sample in zip(*series)
    ]
    if not points:
        raise EngineOutputError("transient output has no samples")
    times = [point["time_s"] for point in points]
    period_s = 1.0 / frequency_hz
    window_start = max(times) - period_s
    window = [point for point in points if point["time_s"] >= window_start] or points[-1:]
    measurement_note = ""
    if window_start < min(times):
        measurement_note = (
            "less than one period simulated; peak-to-peak over available window"
        )
    else:
        step_s = (max(times) - min(times)) / max(len(times) - 1, 1)
        if period_s / step_s < 10:
            measurement_note = (
                "fewer than 10 samples per period; peak-to-peak is approximate"
            )
    outputs = [point["vout_v"] for point in window]
    peak_to_peak = max(outputs) - min(outputs)
    correlation = sum(point["vin_v"] * point["vout_v"] for point in window)
    return {
        "points": _downsample(points),
        "vout_pp_v": peak_to_peak,
        "vout_peak_v": peak_to_peak / 2.0,
        "phase_note": "inverted" if correlation < 0 else "in-phase or undetermined",
        "measurement_note": measurement_note,
    }


def engine_version(executable: str) -> str:
    """Return the ngspice version banner, or 'unknown' if unparseable."""
    try:
        completed = subprocess.run(
            [executable, "-v"],
            input="",
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    match = re.search(r"ngspice-([0-9]+(?:\.[0-9]+)?)", completed.stdout or "")
    return f"ngspice-{match.group(1)}" if match else "unknown"


def run_analysis(analysis: str, values_si: dict[str, float]) -> dict:
    """Run one real ngspice analysis and return parsed results or raise."""
    if analysis not in ("dc", "ac", "tran"):
        raise ValueError(f"unknown analysis: {analysis}")
    executable = find_engine()
    if not executable:
        raise EngineUnavailable("ngspice executable not found")
    version = engine_version(executable)
    filename = {"dc": "op.csv", "ac": "ac.csv", "tran": "tran.csv"}[analysis]

    with tempfile.TemporaryDirectory(prefix="lab04-ngspice-") as run_dir:
        working = Path(run_dir)
        (working / "case.cir").write_text(build_netlist(analysis, values_si), encoding="utf-8")
        try:
            completed = subprocess.run(
                [executable, "-b", "case.cir"],
                cwd=run_dir,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except subprocess.TimeoutExpired as exc:
            raise EngineTimeout("ngspice run timed out") from exc
        except OSError as exc:
            raise EngineUnavailable(f"cannot execute ngspice: {exc}") from exc
        if completed.returncode != 0:
            raise EngineRunError((completed.stderr or completed.stdout or "ngspice failed").strip())
        output = working / filename
        try:
            text = output.read_text(encoding="utf-8")
        except OSError as exc:
            raise EngineRunError(f"ngspice did not write {filename}") from exc

    result = {
        "analysis": analysis,
        "status": "OK",
        "op": parse_op(text) if analysis == "dc" else None,
        "ac": parse_ac(text, values_si["source_freq_hz"]) if analysis == "ac" else None,
        "tran": parse_tran(text, values_si["source_freq_hz"]) if analysis == "tran" else None,
        "provenance": {
            "engine": executable,
            "version": version,
            "model": MODEL_NAME,
            "model_path": MODEL_PATH.resolve().as_posix(),
            "analysis": analysis,
            "fixture": dict(values_si),
            "rows": sum(1 for line in text.splitlines() if line.strip()),
            "stdout_tail": (completed.stdout or "").strip()[-2000:],
        },
    }
    return result


__all__ = [
    "MODEL_NAME",
    "MODEL_PATH",
    "EngineOutputError",
    "EngineRunError",
    "EngineTimeout",
    "EngineUnavailable",
    "SpiceError",
    "build_netlist",
    "engine_version",
    "find_engine",
    "format_spice_value",
    "parse_ac",
    "parse_op",
    "parse_tran",
    "parse_wrdata",
    "run_analysis",
]
