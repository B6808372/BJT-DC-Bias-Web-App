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

ผลรอบสุดท้ายหลังเพิ่ม Lab 04 และแก้ผล reviewer:

```
Ran 76 tests

OK
```

แยกเป็น 37 test ของ Lab 03 (17 เดิมของ Lab 02 + 6 สมการใหม่ + 14 ชั้น Flask)
+ 26 test ของ `spice_engine.py` + 13 test ของชั้น Flask/presentation Lab 04
(netlist, parser, radian fix, finite-value guard, transient-window note,
boundary app→engine, error policy, SVG, Review Focus coverage)

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

## 8. ข้อจำกัดของโหมด Analytical (`bias`, Lab 03)

- เป็นการคำนวณเชิงวิเคราะห์ภายใต้สมมติฐาน β คงที่และ VBE คงที่ ไม่ใช่การจำลอง SPICE
- ค่าที่แสดงในกรณี Cutoff/Saturation มาจากสมการเดิม จึงมี warning กำกับเสมอ
- ยังไม่มีการจำลองอุณหภูมิ ผลของ Early effect หรือความคลาดเคลื่อนของอุปกรณ์
- หากต้องการ SPICE ให้ใช้โหมด `dc` / `ac` / `tran` ในข้อ 9

## 9. Lab 04 — BJT Amplifier Simulator (ngspice จริง)

### สภาพแวดล้อมที่ใช้ตรวจ

- Engine: `ngspice_con.exe` (console) จาก ngspice 47 Windows 64-bit
  ตั้งค่าด้วย `$env:NGSPICE_CMD = 'C:\Users\B6808372\AppData\Local\Temp\opencode\ngspice\Spice64\bin\ngspice_con.exe'`
  ไบนารีอยู่นอก repo และไม่ได้ commit
- Banner ที่อ่านจาก `ngspice_con.exe -v` (ตัวอักษรตามที่พิมพ์จริง):

```
******
** ngspice-47 : Circuit level simulation program
** Compiled with KLU Direct Linear Solver
** The U. C. Berkeley CAD Group
** Copyright 1985-1994, Regents of the University of California.
** Copyright 2001-2026, The ngspice team.
** Please get your ngspice manual from https://ngspice.sourceforge.io/docs.html
** Please file your bug-reports at https://ngspice.sourceforge.io/bugrep.html
```

- โมเดล: `models/bjt_teaching.lib`, `.model QT_NPN NPN(Is=1e-14 Bf=200 Vaf=100 Cje=4.493p Mje=0.2593 Vje=0.75 Cjc=3.638p Mjc=0.3085 Vjc=0.75 Tf=301.2p Rb=10 Rc=1)`
  — **โมเดลสอนที่โปรเจกต์กำหนดเอง ไม่ใช่ Starter Kit ของอาจารย์**
- วิธีตรวจทั้งหมด: **OpenCode Browser** (เครื่องนี้ไม่มี `node`/`npx` จึงไม่ได้ใช้ Playwright MCP
  และไม่ขออ้างว่าเป็นผล Playwright) — `Navigate → Snapshot → Select/Fill → Click → Snapshot →
  Read Values → Compare → Screenshot`; อ่าน HTTP status จาก `browser.network.list`
- หลักฐานกราฟตรวจจากความยาว/ค่าของ `<polyline points>` และตาราง Provenance
  ไม่ใช้ screenshot เพียงอย่างเดียวในการอ้างค่าทางวิศวกรรม

### ผล B1–B9

