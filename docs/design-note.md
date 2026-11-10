# Design Note — BJT DC Bias Web App (Lab 02)

- **วันที่:** 2026-11-10
- **รายวิชา:** ENG29 2121 Computer Programming for Electrical Engineers (2/2569)
- **สถานะ:** รออนุมัติ Design ก่อนลงมือโค้ด
- **ขนาดงาน:** เล็ก (short design) — 1 คาบปฏิบัติการ, ไม่มี builder review แยก

## 1. Intent และเหตุผล

สร้าง Flask Web Application หลายไฟล์ที่รับค่าอุปกรณ์วงจร BJT Common-Emitter
แบบ Voltage-Divider Bias แล้วให้ Python Backend คำนวณ DC Operating Point จริง
(ไม่ใช่ค่าฮาร์ดโค้ดใน HTML) พร้อม validation, warning นอก Forward-Active,
automated tests และ commit ผ่าน GitHub Desktop ภายในคาบ

## 2. Goals

- เปิดผ่าน `http://127.0.0.1:5000/` ได้ และเห็นฟอร์มอินพุต
- รับ `VCC, R1, R2, RC, RE, β, VBE` โดยตัวต้านทานมี dropdown หน่วย Ω / kΩ / MΩ (ค่าเริ่มต้น kΩ)
- แสดง `VB, VE, VC, VCE, IC` พร้อมหน่วย และแสดง `IB, IE` เพิ่ม
- ตรวจอินพุตผิด (ว่าง / ไม่ใช่ตัวเลข / ≤ 0) แล้วแสดง error ที่อ่านรู้เรื่องโดยหน้าไม่ล้ม
- เตือนเมื่อแบบจำลอง Forward-Active ใช้ไม่ได้ (Cutoff / Saturation)
- มี unit tests ทางวิศวกรรม ≥ 3 และ Flask test client ≥ 1 (ใช้ `unittest`)

## 3. Non-goals

- AC small-signal, Bode plot, Transient, Signal Generator, Overlay animation
- SPICE/ngspice solver, DC load line
- Bias แบบอื่น (Fixed, Emitter), FET
- ระบบ login / ฐานข้อมูล / deploy ขึ้น cloud

## 4. Anti-goals (ถือว่าล้มเหลวแม้โค้ดรันได้)

- ตัวเลข DC Bias ถูกเขียนตายใน HTML หรือคำนวณด้วย JavaScript ฝั่ง client
- เปิดด้วย `file://templates/index.html` แล้วอ้างว่าใช้งานได้
- ไม่ออก warning เมื่อผลอยู่นอก Forward-Active
- Test อ้างว่าผ่านโดยไม่ได้รันจริง

## 5. Constraints

- Python 3.14.2, Flask (latest 3.x), ไม่ใช้ dependency อื่นนอกจาก Flask
- คำสั่งทดสอบตามเอกสาร Lab: `python -m unittest discover -s tests -v`
- เวลารวมในคาบ 180 นาที (ช่วง Build 75 นาที)
- Commit/Push ผ่าน GitHub Desktop (GUI) เท่านั้น
- ห้าม commit `.venv/`, `__pycache__/`, `.env`

## 6. Approaches ที่พิจารณา

| แบบ | ลักษณะ | ข้อดี | ข้อเสีย | สรุป |
|---|---|---|---|---|
| 1 | หน้าเดียว server-rendered: `GET /` ฟอร์ม, `POST /calculate` คำนวณ+render ผล | โค้ดน้อย เทสต์ง่าย ตรง A2 | refresh แล้ว resubmit | **เลือก** |
| 2 | POST + Redirect (PRG) + session | refresh ไม่ resubmit | เพิ่ม state โดยไม่ได้คะแนน | ตัดออก |
| 3 | JSON API + JS fetch | ดูทันสมัย | เพิ่มชั้น JS/เทสต์ เสี่ยงเกินเวลา | ตัดออก |

