# Lab 03 Design — หนึ่งเว็บ สามวงจรไบอัส

## Intent
ต่อยอดเว็บ Flask จาก Lab 2 (Voltage Divider Bias เดิม) ให้เลือกได้ 3 โหมด
`divider`, `fixed`, `emitter` โดยผลของ Divider ด้วยอินพุตเดิมต้องคงเดิมทุกตัว
เมื่อรัน Lab 2 ก่อนแก้ได้ `IC = 1.230 mA`, `VCE = 8.052 V`

## Goals
- แยกฟังก์ชันคำนวณ Fixed Bias และ Emitter Bias ใน `dc_bias.py` โดยไม่ย้ายสมการไป HTML
- ผลลัพธ์ทุกโหมดส่งเป็น `dict` ที่มีชื่อคีย์และหน่วยตรงกัน
- `app.py` เลือกฟังก์ชันด้วย `if`/`elif` ตรวจเฉพาะช่องที่โหมดนั้นใช้
- ฟอร์มเลือกโหมดได้โดยไม่ใช้ JavaScript และไม่โชว์ผลค้างจากรอบก่อน
- ตรวจ A1–A5 ผ่าน Browser จริง แล้วบันทึกหลักฐานใน `docs/validation.md`

## Non-goals
SPICE, DC Load Line, AC/Transient, bypass capacitor, Playwright script,
การหาค่าจริงใน Cutoff/Saturation (มีแค่ warning)

## Constraints (จากใบงาน + AGENTS.md)
- ใช้ Python 3.14 / Flask 3.1.3 / unittest เดิม 17 ตัวต้องผ่าน
- หน่วยภายในเป็น SI (V, Ω, A) แปลง kΩ/MΩ→Ω ครั้งเดียวที่ `app.py`
- แสดง VB/VE/VC/VCE เป็น V และ IC เป็น mA
- ทุกครั้งที่เปลี่ยนสมการหรือ validation ต้องเพิ่ม/แก้ test
- คุณ (human partner) เป็นคน Commit/Push ผ่าน GitHub Desktop ผมไม่ git commit เอง
- Node.js ไม่มีในเครื่อง → ใช้ OpenCode Browser Tool แทน Playwright MCP และรายงานวิธีตรวจว่า `OpenCode Browser`

## Approaches
1. **ขยายโมดูลเดิม (เลือก)** — เก็บ `OperatingPoint`, เพิ่ม `to_dict()`,
   เพิ่ม `solve_fixed()` / `solve_emitter()`, ให้ `app.py` เรียกผ่านตาราง `SOLVERS`
   ข้อดี: test เดิม 17 ตัวไม่แตะ, แก้ที่เดียว ข้อเสีย: dataclass ต้องมีฟิลด์ `vth/rth` เป็น optional
2. เขียนโมดulerใหม่ทั้งหมดโดยผลเป็น dict ล้วน — ข้อดี: ตรงตัวตามใบงาน
   ข้อเสีย: ต้องแก้ test เดิม 17 ตัวและเสี่ยงผล Divider เพี้ยน
3. แยกไฟล์ต่อโหมด (`fixed.py`, `emitter.py`) — ข้อเสีย: ไฟล์เล็กเกินไป ซ้ำโครงสร้างเดิม

เลือกข้อ 1 เพราะข้อกำหนดสำคัญที่สุดคือ "Divider ต้องได้ผลเดิม"

## Design
- `dc_bias.py`: `OperatingPoint` เพิ่ม `to_dict()` คืนคีย์
  `vb_v, ve_v, vc_v, vce_v, ib_a, ic_a, ie_a, region, warnings, vth_v, rth_ohm`;
  `vth`/`rth` เป็น optional; `solve()` เดิมเป็น Divider (ไม่เปลี่ยนสูตร);
  เพิ่ม `solve_fixed(vcc, rb, rc, beta, vbe)` และ
  `solve_emitter(vcc, rb, rc, re, beta, vbe)`;
  ตรวจ `ib <= 0` → region `cutoff` + warning, `vce <= 0.2` → region `saturation` + warning
  (Divider ยังใช้เงื่อนไขเดิม `< 0.2` เพื่อรักษาผลเดิม)
- `app.py`: `MODES = ("divider","fixed","emitter")`;
  `MODE_FIELDS = {"divider": ("r1","r2","re"), "fixed": ("rb",),
  "emitter": ("rb","re")}`; `REQUIRED_UNITS = MODE_FIELDS + rc`;
  parse เฉพาะฟิลด์ของโหมด + common (`vcc, rc, beta, vbe`);
  โหมดไม่รู้จัก → 400 พร้อม error ที่ไม่มีผลลัพธ์;
  `GET /?mode=fixed` โหลดฟอร์มใหม่ด้วยช่องของโหมดนั้น;
  POST `/calculate` มี hidden `mode`; เรียก `SOLVERS[mode](...).to_dict()`
- `templates/index.html`: select โหมด + ปุ่ม "เปลี่ยนวงจร" (GET form แยก),
  ฟอร์มคำนวณแสดงเฉพาะ resistor fields ตามโหมด, heading บอกโหมด,
  results ไม่แสดงถ้ามี error
- `tests/`: เพิ่ม test ของสองฟังก์ชัน + dict + mode dispatch + validation รายโหมด
  (คง 17 ตัวเดิมไว้)
- `docs/validation.md`: เพิ่มตาราง A1–A5 พร้อมค่าคาดหมายอิสระและผลจริงจาก Browser

## Values from the handout (คาดหมายก่อนรัน)
| กรณี | IC | VCE |
|---|---|---|
| A1 Divider R1=100k R2=22k RE=1k | 1.230 mA | 8.052 V |
| A2 Fixed RB=1M | 1.130 mA | 9.514 V |
| A3 Emitter RB=1M RE=1k | 1.026 mA | 8.705 V |
| A4 Emitter RB=1M RE=2k | 0.940 mA | 8.033 V (IC ลดลง) |
| A5 Fixed RB=0 | error, ไม่ล่ม, ไม่มีผลค้าง | — |

## Left to the builder
รายละเอียดการเขียนโค้ดอยู่ใน plan; ค่าที่ไม่ได้ระบุให้เลือกตามรูปแบบ Lab 2 เดิม
