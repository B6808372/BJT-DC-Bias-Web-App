# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง Flask Web App หลายไฟล์ที่คำนวณ DC Operating Point ของวงจร BJT Voltage-Divider Bias จากค่าที่ผู้ใช้กรอก พร้อม validation, warning นอก Forward-Active และ automated tests

**Architecture:** แยกสมการวิศวกรรมล้วนไว้ใน `dc_bias.py` (SI units, ไม่รู้จัก HTTP/HTML) ส่วน `app.py` ทำหน้าที่ parse ฟอร์ม แปลงหน่วย และเรียก `dc_bias.solve()` แล้ว render `templates/index.html` ด้วย Jinja หน้าเดียว (GET / แสดงฟอร์ม, POST /calculate แสดงผล)

**Tech Stack:** Python 3.14.2, Flask 3.x, Jinja2, unittest, HTML/CSS ล้วน (ไม่มี JavaScript)

**Spec:** `docs/design-note.md`

## Global Constraints

- Python 3.14.2 — ใช้เฉพาะ standard library + Flask (ไม่เพิ่ม dependency อื่น)
- คำสั่งทดสอบ: `python -m unittest discover -s tests -v` (ไม่ใช้ pytest)
- `dc_bias.py` รับ/คืนค่าเป็น SI เท่านั้น (V, Ω, A) — ห้ามมี kΩ หรือ HTML ในไฟล์นี้
- แปลงหน่วย Ω/kΩ/MΩ ที่ `app.py` ด้วยตัวคูณ 1, 1e3, 1e6
- อินพุตผิด → render หน้าเดิมพร้อม error และ **HTTP 400** (ห้าม exception หลุด)
- ค่า `VCE_SAT = 0.2` V ใช้ตัดสิน Saturation
- แสดงผลปัด 3 ตำแหน่ง แต่คำนวณด้วย float เต็มความละเอียด
- **ห้าม commit ผ่าน git CLI** — ทุกขั้น Commit ให้แจ้งผู้ใช้กดใน GitHub Desktop (Summary ระบุไว้ในขั้นนั้น)
- ห้าม commit `.venv/`, `__pycache__/`, `.env`

## Review Focus

- **หน่วยตัวต้านทาน:** ผู้ใช้เลือก kΩ แต่ลืมคูณ → ผลคลาด 1000 เท่า (test unit equivalence ใน Task 4)
- **VTH ≤ VBE:** ถ้ายังคำนวณต่อจะได้ IB ติดลบ ต้องรายงาน Cutoff + warning (test ใน Task 2)
- **VCE ต่ำ/ติดลบ:** RC ใหญ่ทำให้ VC ต่ำกว่า VE ต้องรายงาน Saturation ไม่ใช่ Active (test ใน Task 2)
- **ค่าที่ไม่ใช่ตัวเลข/ช่องว่าง:** ต้องไม่ทำให้เกิด 500 หรือ traceback (test ใน Task 4)
- **ค่าที่กรอกหายหลัง error:** ฟอร์มต้องคงค่าที่พิมพ์ไว้ (test sticky value ใน Task 4)

---

## File Structure

| ไฟล์ | ความรับผิดชอบ |
|---|---|
| `dc_bias.py` | dataclass `OperatingPoint` + `solve()` — สมการและ region logic |
| `app.py` | Flask routes, parse ฟอร์ม, แปลงหน่วย, validation, เลือก HTTP status |
| `templates/index.html` | ฟอร์ม + ตารางผล + error/warning (Jinja, ไม่มีสมการ) |
| `static/style.css` | layout/responsive |
| `tests/test_dc_bias.py` | unit tests ทางวิศวกรรม |
| `tests/test_web.py` | Flask test client |
| `requirements.txt` | `Flask>=3.0` |
| `README.md` | วิธีติดตั้ง/รัน/ทดสอบ |
| `AGENTS.md` | conventions สำหรับ AI |
| `docs/validation.md` | คำนวณอ้างอิง + test log |
| `docs/reflection.md` | สิ่งที่เรียนรู้ |

---

### Task 1: Engineering core — Forward-Active solve

