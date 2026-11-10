"""DC bias calculations for a BJT common-emitter voltage-divider bias circuit.

All inputs and outputs use SI units only: volts, ohms and amperes.
This module knows nothing about HTTP, HTML or kOhm entry fields.
"""

from dataclasses import dataclass

VCE_SAT = 0.2


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
    vth: float
    rth: float
    region: str
    warnings: tuple[str, ...]


def solve(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> OperatingPoint:
    """Solve the forward-active DC operating point (SI units)."""
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
            vth=vth,
            rth=rth,
            region="cutoff",
            warnings=(
                "แบบจำลอง Forward-Active ใช้ไม่ได้: VTH <= VBE (Cutoff)",
            ),
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
        vth=vth,
        rth=rth,
        region=region,
        warnings=warnings,
    )
