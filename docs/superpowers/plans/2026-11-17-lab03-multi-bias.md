# Lab 03 Multi-Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ขยายเว็บ Lab 2 ให้เลือก Voltage Divider / Fixed / Emitter Bias โดย Divider ได้ผลเดิมทุกตัว

**Architecture:** คง `OperatingPoint` เป็นโครงผลลัพธ์ภายใน เพิ่ม `to_dict()` เป็นสัญญากับ Flask; เพิ่ม `solve_fixed()` และ `solve_emitter()` ใน `dc_bias.py`; `app.py` ใช้ตาราง `SOLVERS` เลือกตาม `mode` และตรวจเฉพาะฟิลด์ที่โหมดนั้นใช้; template ใช้ GET form เปลี่ยนโหมด ไม่ใช้ JavaScript

**Tech Stack:** Python 3.14, Flask 3.1.3, unittest, Jinja2

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`

## Global Constraints
- สมการอยู่ใน `dc_bias.py` เท่านั้น ห้ามคำนวณใน template
- หน่วยภายในเป็น SI; แปลง Ω/kΩ/MΩ เฉพาะใน `app.py`
- 17 test เดิมต้องผ่านทุกตัวหลังทุก task
- ทุกครั้งที่เปลี่ยนสมการ/validation ต้องเพิ่มหรือแก้ test
- ใช้ `unittest`: `python -m unittest discover -s tests -v`
- ผมไม่รัน `git commit` — human partner ใช้ GitHub Desktop เอง

## Review Focus
1. โหมด fixed ได้รับ `re="abc"` → ต้องไม่ error เพราะโหมดนี้ไม่ใช้ RE — pin ด้วย `test_fixed_ignores_unused_fields`
2. โหมด emitter ได้รับ `r1="abc", r2="abc"` → ต้องไม่ error — pin ด้วย `test_emitter_ignores_unused_fields`
3. `mode="bogus"` → 400 + ไม่มี `<section class="results"` — pin ด้วย `test_unknown_mode_returns_error`
4. รอบต่อไปกรอกผิด → ต้องไม่โชว์ผลรอบก่อน (stateless test client ตรวจ absence ของ results) — pin ด้วย `test_error_does_not_show_results`
5. A4 เปลี่ยน RE เดียวจาก 1→2 kΩ → IC ต้องลด 1.026→0.940 mA — pin ด้วย `test_emitter_re_change_affects_ic`
6. RB=1 MΩ ต้องแปลงเป็น 1e6 Ω ครั้งเดียว — pin ด้วย `test_rb_unit_conversion`

---

### Task 1: สมการ Fixed/Emitter + สัญญา dict

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: ไม่มี
- Produces: `OperatingPoint.to_dict() -> dict`; `solve_fixed(vcc,rb,rc,beta,vbe)->OperatingPoint`; `solve_emitter(vcc,rb,rc,re,beta,vbe)->OperatingPoint`; `solve()` เดิมไม่เปลี่ยนลายเซ็น

- [ ] **Step 1: เขียน test ที่ fail ก่อน**

เพิ่มใน `tests/test_dc_bias.py`:
```python
class TestNewCircuits(unittest.TestCase):
    def test_fixed_reference(self):
        op = solve_fixed(12.0, 1_000_000, 2_200, 100, 0.70)
        self.assertAlmostEqual(op.ib * 1e6, 11.3, places=3)
        self.assertAlmostEqual(op.ic * 1000, 1.130, places=3)
        self.assertAlmostEqual(op.vb, 0.70, places=3)
        self.assertAlmostEqual(op.ve, 0.0, places=3)
        self.assertAlmostEqual(op.vce, 9.514, places=3)
        self.assertEqual(op.region, "active")

    def test_emitter_reference(self):
        op = solve_emitter(12.0, 1_000_000, 2_200, 1_000, 100, 0.70)
        self.assertAlmostEqual(op.ic * 1000, 1.026340, places=5)
        self.assertAlmostEqual(op.ve, 1.036603, places=5)
        self.assertAlmostEqual(op.vce, 8.705450, places=5)

    def test_emitter_re_doubling_reduces_ic(self):
        a = solve_emitter(12.0, 1e6, 2200, 1_000, 100, 0.7)
        b = solve_emitter(12.0, 1e6, 2200, 2_000, 100, 0.7)
        self.assertLess(b.ic, a.ic)
        self.assertAlmostEqual(b.ic * 1000, 0.940100, places=5)

    def test_non_positive_base_current_warns(self):
        op = solve_fixed(12.0, 1e6, 2200, 100, 12.0)
        self.assertEqual(op.region, "cutoff")
        self.assertTrue(op.warnings)

    def test_low_vce_warns(self):
        op = solve_fixed(12.0, 1e6, 1_000_000, 100, 0.7)
        self.assertEqual(op.region, "saturation")
        self.assertTrue(op.warnings)

    def test_to_dict_contract(self):
        d = solve(12, 100_000, 22_000, 2200, 1000, 100, 0.7).to_dict()
        for key in ("vb_v", "ve_v", "vc_v", "vce_v", "ib_a", "ic_a",
                    "ie_a", "region", "warnings"):
            self.assertIn(key, d)