**Files:**
- Create: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Produces:
  - `VCE_SAT: float = 0.2`
  - `@dataclass(frozen=True) class OperatingPoint` มีฟิลด์: `vb, ve, vc, vce, ib, ic, ie, vth, rth: float`, `region: str`, `warnings: tuple[str, ...]`
  - `solve(vcc: float, r1: float, r2: float, rc: float, re: float, beta: float, vbe: float) -> OperatingPoint`
  - `region` มีค่าได้ 3 แบบเท่านั้น: `"active"`, `"cutoff"`, `"saturation"`

- [ ] **Step 1: เขียน failing tests**

`tests/test_dc_bias.py`:
```python
import unittest
from dc_bias import solve


class TestActiveRegion(unittest.TestCase):
    def test_reference_example(self):
        op = solve(vcc=12.0, r1=100_000, r2=22_000, rc=2_200,
                   re=1_000, beta=100, vbe=0.70)
        self.assertAlmostEqual(op.vb, 1.942, places=3)
        self.assertAlmostEqual(op.ve, 1.242, places=3)
        self.assertAlmostEqual(op.vc, 9.294, places=3)
        self.assertAlmostEqual(op.vce, 8.052, places=3)
        self.assertAlmostEqual(op.ic * 1000, 1.230, places=3)
        self.assertEqual(op.region, "active")
        self.assertEqual(op.warnings, ())

    def test_kcl_holds(self):
        op = solve(12, 100_000, 22_000, 2_200, 1_000, 100, 0.7)
        self.assertAlmostEqual(op.ie, op.ib + op.ic, places=12)
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: ERROR `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: สร้าง `dc_bias.py`**

สร้าง dataclass `OperatingPoint` (frozen) และ `solve()` ตามสมการใน design note §7.5:
`vth`, `rth`, `ib`, `ic`, `ie`, `ve`, `vb`, `vc`, `vce`
— Task นี้ยังไม่ต้องมี region logic ให้ตั้ง `region="active"`, `warnings=()`

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit (GitHub Desktop)**

แจ้งผู้ใช้: เปิด GitHub Desktop → Changes → Summary: `Add DC bias engineering core` → Commit to main → Push origin

---

### Task 2: Region detection — Cutoff และ Saturation

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py` (เพิ่มคลาสใหม่)

**Interfaces:**
- Consumes: `solve()` จาก Task 1
- Produces: พฤติกรรม `region` / `warnings` ตาม design note §7.7

- [ ] **Step 1: เขียน failing tests**

เพิ่มใน `tests/test_dc_bias.py`:
```python
class TestOutsideActiveRegion(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self):
        op = solve(12, 100_000, 5_000, 2_200, 1_000, 100, 0.7)
        self.assertEqual(op.region, "cutoff")
        self.assertAlmostEqual(op.ib, 0.0)
        self.assertAlmostEqual(op.ic, 0.0)
        self.assertAlmostEqual(op.ie, 0.0)
        self.assertAlmostEqual(op.ve, 0.0)
        self.assertAlmostEqual(op.vb, op.vth)
        self.assertAlmostEqual(op.vc, 12.0)
        self.assertTrue(any("Forward-Active" in w for w in op.warnings))

    def test_saturation_when_vce_below_sat(self):
        op = solve(12, 100_000, 22_000, 10_000, 100, 100, 0.7)
        self.assertEqual(op.region, "saturation")
        self.assertLess(op.vce, 0.2)
        self.assertTrue(any("Saturation" in w for w in op.warnings))
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: FAIL — `region` เป็น `"active"` ไม่ใช่ `"cutoff"`/`"saturation"`

- [ ] **Step 3: เพิ่ม region logic ใน `solve()`**

หลังคำนวณ `vth` แล้ว: ถ้า `vth <= vbe` → ตั้งค่า cutoff ตาม §7.7 และใส่ warning
`"แบบจำลอง Forward-Active ใช้ไม่ได้: VTH <= VBE (Cutoff)"`
ไม่เช่นนั้นคำนวณปกติ แล้วถ้า `vce < VCE_SAT` → `region="saturation"` + warning
`"Saturation: VCE ต่ำกว่า VCE(sat) — ผลไม่อยู่ใน Forward-Active"`

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit (GitHub Desktop)**

Summary: `Add cutoff and saturation warnings` → Commit to main → Push origin

---

### Task 3: Flask app — หน้าแรกและฟอร์ม