**เหตุผลที่เลือกแบบ 1:** ตรงเกณฑ์ตรวจรับ A1/A2, เทสต์ผ่าน Flask test client ได้ตรง ๆ,
และเหลือเวลาไปทำ validation/warning ซึ่งมีคะแนนโดยตรง

## 7. การออกแบบ

### 7.1 โครงไฟล์

```
BJT DC Bias Web App/
├── app.py                  # Flask routes + input parsing/unit conversion
├── dc_bias.py              # สมการวิศวกรรมล้วน (SI units only)
├── templates/index.html    # ฟอร์ม + ผลลัพธ์ + error/warning (Jinja)
├── static/style.css        # responsive layout
├── tests/test_dc_bias.py   # engineering unit tests
├── tests/test_web.py       # Flask test client
├── requirements.txt        # Flask
├── README.md               # วิธีติดตั้ง/รัน/ทดสอบ
├── AGENTS.md               # conventions สำหรับ AI
└── docs/
    ├── design-note.md      # เอกสารนี้
    ├── validation.md       # คำนวณอ้างอิง + test log
    └── reflection.md       # สิ่งที่เรียนรู้
```

### 7.2 Data Flow

```
Browser form (GET /)
   → POST /calculate
   → app.py: parse + validate + แปลงหน่วยเป็น SI
   → dc_bias.solve(...) คืน OperatingPoint
   → render templates/index.html (ผล + warning) → Browser
```

### 7.3 การแบ่งความรับผิดชอบ

- `dc_bias.py` — **ไม่รู้จัก** HTML/HTTP/หน่วย kΩ รับค่าอินพุตเป็น SI (V, Ω, A) เท่านั้น
  คืน dataclass `OperatingPoint` (vb, ve, vc, vce, ib, ic, ie, region, warnings)
- `app.py` — อ่าน `request.form`, แปลงหน่วย (Ω/kΩ/MΩ → Ω), เก็บ error เป็น dict,
  เรียก `solve()`, ส่งต่อ template, ตั้ง HTTP status
- `templates/index.html` — แสดงผลเท่านั้น (ไม่ฝังสมการ), คงค่าที่ผู้ใช้กรอกไว้เมื่อ error
- `static/style.css` — หน้าตา/ responsive

### 7.4 การรับหน่วย (Unit handling)

| ช่อง | ชนิด | หน่วย | ค่าเริ่มต้น |
|---|---|---|---|
| VCC | number | V (คงที่) | 12 |
| R1, R2, RC, RE | number + select | Ω / kΩ / MΩ | 100 kΩ / 22 kΩ / 2.2 kΩ / 1 kΩ |
| β | number | ไม่มีหน่วย | 100 |
| VBE | number | V (คงที่) | 0.70 |

ตัวคูณ: Ω = 1, kΩ = 1e3, MΩ = 1e6 — แปลงที่ `app.py` ก่อนเรียก `solve()`

### 7.5 สมการ (Forward-Active, β คงที่, VBE คงที่)

```
VTH = VCC * R2 / (R1 + R2)
RTH = R1 * R2 / (R1 + R2)
IB  = (VTH - VBE) / (RTH + (β + 1) * RE)
IC  = β * IB
IE  = (β + 1) * IB
VE  = IE * RE
VB  = VE + VBE
VC  = VCC - IC * RC
VCE = VC - VE
```

### 7.6 Validation (ตรวจทุกช่องพร้อมกัน)

| เงื่อนไข | ข้อความ |
|---|---|
| ช่องว่าง / ไม่ใช่ตัวเลข | "กรุณากรอกตัวเลข" + ชื่อช่อง |
| VCC ≤ 0 | "VCC ต้องมากกว่า 0 V" |
| R1, R2, RC, RE ≤ 0 | "ความต้านทานต้องมากกว่า 0 Ω" |
| β ≤ 0 | "β ต้องมากกว่า 0" |
| VBE < 0 หรือ VBE ≥ VCC | "VBE ต้องอยู่ระหว่าง 0 ถึง VCC" |
| หน่วยไม่ถูกต้อง | "หน่วยไม่ถูกต้อง" (whitelist Ω/kΩ/MΩ) |