| Case | Expected (จากใบงาน) | Observed | Evidence | Method | Status |
|---|---|---|---|---|---|
| B1 · Regression | เปิด Fixed / Emitter / Divider แล้วกรอกชุดค่าจาก Lab 3 ผลต้องตรงค่าอ้างอิงและสลับโหมดได้ | Fixed: IC 1.130 mA, VCE 9.514 V · Emitter: 1.026 mA, 8.705 V · Divider: 1.230 mA, 8.052 V ทั้ง 3 อัน `Active Region` | DOM: `DC Bias Results — Fixed/Emitter/Voltage Divider Bias` พร้อมแถวค่าดังกล่าว; ไม่มี error | OpenCode Browser — เปลี่ยน `mode` แบบ GET, fill ค่า, กด `Calculate DC Bias`, อ่าน DOM หลัง submit | PASS |
| B2 · DC SPICE | Run DC แล้วแสดง VB/VE/VC/VCE/IC จาก ngspice output พร้อม Model และ Run Status | `Success`; VB 2.048 V, VE 1.386 V, VC 8.965 V, VCE 7.580 V, IC 1.380 mA, IB 6.453 µA, IE −1.386 mA; Model `QT_NPN teaching model`; `SPICE rows 1` | ตาราง `SPICE Results — SPICE · DC Operating Point` + Provenance `ngspice-47`, path ไฟล์โมเดล, `Analysis dc`; `POST /calculate → 200` (58–150 ms) | OpenCode Browser — เลือก `analysis=dc`, fill ชุดค่าตั้งต้น, กด `Run ngspice DC` | PASS |
| B3 · Change RE | เปลี่ยน RE เพียงค่าเดียวแล้ว Run ซ้ำ Operating Point ต้องเปลี่ยน ไม่ใช่ค่าค้าง | RE 1 kΩ → VB 2.048 V, IC 1.380 mA, VCE 7.580 V; เปลี่ยนเป็น 2 kΩ → VB 2.103 V, VE 1.459 V, VC 10.403 V, VCE 8.944 V, IC 726.006 µA | Provenance `re=1000` → `re=2000` ในรันที่ต่างกัน; ตารางผลต่างกันทั้ง 7 แถว; field อื่นไม่ได้แตะ | OpenCode Browser — แก้ `re` จาก `1` เป็น `2` (หน่วย kΩ เดิม), submit ซ้ำ, อ่าน DOM หลังโหลดจริง | PASS |
| B4 · AC | Run AC แล้วดู Bode: frequency axis, gain magnitude, phase พร้อมหน่วยและค่าจาก Run จริง | `Frequency 1000 Hz`, `Gain 4.91 dB`, `Phase -179.9°`; axis `Frequency (Hz)`, `Gain (dB)` และ `Phase (°)` ด้านขวา; marker `4.91 dB @ 1000 Hz`; gain/phase polyline คนละ 61 จุด, `SPICE rows 61` | DOM: `.chart-line` และ `.chart-line-phase` คนละ 61 จุด, `.chart-tick-phase` = `-180°/0°/180°`, `.chart-title-phase` = `Phase (°)`; raw ngspice แถว `1.00000000e+03 ... 1.76045151e-02 ... -3.13936455e+00` ให้ 20·log10(1.76045)=4.91 dB และ −179.9° ตรงกัน; เปลี่ยน input เป็น 24 V / RE 470 Ω / 25 mV / 2 kHz → marker `-12.34 dB @ 1995.26 Hz`, ticks `1°/50°/99°` | OpenCode Browser — `analysis=ac`, submit รันจริง 2 ชุด, วัด DOM/polyline/phase ticks และเทียบกับ log จากรันจริง | PASS |
| B5 · Transient | Run `.tran` ที่ 10 mV peak, 1 kHz เห็น Vin/Vout ตามเวลา มีป้ายเวลา/แรงดัน และสัญญาณกลับเฟส | input `10 mV`, `1 kHz`; `Vout peak-to-peak 0.035 V`, `peak 0.018 V`, `Phase relationship inverted`; axis `0.00`–`5.00` ms และ `Voltage (V)`; 2 polyline × 1200 จุด, `SPICE rows 2008` | `docs/evidence/b5-transient-desktop.png`; SVG caption `measured from ngspice samples`, Provenance `source_amp_v=0.01, source_freq_hz=1000` | OpenCode Browser — `analysis=tran`, ตรวจค่า input ก่อน submit, อ่าน DOM/กราฟ, เก็บ screenshot | PASS |
| B6 · Change Source | เปลี่ยน Amplitude หรือ Frequency แล้ว Run ซ้ำ Waveform ต้องเปลี่ยน ไม่ใช่กราฟ hard-code | amplitude 10 → 30 mV: `Vout pp 0.035 → 0.106 V`, `peak 0.018 → 0.053 V`; fixture `source_amp_v=0.01 → 0.03`; จุด polyline ของ Vin และ Vout เปลี่ยนทั้งชุด | เปรียบเทียบ 160 อักขระแรกของ `<polyline points>` ก่อน/หลัง (ต่างกัน) + ตาราง Provenance | OpenCode Browser — แก้เฉพาะ `source_amp`, submit ซ้ำ, วัด DOM ก่อน/หลัง | PASS |
| B7 · Invalid / Fail | ใส่ RE=0 หรือ engine ไม่พร้อม ต้องแจ้ง Error ไม่ค้าง ไม่ส่งผลสำเร็จปลอม | RE=0 → `RE ต้องมากกว่า 0`, ไม่มีผล/SVG/Success, `POST → 400`; รันเซิร์ฟเวอร์ที่ 2 โดยไม่ตั้ง `NGSPICE_CMD` → `UNAVAILABLE`, `ngspice executable not found`, ไม่มีผล/SVG/Success, `POST → 200` | `browser.network.list` เห็น status 400 และ 200 ตามลำดับ; DOM ไม่มี `.spice-results` และไม่มีคำว่า `Success` | OpenCode Browser — กรอก `re=0` กด run; เปิด Flask port 5001 ที่ไม่มี engine กด run | PASS |
| B8 · UI | เปิด Desktop/Phone viewport และเปลี่ยนโหมด กราฟ/หน่วย/ปุ่มอ่านง่าย ไม่มีเนื้อหาสำคัญถูกตัด | Desktop 1296 px: ไม่มี overflow; viewport แคบ 390 px (iframe ที่ `matchMedia('(max-width: 640px)')` เป็น true): `scrollWidth 375 ≤ 390`, `.form-grid` 1 column `321px`, SVG กราฟ/วงจรกว้าง 321 px, ไม่มี element ที่ `right > 391`; ผล AC ยัง `Success` | `docs/evidence/b8-desktop-ac.png`, `docs/evidence/b8-mobile-390-ac.png`; วัด `getBoundingClientRect()`, `gridTemplateColumns` และ `scrollWidth` ใน DOM จริงหลังเพิ่มแกน phase | OpenCode Browser — ใช้ iframe กว้าง 390 px แทน device emulation (เครื่องมือไม่มี viewport tool) | PASS* |
| B9 · Circuit values | ภาพวงจรต้องโชว์ค่าที่ผู้ใช้กรอก ไม่ใช่ค่าฝังไว้ และไม่โชว์ผลจำลองเป็นค่าชิ้นส่วน | default: `12 V`, `10 mV · 1 kHz`, `10 µF`, `100 kΩ`, `22 kΩ`, `2.2 kΩ`, `1 kΩ`, `10 µF`, `10 kΩ`; หลังแก้ฟอร์ม: `24 V`, `25 mV · 2 kHz`, `100 nF`, `47 kΩ`, `22 kΩ`, `2.2 kΩ`, `470 Ω`, `10 µF`, `10 kΩ` | DOM `.circuit-value` เปลี่ยนตาม input; Provenance `fixture (SI)` เปลี่ยน `vcc=12, r1=100000, re=1000, cin=1e-05, source_amp_v=0.01, source_freq_hz=1000` → `vcc=24, r1=47000, re=470, cin=1e-07, source_amp_v=0.025, source_freq_hz=2000` | OpenCode Browser — อ่าน `.circuit-value` ก่อน/หลัง submit พร้อมตาราง Provenance จากรัน ngspice จริง | PASS |

