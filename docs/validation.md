# Validation — BJT DC Bias Web App

เอกสารนี้บันทึกการคำนวณอ้างอิงด้วยมือ ผลทดสอบอัตโนมัติ ผลตรวจผ่าน HTTP จริง
และผลตรวจผ่าน Browser จริงสำหรับค่าตัวอย่างในเอกสาร Lab 02 และ Lab 03

## 1. ค่าอินพุตอ้างอิง

| พารามิเตอร์ | ค่า | หน่วย SI |
|---|---|---|
| VCC | 12 | 12 V |
| R1 | 100 kΩ | 100 000 Ω |
| R2 | 22 kΩ | 22 000 Ω |
| RC | 2.2 kΩ | 2 200 Ω |
| RE | 1 kΩ | 1 000 Ω |
| β | 100 | — |
| VBE | 0.70 | 0.70 V |

## 2. การคำนวณด้วยมือ (Forward-Active)

```
VTH = VCC × R2 / (R1 + R2)
    = 12 × 22 000 / (100 000 + 22 000)
    = 2.164 V

RTH = R1 × R2 / (R1 + R2)
    = 100 000 × 22 000 / 122 000
    = 18 033 Ω   (18.033 kΩ)

IB  = (VTH − VBE) / (RTH + (β + 1) × RE)
    = (2.164 − 0.70) / (18 033 + 101 × 1 000)
    = 1.464 / 119 033
    = 12.30 µA

IC  = β × IB = 100 × 12.30 µA = 1.230 mA
IE  = (β + 1) × IB = 101 × 12.30 µA = 1.242 mA

VE  = IE × RE = 1.242 mA × 1 000 Ω = 1.242 V
VB  = VE + VBE = 1.242 + 0.70 = 1.942 V
VC  = VCC − IC × RC = 12 − 1.230 mA × 2 200 Ω = 9.294 V
VCE = VC − VE = 9.294 − 1.242 = 8.052 V
```

**ตรวจ Region:** `VTH = 2.164 V > VBE = 0.70 V` (ไม่อยู่ใน Cutoff)
และ `VCE = 8.052 V > VCE(sat) = 0.2 V` → **Active Region** ใช้แบบจำลองได้

## 3. เปรียบเทียบผลคำนวณมือกับผลจากเว็บ

| ปริมาณ | คำนวณมือ | ผลจากเว็บ | ต่าง |
|---|---|---|---|
| VB | 1.942 V | 1.942 V | 0.000 |
| VE | 1.242 V | 1.242 V | 0.000 |
| VC | 9.294 V | 9.294 V | 0.000 |
| VCE | 8.052 V | 8.052 V | 0.000 |
| IC | 1.230 mA | 1.230 mA | 0.000 |
| IB | 12.299 µA | 12.299 µA | 0.000 |
| IE | 1.242 mA | 1.242 mA | 0.000 |

## 4. กรณีทดสอบนอก Forward-Active

| กรณี | อินพุต | ผลที่ได้ | ตรงตามที่ออกแบบ |
|---|---|---|---|
| Cutoff | VCC=12, R1=100k, R2=5k, RC=2.2k, RE=1k, β=100, VBE=0.7 | `VTH = 0.571 V ≤ VBE` → region = cutoff, IB=IC=IE=0, VC=VCC, warning "แบบจำลอง Forward-Active ใช้ไม่ได้" | ✅ |
| Saturation | VCC=12, R1=100k, R2=22k, RC=10k, RE=100, β=100, VBE=0.7 | `VCE ≈ −40.6 V < 0.2 V` → region = saturation, IC ≈ 5.204 mA, warning | ✅ |

## 5. ผลทดสอบอัตโนมัติ

คำสั่ง: `python -m unittest discover -s tests -v`

ผลรอบสุดท้ายหลังเพิ่ม Lab 03:

```
Ran 37 tests

OK
```

แยกเป็น 17 test เดิมของ Lab 02 + 6 test สมการใหม่ (`solve_fixed`, `solve_emitter`,
`to_dict`, RE เพิ่มแล้ว IC ต้องลด, cutoff/saturation warning) + 14 test ของชั้น Flask
(mode dispatch, แปลงหน่วย RB, ละเว้นช่องที่โหมดไม่ใช้, โหมดไม่รู้จักทั้ง GET/POST,
หน่วย RB ผิด, ไม่โชว์ผลค้าง, GET `?mode=` เลือกฟอร์ม, mode selector ในหน้าเว็บ)

## 6. ผลตรวจผ่าน HTTP จริง (Flask dev server, port 5000)

| การทดสอบ | ผล |
|---|---|
| `GET /` | 200 — หน้าฟอร์มพร้อมช่องกรอกครบ |
| `POST /calculate` (ค่าตัวอย่าง, หน่วย kΩ) | 200 — พบ 1.942, 1.242, 9.294, 8.052, 1.230 และ "Active Region" ใน HTML |
| `POST /calculate` (R1 = 0) | 400 — แสดงข้อความ "ความต้านทานต้องมากกว่า 0 Ω" |
| `POST /calculate` (R1 = "abc") | 400 — แสดง "กรุณากรอกตัวเลข: R1" และคงค่า `abc` ไว้ในฟอร์ม |
| เปรียบเทียบ kΩ กับ Ω | ผลลัพธ์ในส่วน Results เหมือนกันทุกตัวอักษร |
| `GET /?mode=fixed` | 200 — เฉพาะช่อง RB/RC และ hidden `mode=fixed` |
| `GET /?mode=emitter` | 200 — เฉพาะช่อง RB/RC/RE |
| `POST /calculate` mode=`fixed`, RB=1 MΩ | 200 — `IC 1.130 mA`, `VCE 9.514 V` |
| `POST /calculate` mode=`emitter`, RB=1 MΩ, RE=1 kΩ | 200 — `IC 1.026 mA`, `VCE 8.705 V` |
| `POST /calculate` mode=`bogus` | 400 — `โหมดไม่ถูกต้อง`, ไม่มีส่วน Results |

