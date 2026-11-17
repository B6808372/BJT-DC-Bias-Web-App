# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร BJT Common-Emitter
3 แบบภายใต้แบบจำลอง Forward-Active (β คงที่, VBE คงที่):

- **Voltage Divider Bias** (Lab 02 — ผลเดิมไม่เปลี่ยน)
- **Fixed Bias** (Lab 03)
- **Emitter Bias** (Lab 03)

พัฒนาเป็นส่วนหนึ่งของ ENG29 2121 Lab 02–Lab 03

## โครงสร้างโปรเจกต์

```
.
├── app.py                  # Flask routes + parse ฟอร์ม + แปลงหน่วย
├── dc_bias.py              # สมการวิศวกรรม (SI units เท่านั้น)
├── templates/index.html    # ฟอร์ม + ผลลัพธ์ (Jinja)
├── static/style.css        # layout / responsive
├── tests/
│   ├── test_dc_bias.py     # unit tests ทางวิศวกรรม
│   └── test_web.py         # Flask test client
├── requirements.txt
└── docs/
    ├── design-note.md
    ├── validation.md
    └── reflection.md
```

## การติดตั้งและรัน

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/>

> ต้องรันผ่าน Flask Server เท่านั้น — การดับเบิลคลิกเปิด `templates/index.html`
> จะไม่มีการคำนวณเพราะไม่มี Python Backend

## การเลือกวงจร

ใช้ dropdown **เลือกวงจร** ด้านบนฟอร์ม แล้วกด **เปลี่ยนวงจร** (เป็น GET form ไม่ใช้ JavaScript)
จากนั้นกรอกเฉพาะช่องที่โหมดนั้นใช้:

| โหมด | ช่องที่ต้องกรอก |
|---|---|
| Voltage Divider Bias | VCC, R1, R2, RC, RE, β, VBE |
| Fixed Bias | VCC, RB, RC, β, VBE |
| Emitter Bias | VCC, RB, RC, RE, β, VBE |

ค่าที่พิมพ์ผิดจะได้ HTTP 400 พร้อม error รายช่อง และจะไม่โชว์ผลลัพธ์จากรอบก่อน

> การกด **เปลี่ยนวงจร** จะโหลดฟอร์มใหม่ด้วยค่าตั้งต้นของโหมดนั้น (ไม่คงค่าที่กรอกค้างไว้)
> เพื่อให้ช่องที่ใช้ตรงกับวงจรเสมอ — กรอกค่าที่ต้องการหลังเปลี่ยนโหมดได้เลย

## การทดสอบ

```bash
python -m unittest discover -s tests -v
```

## พารามิเตอร์

| อินพุต | หน่วย |
|---|---|
| VCC | V |
| R1, R2, RB, RC, RE | Ω / kΩ / MΩ (เลือกได้ต่อช่อง; ใช้ตามโหมด) |
| β (hFE) | ไม่มีหน่วย |
| VBE | V |

| เอาต์พุต | หน่วย |
|---|---|
| VB, VE, VC, VCE | V |
| IC, IB, IE | เลือกอัตโนมัติเป็น mA / µA / nA ให้ตัวเลขอยู่ในช่วงอ่านง่าย |

## ค่าตัวอย่าง

VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V (ค่าตั้งต้นของฟอร์ม)

| โหมด | อินพุตเพิ่ม | IC | VCE |
|---|---|---|---|
| Divider | R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | 1.230 mA | 8.052 V |
| Fixed | RB=1 MΩ | 1.130 mA | 9.514 V |
| Emitter | RB=1 MΩ, RE=1 kΩ | 1.026 mA | 8.705 V |
| Emitter (A4) | RB=1 MΩ, RE=2 kΩ | 940.100 µA | 8.033 V |

ดูการคำนวณด้วยมือ ผลตรวจ A1–A5 และหลักฐาน Browser ได้ใน `docs/validation.md`

## ข้อจำกัดของแบบจำลอง

- ใช้ Forward-Active Approximation (β คงที่, VBE คงที่) — ไม่ใช่ SPICE
- Divider: ถ้า `VTH ≤ VBE` อยู่ใน Cutoff; ถ้า `VCE < 0.2 V` อยู่ใน Saturation
- Fixed/Emitter: ถ้า `IB ≤ 0` อยู่ใน Cutoff; ถ้า `VCE ≤ 0.2 V` อยู่ใน Saturation
- ค่า Cutoff/Saturation เป็นค่าจากสมการเชิงเส้น มี warning กำกับเสมอ
- ไม่มี AC analysis, Bode plot, Transient หรือ load line ในเวอร์ชันนี้
