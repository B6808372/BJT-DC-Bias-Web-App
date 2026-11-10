# Validation — BJT DC Bias Web App

เอกสารนี้บันทึกการคำนวณอ้างอิงด้วยมือ ผลทดสอบอัตโนมัติ และผลตรวจผ่าน HTTP จริง
สำหรับค่าตัวอย่างในเอกสาร Lab 02

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

```
test_kcl_holds (test_dc_bias.TestActiveRegion) ... ok
test_reference_example (test_dc_bias.TestActiveRegion) ... ok
test_cutoff_when_vth_below_vbe (test_dc_bias.TestOutsideActiveRegion) ... ok
test_saturation_when_vce_below_sat (test_dc_bias.TestOutsideActiveRegion) ... ok
test_cutoff_badge_and_warning (test_web.TestCalculate) ... ok
test_empty_field_shows_error (test_web.TestCalculate) ... ok
test_invalid_unit_shows_error (test_web.TestCalculate) ... ok
test_non_finite_values_are_rejected (test_web.TestCalculate) ... ok
test_non_numeric_keeps_typed_value (test_web.TestCalculate) ... ok
test_saturation_badge_and_warning (test_web.TestCalculate) ... ok
test_small_current_uses_microamps (test_web.TestCalculate) ... ok
test_unit_conversion_matches_ohms (test_web.TestCalculate) ... ok
test_valid_input_shows_results (test_web.TestCalculate) ... ok
test_vbe_must_be_below_vcc (test_web.TestCalculate) ... ok
test_zero_beta_shows_error (test_web.TestCalculate) ... ok
test_zero_resistance_shows_error (test_web.TestCalculate) ... ok
test_get_index_returns_form (test_web.TestFormPage) ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.041s

OK
```

## 6. ผลตรวจผ่าน HTTP จริง (Flask dev server, port 5000)

| การทดสอบ | ผล |
|---|---|
| `GET /` | 200 — หน้าฟอร์มพร้อมช่องกรอกครบ |
| `POST /calculate` (ค่าตัวอย่าง, หน่วย kΩ) | 200 — พบ 1.942, 1.242, 9.294, 8.052, 1.230 และ "Active Region" ใน HTML |
| `POST /calculate` (R1 = 0) | 400 — แสดงข้อความ "ความต้านทานต้องมากกว่า 0 Ω" |
| `POST /calculate` (R1 = "abc") | 400 — แสดง "กรุณากรอกตัวเลข: R1" และคงค่า `abc` ไว้ในฟอร์ม |
| เปรียบเทียบ kΩ กับ Ω | ผลลัพธ์ในส่วน Results เหมือนกันทุกตัวอักษร |

## 7. ข้อจำกัดที่ยังเหลือ

- เป็นการคำนวณเชิงวิเคราะห์ภายใต้สมมติฐาน β คงที่และ VBE คงที่ ไม่ใช่การจำลอง SPICE
- ค่าที่แสดงในกรณี Cutoff/Saturation มาจากสมการเดิม จึงมี warning กำกับเสมอ
- ยังไม่มีการจำลองอุณหภูมิ ผลของ Early effect หรือความคลาดเคลื่อนของอุปกรณ์
