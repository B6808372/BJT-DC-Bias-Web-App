# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร BJT Common-Emitter
แบบ **Voltage-Divider Bias** ภายใต้แบบจำลอง Forward-Active (β คงที่, VBE คงที่)

พัฒนาเป็นส่วนหนึ่งของ ENG29 2121 Lab 02

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

## การทดสอบ

```bash
python -m unittest discover -s tests -v
```

## พารามิเตอร์

| อินพุต | หน่วย |
|---|---|
| VCC | V |
| R1, R2, RC, RE | Ω / kΩ / MΩ (เลือกได้ต่อช่อง) |
| β (hFE) | ไม่มีหน่วย |
| VBE | V |

| เอาต์พุต | หน่วย |
|---|---|
| VB, VE, VC, VCE | V |
| IC, IE | mA |
| IB | µA |

## ค่าตัวอย่าง

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

ผลลัพธ์ที่คาดหวัง (ดูการคำนวณด้วยมือใน `docs/validation.md`):

| ปริมาณ | ค่า |
|---|---|
| VB | 1.942 V |
| VE | 1.242 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| IC | 1.230 mA |

## ข้อจำกัดของแบบจำลอง

- ใช้ Forward-Active Approximation (β คงที่, VBE คงที่) — ไม่ใช่ SPICE
- ถ้า `VTH ≤ VBE` วงจรอยู่ใน Cutoff และแบบจำลองนี้ใช้ไม่ได้ → แสดง warning
- ถ้า `VCE < 0.2 V` (VCE(sat)) ผลไม่อยู่ใน Forward-Active → แสดง warning
- ไม่มี AC analysis, Bode plot, Transient หรือ load line ในเวอร์ชันนี้