```
นำเข้าฟังก์ชันใหม่ด้วย `from dc_bias import solve, solve_fixed, solve_emitter`

- [ ] **Step 2: รัน test ยืนยัน fail**

`python -m unittest tests.test_dc_bias -v` → FAIL `ImportError: cannot import name 'solve_fixed'`

- [ ] **Step 3: แก้ `dc_bias.py`**

- เปลี่ยนฟิลด์ `vth`, `rth` เป็น `float | None = None` และย้ายไปท้าย dataclass (หลัง `region`, `warnings`) — ทุก call ใช้ keyword อยู่แล้ว
- เพิ่ม `to_dict()` คืนคีย์ตาม Step 1
- `solve_fixed`: `ib=(vcc-vbe)/rb`; `ve=0`; ใช้ helper ร่วมคำนวณ `ic, ie, vb, vc, vce` และตรวจ `ib<=0` → cutoff, `vce<=VCE_SAT` → saturation
- `solve_emitter`: `ib=(vcc-vbe)/(rb+(beta+1)*re)`; `ve=ie*re`; ตรวจ region แบบเดียวกับ `solve_fixed`
- `solve()` เดิม **ห้ามเปลี่ยนสูตรหรือลำดับผล** (22–89 คงเดิม ยกเว้นการย้ายฟิลด์)

- [ ] **Step 4: รัน test ให้ผ่าน + verify 17 ตัวเดิม**

`python -m unittest discover -s tests -v` → `Ran 23 tests ... OK`

- [ ] **Step 5: Commit ผ่าน GitHub Desktop**

แจ้ง human partner ให้ Commit ข้อความ `feat: add fixed and emitter bias solvers`

---

### Task 2: เลือกโหมด + ตรวจอินพุตรายโหมดใน Flask

**Files:**
- Modify: `app.py`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `SOLVERS` ไม่มี — ใช้ `solve`, `solve_fixed`, `solve_emitter` และ `.to_dict()` จาก Task 1
- Produces: `parse_form(form, mode) -> tuple[dict, dict]`; `MODES`; `MODE_FIELDS`; `MODE_LABELS`; `SOLVERS`; `render_page(values, units, mode, result=None, errors=None, status=200)`

- [ ] **Step 1: เขียน failing tests**

เพิ่มใน `tests/test_web.py`:
```python
def _mode_payload(self, mode="fixed", **overrides):
    data = {"mode": mode, "vcc": "12", "rc": "2.2", "beta": "100",
            "vbe": "0.70", "rb": "1", "rb_unit": "mohm", "re": "1",
            "re_unit": "kohm", "r1": "100", "r1_unit": "kohm",
            "r2": "22", "r2_unit": "kohm"}
    data.update(overrides)
    return data

def test_fixed_dispatch(self):
    res = self.client.post("/calculate", data=self._mode_payload())
    self.assertEqual(res.status_code, 200)
    self.assertIn("Fixed Bias", res.get_data(as_text=True))
    self.assertIn("1.130 mA", res.get_data(as_text=True))

def test_emitter_dispatch(self):
    res = self.client.post("/calculate", data=self._mode_payload("emitter", re="1"))
    self.assertIn("Emitter Bias", res.get_data(as_text=True))
    self.assertIn("1.026 mA", res.get_data(as_text=True))

def test_divider_unchanged(self):
    res = self.client.post("/calculate", data=self._payload(mode="divider"))
    self.assertIn("9.294", self._results_html(res.get_data(as_text=True)))

def test_rb_unit_conversion(self):
    a = self.client.post("/calculate", data=self._mode_payload(rb="1", rb_unit="mohm"))
    b = self.client.post("/calculate", data=self._mode_payload(rb="1000000", rb_unit="ohm"))
    self.assertEqual(self._results_html(a.get_data(as_text=True)),
                     self._results_html(b.get_data(as_text=True)))