**Files:**
- Create: `app.py`, `requirements.txt`, `templates/index.html`, `static/style.css`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `dc_bias.solve`, `dc_bias.OperatingPoint`
- Produces:
  - Flask app object ชื่อ `app`
  - route `GET /` → `render_template("index.html", values=..., units=..., result=None, errors={})` status 200
  - ชื่อฟิลด์ฟอร์ม: `vcc, r1, r2, rc, re, beta, vbe` และ `r1_unit, r2_unit, rc_unit, re_unit`
  - ค่าเริ่มต้น: vcc=12, r1=100, r2=22, rc=2.2, re=1, beta=100, vbe=0.70, หน่วยตัวต้านทาน `kohm`

- [ ] **Step 1: เขียน failing test**

`tests/test_web.py`:
```python
import unittest
from app import app


class TestFormPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        for field in ["vcc", "r1", "r2", "rc", "re", "beta", "vbe",
                      "r1_unit", "r2_unit", "rc_unit", "re_unit"]:
            self.assertIn(f'name="{field}"', html)
        self.assertIn("Calculate DC Bias", html)
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest tests.test_web -v`
Expected: ERROR `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: ติดตั้ง Flask และสร้างไฟล์**

Run: `python -m pip install -r requirements.txt`
`requirements.txt`: `Flask>=3.0`
สร้าง `app.py` ที่มี `app = Flask(__name__)` และ route `GET /` ส่งค่าเริ่มต้น
สร้าง `templates/index.html` มี `<form method="post" action="/calculate">` และ input name ตาม Interfaces
สร้าง `static/style.css` เป็นไฟล์ว่างก่อน (จัดเต็มใน Task 5)

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest tests.test_web -v`
Expected: 1 test PASS

- [ ] **Step 5: Commit (GitHub Desktop)**

Summary: `Add Flask form page` → Commit to main → Push origin

---

### Task 4: POST /calculate — แปลงหน่วย, validation, แสดงผล

**Files:**
- Modify: `app.py`, `templates/index.html`
- Test: `tests/test_web.py` (เพิ่มคลาส)

**Interfaces:**
- Produces:
  - `parse_form(form) -> tuple[dict[str, float], dict[str, str]]` คืน `(values_si, errors)`
    โดย `values_si` มีคีย์ `vcc, r1, r2, rc, re, beta, vbe` หน่วย SI
  - route `POST /calculate` → สำเร็จ 200, ผิด 400, template รับ `result` (OperatingPoint), `errors`, `values`, `units`
  - `UNITS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}`

- [ ] **Step 1: เขียน failing tests**

เพิ่มใน `tests/test_web.py`:
```python
class TestCalculate(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _payload(self, **overrides):
        data = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
                "beta": "100", "vbe": "0.70",
                "r1_unit": "kohm", "r2_unit": "kohm",
                "rc_unit": "kohm", "re_unit": "kohm"}
        data.update(overrides)
        return data

    def test_valid_input_shows_results(self):
        res = self.client.post("/calculate", data=self._payload())
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        for expected in ["9.294", "8.052", "1.942", "1.242"]:
            self.assertIn(expected, html)
        self.assertIn("Active", html)

    def test_unit_conversion_matches_ohms(self):
        kohm = self.client.post("/calculate", data=self._payload())
        ohm = self.client.post("/calculate", data=self._payload(
            r1="100000", r2="22000", rc="2200", re="1000",
            r1_unit="ohm", r2_unit="ohm", rc_unit="ohm", re_unit="ohm"))
        self.assertEqual(kohm.get_data(as_text=True),
                         ohm.get_data(as_text=True))

    def test_zero_resistance_shows_error(self):
        res = self.client.post("/calculate", data=self._payload(r1="0"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("มากกว่า 0", res.get_data(as_text=True))

    def test_non_numeric_keeps_typed_value(self):
        res = self.client.post("/calculate", data=self._payload(r1="abc"))
        self.assertEqual(res.status_code, 400)
        html = res.get_data(as_text=True)
        self.assertIn("กรุณากรอกตัวเลข", html)
        self.assertIn('value="abc"', html)
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — POST `/calculate` ตอบ 404

- [ ] **Step 3: เพิ่ม `parse_form()` และ route `POST /calculate`**

`parse_form` ตรวจ: ช่องว่าง/ไม่ใช่ตัวเลข → `"กรุณากรอกตัวเลข: <ชื่อช่อง>"`;
VCC ≤ 0, R ≤ 0, β ≤ 0, VBE < 0 หรือ VBE ≥ VCC, หน่วยไม่อยู่ใน `UNITS`
— route เรียก `dc_bias.solve(**values_si)` แล้ว render template เดิมพร้อมผล

- [ ] **Step 4: เพิ่มส่วนแสดงผลใน `templates/index.html`**

แสดงตาราง VB, VE, VC, VCE (V), IC, IB, IE (mA/µA), ป้าย region และ warning list
แสดง error ใต้ช่องที่ผิด และคงค่าที่กรอกด้วย `value="{{ values.<field> }}"`
ห้ามเขียนค่าคงที่ของผลลัพธ์ลงใน HTML

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: 9 tests PASS (4 engineering + 5 web)

- [ ] **Step 6: Commit (GitHub Desktop)**

Summary: `Calculate DC bias from form input with validation` → Commit to main → Push origin

---

### Task 5: Styling, เอกสาร และการตรวจด้วยมือ

**Files:**
- Modify: `static/style.css`
- Create: `README.md`, `AGENTS.md`, `docs/validation.md`, `docs/reflection.md`

**Interfaces:**
- Consumes: ทุกไฟล์จาก Task 1–4

- [ ] **Step 1: เขียน `static/style.css`**

Layout 2 คอลัมน์บนจอ ≥ 800px (ฟอร์มซ้าย/ผลขวา), 1 คอลัมน์บนมือถือ;
ป้าย Active = เขียว, warning = ส้ม; ใช้ฟอนต์ system-ui/Tahoma

- [ ] **Step 2: เขียน `README.md`**

ต้องมีคำสั่ง: `python -m venv .venv`, activate ตาม OS,
`python -m pip install -r requirements.txt`, `python -m flask --app app run --debug`,
`python -m unittest discover -s tests -v` และ URL `http://127.0.0.1:5000/`

