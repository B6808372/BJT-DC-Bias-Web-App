# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร BJT Common-Emitter
3 แบบภายใต้แบบจำลอง Forward-Active (β คงที่, VBE คงที่):

- **Voltage Divider Bias** (Lab 02 — ผลเดิมไม่เปลี่ยน)
- **Fixed Bias** (Lab 03)
- **Emitter Bias** (Lab 03)

Lab 04 เพิ่ม **BJT Amplifier Simulator** ที่รัน ngspice จริง (`.op`, `.ac`, `.tran`)
บนวงจร Common-Emitter voltage-divider โดยไม่เปลี่ยนผล Lab 03 เดิม

พัฒนาเป็นส่วนหนึ่งของ ENG29 2121 Lab 02–Lab 04

## โครงสร้างโปรเจกต์

```
.
├── app.py                  # Flask routes + parse ฟอร์ม + แปลงหน่วย + SVG chart coords
├── dc_bias.py              # สมการวิศวกรรม Lab 03 (SI units เท่านั้น)
├── spice_engine.py         # ngspice netlist/run/parse (Lab 04 เท่านั้น)
├── models/
│   └── bjt_teaching.lib    # โมเดลสอน QT_NPN ที่โปรเจกต์กำหนดเอง
├── templates/index.html    # ฟอร์ม + ผลลัพธ์ (Jinja)
├── static/style.css        # layout / responsive
├── tests/
│   ├── test_dc_bias.py     # unit tests ทางวิศวกรรม (Lab 03)
│   ├── test_web.py         # Flask test client (Lab 03)
│   ├── test_spice_engine.py
│   └── test_web_lab04.py
├── requirements.txt
└── docs/
    ├── design-note.md
    ├── validation.md
    ├── reflection.md
    ├── superpowers/        # spec + plan ของ Lab 04
    └── evidence/           # screenshot จาก OpenCode Browser
```

## การติดตั้งและรัน

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

python -m pip install -r requirements.txt
python -m flask --app app run
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/>

### ngspice สำหรับ Lab 04

- ใช้ **ngspice 47 Windows 64-bit** ตัว **console** (`ngspice_con.exe`) — ไม่ใช้ `ngspice.exe`
  (GUI ค้างรอ input ในโหมด batch) และไม่ได้ commit ไบนารีไว้ใน repo
- ดาวน์โหลดจาก <https://ngspice.sourceforge.io/download.html> แล้วแตกซิปไว้นอก repo
- เลือกอย่างใดอย่างหนึ่ง:
  - เพิ่มโฟลเดอร์ `Spice64\bin` ลง `PATH`, หรือ
  - ตั้ง `NGSPICE_CMD` ให้ชี้ไฟล์เช่น
    ```powershell
    $env:NGSPICE_CMD = 'C:\path\to\Spice64\bin\ngspice_con.exe'
    ```
- ลำดับค้นหาคือ `NGSPICE_CMD` → `ngspice_con` ใน `PATH` → `ngspice` ใน `PATH`
- ถ้าไม่พบ engine หน้าเว็บจะแสดง `UNAVAILABLE` (HTTP 200) โดยไม่แสดงผลปลอม
- ตรวจเวอร์ชันได้ด้วย `ngspice_con.exe -v`

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

## Lab 04 — เลือกการวิเคราะห์

ใช้ dropdown **การวิเคราะห์** ด้านบนสุด (GET แบบเดียวกับ **เลือกวงจร**) มี 4 ค่า:

| `analysis` | ความหมาย |
|---|---|
| `bias` | Analytical DC Bias ของ Lab 03 (ค่าเริ่มต้น) |
| `dc` | ngspice `.op` — VB/VE/VC/VCE/IC/IB/IE |
| `ac` | ngspice `.ac dec 10 10 10meg` — กราฟ Gain/Phase และค่าที่ความถี่ที่ขอ |
| `tran` | ngspice `.tran` — กราฟ Vin/Vout และ peak-to-peak รอบสุดท้าย |

ค่าเริ่มต้นของวงจร SPICE (CE voltage-divider, ไม่มี capacitor bypass RE):

| VCC | R1 | R2 | RC | RE | RL | Cin | Cout | Source | Frequency |
|---|---|---|---|---|---|---|---|---|---|
| 12 V | 100 kΩ | 22 kΩ | 2.2 kΩ | 1 kΩ | 10 kΩ | 10 µF | 10 µF | 10 mV peak | 1 kHz |

ทุกช่องต้องเป็นตัวเลขจำนวนจริงที่ **> 0** และมี dropdown หน่วยของตัวเอง
(Ω/kΩ/MΩ, pF/nF/µF, mV/V, Hz/kHz/MHz) — ผิดจะได้ HTTP 400 พร้อม error รายช่อง
ส่วน engine ล่ม/หมดเวลา/ไม่มีไฟล์ output จะได้ HTTP 200 พร้อม `ERROR` หรือ `UNAVAILABLE`
และไม่มีการแสดงผลรอบก่อนค้างอยู่

### ที่มาของผล

- ทุกตัวเลขและกราฟอ่านจากไฟล์ `wrdata` ที่ ngspice เขียนจริงใน temp directory แยกต่อรัน
- ตาราง **Provenance** แสดง executable, เวอร์ชัน, โมเดล, analysis, จำนวน row และค่า input แบบ SI
- โมเดลคือ `QT_NPN` โมเดลสอนที่โปรเจกต์กำหนดเองใน `models/bjt_teaching.lib`
  (**ไม่ได้มาจาก Starter Kit ของอาจารย์**) — ไม่บังคับให้ตรงกับผล Analytical ทุกหลัก
- AC วัด gain เทียบกับ node `IN` ก่อน `Cin`; หากความถี่ที่ขออยู่นอก sweep จะขึ้น
  `not determined in sweep range` แทนการแต่งค่าขึ้นมา
- Transient ใช้ `stop = min(max(5/f, 1 ms), 20 ms)` และ downsample เหลือ ≤1200 จุดต่อสัญญาณ
- ถ้าหน้าต่างจำลองสั้นกว่า 1 รอบ หรือ sample ต่อรอบน้อยกว่า 10 จุด หน้าเว็บจะแสดง note
  แทนป้าย `last cycle` — ค่าที่แสดงยังอ่านจาก sample จริง แต่ไม่เรียกว่าเป็น peak ของรอบสุดท้าย
- กราฟเป็น **inline SVG** ที่ render จากข้อมูลจริงบน Server — ไม่มี JavaScript คำนวณ
  และไม่มี dependency เพิ่มจาก `Flask>=3.0`

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
- โหมด `bias` ไม่มี AC analysis/Bode/Transient — ใช้โหมด `ac`/`tran` ของ Lab 04 แทน
- Lab 04 ยังไม่มี DC load line, parametric sweep, Monte Carlo หรือ temperature sweep
- โมเดล QT_NPN เป็นโมเดลสอน ไม่ใช่ model ของทรานซิสเตอร์รุ่นจริง specific part