def test_unknown_mode_returns_error(self):
    res = self.client.post("/calculate", data=self._mode_payload("bogus"))
    self.assertEqual(res.status_code, 400)
    self.assertIn("โหมดไม่ถูกต้อง", res.get_data(as_text=True))
    self.assertNotIn('<section class="results"', res.get_data(as_text=True))

def test_fixed_ignores_unused_fields(self):
    res = self.client.post("/calculate", data=self._mode_payload(
        re="abc", r1="abc", r2="abc", re_unit="BAD"))
    self.assertEqual(res.status_code, 200)

def test_emitter_ignores_unused_fields(self):
    res = self.client.post("/calculate", data=self._mode_payload(
        "emitter", r1="abc", r2="abc", r1_unit="BAD"))
    self.assertEqual(res.status_code, 200)

def test_error_does_not_show_results(self):
    res = self.client.post("/calculate", data=self._mode_payload(rb="0"))
    self.assertEqual(res.status_code, 400)
    self.assertNotIn('<section class="results"', res.get_data(as_text=True))

def test_get_mode_selects_form(self):
    res = self.client.get("/?mode=fixed")
    self.assertEqual(res.status_code, 200)
    self.assertIn('name="rb"', res.get_data(as_text=True))
    self.assertNotIn('name="r1"', res.get_data(as_text=True))
```
(เพิ่ม `mode="divider"` เข้า `_payload()` เดิมเพื่อให้ 17 test เดิมยังใช้ route เดิมได้)

- [ ] **Step 2: รัน test ยืนยัน fail**

`python -m unittest tests.test_web -v` → FAIL `AssertionError: 200 != 400` และ `name="rb"` ไม่เจอ

- [ ] **Step 3: แก้ `app.py`**

- `MODES=("divider","fixed","emitter")`, `MODE_FIELDS` ตาม spec, `MODE_LABELS` (`Voltage Divider Bias`, `Fixed Bias`, `Emitter Bias`)
- `FIELD_LABELS` เพิ่ม `"rb": "RB"`, `"rb_unit": ...`
- `DEFAULT_VALUES` เพิ่ม `"rb": "1"`, `DEFAULT_UNITS` เพิ่ม `"rb_unit": "mohm"`
- `parse_form(form, mode)`: ถ้า mode ผิดคืน `({}, {"mode": "โหมดไม่ถูกต้อง"})`; อ่านเฉพาะ `COMMON_FIELDS + MODE_FIELDS[mode]`; ตรวจ finite/บวก/หน่วยเฉพาะฟิลด์ที่อ่าน
- `SOLVERS = {"divider": solve, "fixed": solve_fixed, "emitter": solve_emitter}`
- `index()` อ่าน `request.args.get("mode", "divider")` ตรวจโหมด แล้ว `render_page(..., mode=mode)`
- `calculate()` อ่าน `request.form.get("mode", "")`, เรียก `SOLVERS[mode](**values_si).to_dict()` เมื่อไม่มี error; ข้อผิดพลาด → `result=None, status=400`
- `render_page` ส่ง `mode`, `mode_labels=MODE_LABELS`, `resistor_specs=[(f, label, f+"_unit") for f in MODE_FIELDS[mode]]` ให้ template

- [ ] **Step 4: รันทุก test**

`python -m unittest discover -s tests -v` → `Ran 32 tests ... OK`

- [ ] **Step 5: Commit ผ่าน GitHub Desktop**

ข้อความ `feat: select bias mode and validate per-mode inputs`

---

### Task 3: ฟอร์มเลือกโหมด + แสดงผลตามโหมด

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css` (เพิ่ม `.mode-form`)
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `mode`, `mode_labels`, `resistor_specs`, `values`, `units`, `result(dict)`, `display`, `errors` จาก Task 2
- Produces: หน้าเว็บที่มี select `name="mode"`, ปุ่ม "เปลี่ยนวงจร", ช่อง RB/RE ตามโหมด, heading บอกโหมด

- [ ] **Step 1: เขียน failing tests**