\* หมายเหตุ B8: OpenCode Browser ไม่มีเครื่องมือปรับ viewport ของ-tab จึงใช้ iframe กว้าง 390 px
ที่มี media query แบบมือถือทำงานจริง ไม่ใช่ device emulation โมเดลที่เขียนเอกสารนี้ไม่สามารถ
เปิดดูพิกเซลของ screenshot ได้ จึงตัดสิน “ไม่ถูกตัด” จาก geometry/CSS ที่วัดใน DOM แทน
และแนบ screenshot ไว้ให้ตรวจด้วยมนุษย์ — ไม่ได้อ้างว่าดูภาพด้วยตนเอง

### ข้อสังเกตและการแก้ระหว่างตรวจรับ

- ตรวจผ่าน HTTP จริงด้วย Flask test client ก่อน Browser พบ 3 bug ที่ test แบบ mock ไม่เจอ:
  (1) key `source_amp`/`source_freq` ไม่ตรง `source_amp_v`/`source_freq_hz`,
  (2) `.include` ตัด path ที่มีช่องว่าง, (3) `vp()` ของ ngspice เป็น **radian** ไม่ใช่องศา
  (พิสูจน์ด้วย RC low-pass ที่ fc ให้ −0.785398 ≈ −π/4 แทน −45°) — แก้พร้อมเพิ่ม regression test
- B8 พบกราฟล้นใน viewport แคบ (`scrollWidth 752 > 390`) เพราะ grid `1fr` มี auto minimum
  และตาราง Provenance มี string ยาวไม่ตัด — แก้เป็น `minmax(0, 1fr)` + `table-layout: fixed`
  และ `overflow-wrap: anywhere`; วัดซ้ำแล้ว `scrollWidth 375 ≤ 390`
- `IE` ติดลบเพราะ ngspice ใช้ conventions กระแสเข้าขา (current into terminal) หน้าเว็บมีคำอธิบาย
  ไม่ได้แก้เครื่องหมายของค่าดิบ
- AC และ Transient ไม่ควรบังคับให้ตรงกับ Analytical ทุกหลัก เพราะโมเดล QT_NPN มี `Is/Bf/Vaf/Cje/Cjc/Tf`
 ของตัวเอง; validation เปรียบเทียบแต่ละแหล่งตาม contract ของตัวเอง
- หลัง reviewer ตรวจทั้ง branch พบ 2 Important: token `nan`/`inf` ผ่าน `float()` แล้วโชว์เป็น `nan V`/`nan dB`,
  และป้าย `last cycle` ผิดเมื่อหน้าต่างสั้นกว่า 1 รอบ (f < 50 Hz) หรือ sample ต่อรอบน้อยเกินไป —
  แก้ด้วย `math.isfinite` ใน `parse_wrdata` และ `measurement_note` ใน `parse_tran` + เปลี่ยนป้ายเป็น
  `Vout peak (available window)` พร้อมข้อความอธิบาย; `stop = min(max(5/f, 1 ms), 20 ms)` ยังตาม spec เดิม
- รัน ngspice 47 ซ้ำหลังแก้ด้วย fixture เดิม: DC IC 0.00137979504 A (rows 1), AC 4.912481 dB / −179.872°
  (rows 61), TRAN pp 0.0352079097 V พร้อม `measurement_note=''` (rows 2008)
  ที่ 1 kHz — ค่าที่บันทึกใน B2–B5 ไม่เปลี่ยน