- อินพุตผิด → render หน้าเดิมพร้อม error, **HTTP 400**, คงค่าที่กรอกไว้
- ไม่มี exception หลุดออกไปยังผู้ใช้

### 7.7 Region และ Warning

ค่าคงที่ `VCE_SAT = 0.2 V` (ระบุในเอกสาร)

| เงื่อนไข | Region | การแสดงผล |
|---|---|---|
| VTH ≤ VBE | Cutoff | IB=IC=IE=0, VE=0, VB=VTH, VC=VCC, VCE=VCC + warning "แบบจำลอง Forward-Active ใช้ไม่ได้: VTH ≤ VBE (Cutoff)" |
| VCE < VCE_SAT | Saturation | แสดงค่าที่คำนวณได้ + warning "VCE ต่ำกว่า VCE(sat) — ผลไม่อยู่ใน Forward-Active" |
| อื่น ๆ | Active | แสดงผลปกติ + ป้าย "Active Region" |

> หมายเหตุ: ค่าที่แสดงในกรณี Cutoff/Saturation เป็นผลจากสมการภายใต้สมมติฐานเดิม
> จึงต้องมี warning กำกับเสมอ ไม่รายงานว่าเป็นคำตอบที่แม่นยำ

### 7.8 การแสดงผล

- ตารางผลลัพธ์: VB, VE, VC, VCE (V), IC, IB, IE (mA หรือ µA ตามขนาด)
- ป้าย Region (เขียว = Active, ส้ม = Warning)
- ปัดทศนิยม 3 ตำแหน่งตอนแสดง แต่คำนวณด้วยความละเอียดเต็ม

## 8. Test Plan

**tests/test_dc_bias.py** (unittest)
1. ค่าตัวอย่าง Lab (12 V, 100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ, β=100, VBE=0.70) → VB≈1.942, VE≈1.242, VC≈9.294, VCE≈8.052, IC≈1.230 mA (tolerance 1e-3)
2. KCL: IE ≈ IB + IC
3. Cutoff (เช่น R2 เล็กมากจน VTH < VBE) → region = cutoff + warning
4. Saturation (RC ใหญ่ / RE เล็ก) → region = saturation + warning

**tests/test_web.py** (Flask test client)
1. `GET /` → 200 และมี input name ครบ
2. `POST /calculate` ค่าถูกต้อง → 200 และ HTML มีค่าที่คำนวณ (ไม่ใช่ค่าฮาร์ดโค้ด)
3. `POST /calculate` R1=0 → 400 + ข้อความ error
4. `POST /calculate` ค่าไม่ใช่ตัวเลข → 400 + ข้อความ error
5. หน่วย kΩ → ผลตรงกับกรอกเป็น Ω (คูณ 1000)

## 9. Acceptance Mapping

| เกณฑ์ | ครอบด้วย |
|---|---|
| A1 GET / | route `GET /` + test 1 |
| A2 POST คำนวณจริง | `POST /calculate` → `dc_bias.solve()` + test 2 |
| A3 Engineering Reference | test 1 + `docs/validation.md` |
| A4 Validation | §7.6 + test 3, 4 |
| A5 Outside Active Region | §7.7 + test 3, 4 (unit) |
| A6 Unit + HTTP Tests | §8 (≥3 + ≥1) |
| A7 GitHub Reproducibility | README + requirements.txt + commit ผ่าน GitHub Desktop |

## 10. สิ่งที่เหลือให้ผู้สร้างตัดสินใจ

- โทนสี/ฟอนต์/ระยะห่างของ CSS (ใช้ palette น้ำเงิน-เทาตามธีมรายวิชา)
- ถ้อยคำภาษาไทยของ label/ข้อความ warning (ความหมายตาม §7.6–7.7)
- ค่า tolerance ของ test (เริ่มที่ 1e-3 relative)
- การจัดวางตารางผลลัพธ์ (2 คอลัมน์บนจอใหญ่, 1 คอลัมน์บนมือถือ)