## 7. Lab 03 — หนึ่งเว็บ สามวงจรไบอัส (ตรวจผ่าน Browser จริง)

วิธีตรวจ: **OpenCode Browser** (เครื่องนี้ไม่มี Node.js/npx จึงใช้ Browser Tool ของ OpenCode แทน Playwright MCP)
เปิด `http://127.0.0.1:5000/` แล้วกด `Calculate DC Bias` จริง อ่านค่าจาก DOM หลังผลลัพธ์ render ทุกครั้ง
สำหรับ A5 อ่าน HTTP status จาก `browser.network.list`

สมการอ้างอิงที่ใช้คำนวณค่าคาดหมายอย่างอิสระ:
- Fixed: `IB=(VCC−VBE)/RB`, `IC=β·IB`, `VCE=VCC−IC·RC` (VE=0)
- Emitter: `IB=(VCC−VBE)/(RB+(β+1)·RE)`, `VE=(β+1)·IB·RE`, `VCE=VCC−IC·RC−VE`

| กรณี | อินพุต | คาดหมาย (คำนวณอิสระ) | เห็นจริง | วิธีตรวจ | สถานะ | หลักฐาน |
|---|---|---|---|---|---|---|
| A1 Divider | VCC=12, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 | IC 1.230 mA, VCE 8.052 V (ต้องตรง Lab 02) | IC 1.230 mA, VCE 8.052 V, VB 1.942 V, VC 9.294 V | OpenCode Browser | PASS | `DC Bias Results — Voltage Divider Bias`, `Active Region`, table rows `IC 1.230 mA`, `VCE 8.052 V` |
| A2 Fixed | VCC=12, RB=1 MΩ, RC=2.2 kΩ, β=100, VBE=0.70 | IC 1.130 mA, VCE 9.514 V | IC 1.130 mA, VCE 9.514 V, VB 0.700 V, VE 0.000 V | OpenCode Browser | PASS | `DC Bias Results — Fixed Bias`, `Active Region`, `IC 1.130 mA`, `VCE 9.514 V` |
| A3 Emitter | VCC=12, RB=1 MΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 | IC 1.026340 mA, VCE 8.705450 V | IC 1.026 mA, VCE 8.705 V, VE 1.037 V | OpenCode Browser | PASS | `DC Bias Results — Emitter Bias`, `Active Region`, `IC 1.026 mA`, `VCE 8.705 V` |
| A4 Emitter (เปลี่ยน RE เดียว) | เหมือน A3 แต่ RE=2 kΩ | IC 0.940100 mA, VCE 8.032779 V และ IC ต้องลดจาก A3 | IC 940.100 µA (=0.940100 mA), VCE 8.033 V → ลดจาก 1.026 mA | OpenCode Browser | PASS | input `re=2`, `re_unit=kohm`; rows `IC 940.100 µA`, `VCE 8.033 V` |
| A5 Fixed RB=0 | เหมือน A2 แต่ RB=0 | 400, ไม่ล่ม, ไม่มีผลค้าง | HTTP 400, error `ความต้านทานต้องมากกว่า 0 Ω`, ไม่มี `<section class="results">`, RB คง `0` | OpenCode Browser + network.list | PASS | `POST http://127.0.0.1:5000/calculate → 400`; `hasResults=false`; error text ปรากฏในหน้า |

หมายเหตุ
- ตัวเลข A4 แสดงเป็น `µA` เพราะ `format_current()` เลือกหน่วยให้ตัวเลขอยู่ในช่วง 3 หลัก; `940.100 µA` เท่ากับ `0.940100 mA` ตามค่าอิสระ
- ฟอร์มเลือกโหมดตรวจเพิ่มด้วย `GET /?mode=fixed` และ `GET /?mode=emitter` ใน Browser: subtitle เปลี่ยนเป็น `Fixed Bias` / `Emitter Bias` และช่องฟอร์มเปลี่ยนเป็น `RB` / `RB+RE` ตามลำดับ
- Browser Tool บางครั้งค้าง ref หลัง `select`/`fill` จึงใช้ `evaluate` ตั้งค่า input หรือ `requestSubmit()` ในขั้นตอนเลือกโหมด; แอปยังถึง route เดิมและ test client ครอบกรณีนี้แล้ว (`test_get_mode_selects_form`, `test_mode_selector_present`)

## 8. ข้อจำกัดที่ยังเหลือ

- เป็นการคำนวณเชิงวิเคราะห์ภายใต้สมมติฐาน β คงที่และ VBE คงที่ ไม่ใช่การจำลอง SPICE
- ค่าที่แสดงในกรณี Cutoff/Saturation มาจากสมการเดิม จึงมี warning กำกับเสมอ
- ยังไม่มีการจำลองอุณหภูมิ ผลของ Early effect หรือความคลาดเคลื่อนของอุปกรณ์