เพิ่มใน `tests/test_web.py`:
```python
def test_mode_selector_present(self):
    html = self.client.get("/").get_data(as_text=True)
    self.assertIn('id="mode"', html)
    self.assertIn("เปลี่ยนวงจร", html)

def test_fixed_form_hides_divider_fields(self):
    html = self.client.get("/?mode=fixed").get_data(as_text=True)
    self.assertIn('name="rb"', html)
    self.assertNotIn('name="r1"', html)
    self.assertNotIn('name="r2"', html)

def test_result_shows_selected_mode(self):
    html = self.client.post("/calculate", data=self._mode_payload(
        "emitter")).get_data(as_text=True)
    self.assertIn("Emitter Bias", self._results_html(html))
```

- [ ] **Step 2: รัน test ยืนยัน fail**

`python -m unittest tests.test_web -v` → FAIL `AssertionError: 'id="mode"' not found`

- [ ] **Step 3: แก้ template/CSS**

- เปลี่ยน eyebrow เป็น `Lab 03`; subtitle แสดง `mode_labels[mode]`
- เพิ่ม GET form แยกด้านบน: `<select id="mode" name="mode">` loop `modes` (ส่งมาจาก app) + ปุ่ม `เปลี่ยนวงจร`; แสดง `errors.mode`
- ฟอร์มคำนวณ: hidden `mode`; ช่อง common `vcc, rc, beta, vbe`; loop `resistor_specs` แสดง input + select หน่วยตามเดิม
- ส่วน results: heading มี `mode_labels[mode]`; badge/table/warnings คงเดิมใช้อย่างเดิมได้เลยเพราะ `display` มาจาก dict แล้ว
- CSS: `.mode-form{display:flex;gap:8px;align-items:end;margin-bottom:16px}` + `.mode-form select{flex:1}`

- [ ] **Step 4: รันทุก test**

`python -m unittest discover -s tests -v` → `Ran 35 tests ... OK`

- [ ] **Step 5: Commit ผ่าน GitHub Desktop**

ข้อความ `feat: add mode selector to form`

---

### Task 4: ตรวจ A1–A5 ผ่าน Browser + อัปเดตเอกสาร

**Files:**
- Modify: `docs/validation.md`, `README.md`, `docs/reflection.md`

**Interfaces:**
- Consumes: A1–A5 values ใน Spec; เว็บที่รันที่ `http://127.0.0.1:5000/`
- Produces: ตาราง A1–A5 พร้อมวิธีตรวจ `OpenCode Browser`, สถานะ PASS/FAIL, หลักฐานข้อความจากหน้าเว็บ

- [ ] **Step 1: โหลด browser skill แล้วเปิดเว็บ**

ใช้ skill `browser` ก่อนเรียก tool; เปิด `http://127.0.0.1:5000/` อ่าน snapshot; restart Flask ถ้า port 5000 ไม่ listen

- [ ] **Step 2: รัน A1–A5 จริง**

สำหรับแต่ละกรณี: เลือกโหมด → กด "เปลี่ยนวงจร" → กรอกเฉพาะช่องที่ใช้ → กด Calculate → อ่าน snapshot ใหม่ทุกครั้ง (ห้ามใช้ผลรอบก่อน) → บันทึก IC/VCE/ข้อความ error

- [ ] **Step 3: เขียนผลลง `docs/validation.md`**

ตารางคอลัมน์: กรณี | อินพุต | คาดหมาย | เห็นจริง | วิธีตรวจ | สถานะ | หลักฐาน; ระบุค่าอิสระที่คำนวณจากสมการ; ถ้า FAIL ให้แก้แล้วรันซ้ำและบันทึกก่อน–หลัง

- [ ] **Step 4: อัปเดต `README.md` / `docs/reflection.md`**

README: วิธีเลือกโหมด + ตัวอย่าง A2/A3; reflection: สิ่งที่ตรวจในโค้ดที่ AI เขียน, การแปลงหน่วย, บทบาท MCP (client/server) และเหตุผลที่ใช้ OpenCode Browser แทน Playwright MCP (Node.js ไม่มีในเครื่อง)

- [ ] **Step 5: รัน test รอบสุดท้าย + verify remote**

`python -m unittest discover -s tests -v` → OK; `git status --short` ต้องไม่มีไฟล์ที่ลืม; แจ้ง human partner ให้ Commit + Push ผ่าน GitHub Desktop แล้วส่ง URL + commit SHA

---

## Final verification (หลัง all tasks)
- `python -m unittest discover -s tests -v` → OK (ไม่มี test เดิมหาย)
- Flask `GET /` 200, `POST /calculate` ครบ 3 โหมด
- ผล Divider ยังตรง 1.942 / 1.242 / 9.294 / 8.052 / 1.230
- `git status` clean หลัง human partner commit/push