- [ ] **Step 3: เขียน `AGENTS.md`**

ระบุ: สมการอยู่ที่ `dc_bias.py` เท่านั้น, ห้ามฝังตัวเลขผลลัพธ์ใน template,
เพิ่ม test ทุกครั้งที่แก้สมการ, ใช้ unittest

- [ ] **Step 4: รันเว็บและตรวจด้วยมือ**

Run: `python -m flask --app app run --debug`
ตรวจในเบราว์เซอร์: ค่าตัวอย่าง → ได้ VB 1.942, VE 1.242, VC 9.294, VCE 8.052, IC 1.230 mA, ป้าย Active
ทดลอง R1=0 → เห็น error, หน้าไม่ล้ม

- [ ] **Step 5: เขียน `docs/validation.md` และ `docs/reflection.md`**

validation: ตารางคำนวณอ้างอิงด้วยมือ (VTH, RTH, IB, IC, IE, VE, VB, VC, VCE),
ผลรัน test ทั้งหมด (copy จาก terminal), ผลตรวจในเบราว์เซอร์
reflection: สิ่งที่เรียนรู้เรื่อง Frontend/Backend/HTTP/Template และข้อจำกัดของแบบจำลอง

- [ ] **Step 6: รัน test ครั้งสุดท้าย**

Run: `python -m unittest discover -s tests -v`
Expected: 9 tests PASS (บันทึก log ลง `docs/validation.md`)

- [ ] **Step 7: Commit (GitHub Desktop)**

Summary: `Add styling, README and validation docs` → Commit to main → Push origin
จากนั้นคัดลอก commit SHA ล่าสุดจากแท็บ History ไว้ส่ง Moodle

---

## Self-Review

- **Spec coverage:** A1 (Task 3), A2 (Task 4), A3 (Task 1 + validation.md), A4 (Task 4), A5 (Task 2), A6 (Task 1–4), A7 (Task 5 + README) — ครบ
- **Step granularity:** ทุกขั้นมีคำสั่ง/ผลลัพธ์ตรวจได้ ไม่มี "handle edge cases" ลอย ๆ
- **Type consistency:** `OperatingPoint` ฟิลด์ตรงกันทุก task, ชื่อฟิลด์ฟอร์มตรงกับ `parse_form`, `UNITS` คีย์ `ohm/kohm/mohm` ตรงกับ `value` ในเทมเพลต
- **Review Focus:** ทั้ง 5 ข้อมี test ใน Task 2 และ Task 4
