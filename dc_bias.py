"""DC bias calculations for BJT common-emitter bias circuits.

All inputs and outputs use SI units only: volts, ohms and amperes.
This module knows nothing about HTTP, HTML or kOhm entry fields.
"""

from dataclasses import dataclass

VCE_SAT = 0.2

CUTOFF_WARNING = "แบบจำลอง Forward-Active ใช้ไม่ได้: IB ≤ 0 (Cutoff)"
SATURATION_WARNING = "แบบจำลอง Forward-Active ใช้ไม่ได้: VCE ≤ VCE(sat) (Saturation)"


@dataclass(frozen=True)
class OperatingPoint:
    """Result of a DC bias calculation."""

    vb: float
    ve: float
    vc: float
    vce: float
    ib: float
    ic: float
    ie: float
    region: str
    warnings: tuple[str, ...]
    vth: float | None = None
    rth: float | None = None

    def to_dict(self) -> dict:
        """Return the agreed dict contract consumed by the Flask layer."""
        return {
            "vb_v": self.vb,
            "ve_v": self.ve,
            "vc_v": self.vc,
            "vce_v": self.vce,
            "ib_a": self.ib,
            "ic_a": self.ic,
            "ie_a": self.ie,
            "region": self.region,
            "warnings": self.warnings,
            "vth_v": self.vth,
            "rth_ohm": self.rth,
        }


def _from_base_current(
    vcc: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
    ib: float,
) -> OperatingPoint:
    """Finish a forward-active calculation once IB is known."""
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    if ib <= 0:
        return OperatingPoint(
            vb=vcc,
            ve=0.0,
            vc=vcc,
            vce=vcc,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            region="cutoff",
            warnings=(CUTOFF_WARNING,),
        )

    if vce <= VCE_SAT:
        region = "saturation"
        warnings = (SATURATION_WARNING,)
    else:
        region = "active"
        warnings = ()

    return OperatingPoint(
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        ib=ib,
        ic=ic,
        ie=ie,
        region=region,
        warnings=warnings,
    )


def solve_fixed(
    vcc: float,
    rb: float,
    rc: float,
    beta: float,
    vbe: float,
) -> OperatingPoint:
    """Fixed bias: RB from VCC to base, emitter tied directly to ground."""
    ib = (vcc - vbe) / rb
    return _from_base_current(vcc, rc, 0.0, beta, vbe, ib)


def solve_emitter(
    vcc: float,
    rb: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> OperatingPoint:
    """Single-supply emitter bias: RB to base and RE from emitter to ground."""
    ib = (vcc - vbe) / (rb + (beta + 1) * re)
    return _from_base_current(vcc, rc, re, beta, vbe, ib)


def solve(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> OperatingPoint:
    """Solve the voltage-divider bias operating point (Lab 2 behaviour)."""
    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)

    if vth <= vbe:
        return OperatingPoint(
            vb=vth,
            ve=0.0,
            vc=vcc,
            vce=vcc,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            region="cutoff",
            warnings=(
                "แบบจำลอง Forward-Active ใช้ไม่ได้: VTH <= VBE (Cutoff)",
            ),
            vth=vth,
            rth=rth,
        )

    ib = (vth - vbe) / (rth + (beta + 1) * re)
    ic = beta * ib
    ie = (beta + 1) * ib

    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    if vce < VCE_SAT:
        region = "saturation"
        warnings = (
            "Saturation: VCE ต่ำกว่า VCE(sat) — ผลไม่อยู่ใน Forward-Active",
        )
    else:
        region = "active"
        warnings = ()

    return OperatingPoint(
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        ib=ib,
        ic=ic,
        ie=ie,
        region=region,
        warnings=warnings,
        vth=vth,
        rth=rth,
    )
