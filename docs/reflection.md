# Reflection — Lab 02 และ Lab 03

## สิ่งที่ได้เรียนรู้

### Frontend / Backend / Template
- ไฟล์ `.html` ใน Flask เป็น **Template** ที่ Server นำไป render — ตัวเลข DC Bias ไม่ได้อยู่ใน HTML
  แต่มาจากฟังก์ชัน Python ทุกครั้งที่กด Calculate
- การเปิด `templates/index.html` ด้วย `file://` ไม่ทำให้เกิดการคำนวณ เพราะไม่มี HTTP Request
  ไปถึง Backend และไม่มี Jinja แทนค่า
- การแยก `dc_bias.py` ออกจาก `app.py` ทำให้แก้สมการได้โดยไม่ต้องแตะ HTML และเขียน unit test
  ได้ตรง ๆ โดยไม่ต้องจำลอง HTTP

### HTTP Request / Form
- ฟอร์มคำนวณใช้ `method="post"` ไปที่ `/calculate` — เบราว์เซอร์ส่งค่าเป็น `application/x-www-form-urlencoded`
  แล้ว Flask อ่านด้วย `request.form`
- ฟอร์มเลือกโหมดเป็น GET form แยก (`/` พร้อม `?mode=...`) จึงไม่ต้องเขียน JavaScript
  และลิงก์/URL ของแต่ละวงจรแยกชัดเจน
- การตอบ **400** เมื่ออินพุตผิด ช่วยให้แยกได้ชัดระหว่าง "คำนวณสำเร็จ" กับ "ผู้ใช้กรอกผิด"
  โดยหน้าเว็บยังแสดงผลได้ปกติ ไม่เกิด traceback
- การคงค่าที่ผู้ใช้พิมพ์ไว้ (`value="{{ values.r1 }}"`) สำคัญมาก เพราะถ้าฟอร์มรีเซ็ต
  ผู้ใช้ต้องพิมพ์ใหม่ทุกครั้งที่พิมพ์ผิด

### วิศวกรรมไฟฟ้า
- Voltage-Divider Bias ต้องแปลงเป็น Thevenin ก่อน (`VTH`, `RTH`) จึงจะคำนวณ `IB` ได้
- หน่วยต้องสม่ำเสมอ — ถ้าลืมแปลง kΩ เป็น Ω ผลจะคลาด 1000 เท่า จึงเลือกใช้ dropdown หน่วย
  และมี test เปรียบเทียบ kΩ กับ Ω โดยตรง
- แบบจำลอง Forward-Active ใช้ได้เฉพาะบางช่วง: ถ้า `VTH ≤ VBE` (Divider) หรือ `IB ≤ 0`
  (Fixed/Emitter) ทรานซิสเตอร์อยู่ใน Cutoff และถ้า `VCE` ต่ำกว่า/เท่ากับ `VCE(sat)`
  ผลที่คำนวณได้ไม่มีความหมายทางกายภาพ จึงต้องมี warning ไม่ใช่ปล่อยให้ผู้ใช้เข้าใจผิด
- Fixed Bias หา `IB` จาก `(VCC−VBE)/RB`; Emitter Bias ต้องรวม `(β+1)·RE` เข้าในตัวหาร
  ซึ่งอธิบายว่าทำไมเพิ่ม RE จาก 1→2 kΩ แล้ว IC ตกลง (1.026→0.940 mA)

### กระบวนการทำงานกับ AI
- การกำหนด Design ให้ชัดก่อนเขียนโค้ด (โครงไฟล์, ชื่อฟิลด์, เกณฑ์ validation) ทำให้ตรวจงานง่าย
- TDD ช่วยจับกรณีที่ลืมคิด เช่น ค่าที่ไม่ใช่ตัวเลข หรือหน่วยที่ไม่ถูกต้อง
- ต้องตรวจผลด้วยการคำนวณมือเสมอ ไม่เชื่อตัวเลขที่โปรแกรมแสดงโดยไม่ตรวจ

## Lab 03: สิ่งที่ตรวจในโค้ดที่ AI เขียน

- เปิด `dc_bias.py` แล้วตามว่าสมการอยู่ใน Python เท่านั้น แผนที่/ผลลัพธ์ใน HTML เป็น Jinja `${...}`
  ไม่มีตัวเลขคงที่เช่น `9.294` ฝังอยู่
- ทดสอบว่าฟังก์ชันเดิม `solve()` ยังให้ผล Lab 02 เทเดิมทุกตัว (`test_divider_unchanged`, A1 ใน Browser)
  ก่อนเชื่อฟังก์ชันใหม่ `solve_fixed()` / `solve_emitter()`
- ตรวจเขต validation แยกโหมด: Fixed ไม่ควรสนใจ RE/R1/R2, Emitter ไม่ควรสนใจ R1/R2,
  โหมดแปลกปลอมต้อง 400 และรอบที่กรอกผิดต้องไม่โชว์ผลรอบก่อน
- ตรวจการแปลงหน่วย RB `1 MΩ` กับ `1 000 000 Ω` ต้องให้ผลเหมือนกันทุกตัวอักษร
  ซึ่งยืนยันว่า kΩ/MΩ ถูกคูณครั้งเดียวที่ `app.py` ไม่ใช่ที่ HTML

## MCP และเครื่องมือตรวจ Browser

- **MCP client** คือโปรแกรมที่เรียกใช้ tool (ในที่นี้คือ OpenCode/AI agent ส่วนที่ขอเปิดเบราว์เซอร์)
  **MCP server** คือ process ที่เปิด tool ให้เรียกผ่าน protocol (เช่น Playwright MCP server)
  ทั้งสองเป็นคนละชั้นกับเว็บแอป Flask ของเรา — เว็บไม่ต้องรู้จัก MCP เลย
- ใบงานแนะนำ Playwright MCP แต่เครื่องนี้ไม่มี `node`/`npx` จึงใช้ **OpenCode Browser Tool**
  เป็นเครื่องมือตรวจแทน และบันทึกวิธีตรวจใน `docs/validation.md` ว่า `OpenCode Browser`
- สิ่งที่ทำจริง: เปิด `http://127.0.0.1:5000/`, กด Calculate, อ่าน DOM ด้วย `evaluate`,
  และใช้ `network.list` อ่าน statusCode 400 ของ A5
- พบข้อจำกัดของ Browser Tool คือ ref บางครั้งค้างหลัง `select`/`fill` จึงใช้ `evaluate`
  ตั้งค่า input หรือ `requestSubmit()` เพื่อเลือกโหมด; แอปยังถึง route เดิม
  และมี test client ครอบอยู่แล้ว จึงไม่แก้โค้ดแอปเพื่ออาการของเครื่องมือนี้

## Lab 04: สิ่งที่ได้เรียนรู้จากการต่อ ngspice เข้าเว็บ

### External-process integration

- แยก `spice_engine.py` ออกจาก `app.py` ทำให้ชั้น HTTP ไม่ต้องรู้จัก netlist/CSV เลย
  และยังรักษากฎเดิม: `dc_bias.py` เป็นสมการวิเคราะห์เพียงแหล่งเดียว ส่วน SPICE เป็นอีกแหล่งข้อมูล
- เรียก engine ด้วย argument list, `cwd` เป็น temp directory แยกต่อรัน, มี `timeout`
  และไม่ใช้ `shell=True` — ไฟล์ `wrdata` ที่เกิดขึ้นจึงไม่ปนกันระหว่างรัน
- typed error (`EngineUnavailable`, `EngineRunError`, `EngineTimeout`, `EngineOutputError`)
  ทำให้หน้าเว็บแยกได้ชัดระหว่าง “ผู้ใช้กรอกผิด” (400) กับ “engine ไม่พร้อม/ล่ม” (200 + status)
  และไม่โชว์ผลรอบก่อนค้าง
- TDD กับ mock `subprocess` ผ่านทั้งหมด แต่การรัน ngspice จริงเจออีก 3 bug ที่ mock ไม่ครอบ:
  key ของ amplitude/frequency ไม่ตรงกัน, path `.include` มีช่องว่าง, และ `vp()` เป็น radian
  → สรุปว่าต้องมีทั้ง unit test และ integration test กับ binary จริง

### `.ac` กับ `.tran` ต่างกันอย่างไร

- `.ac` เป็น small-signal frequency sweep: ได้ gain/phase ต่อความถี่ ต้องวัดเทียบ
  source node `IN` ก่อน `Cin` ไม่ใช่เทียบ input หลัง capacitor และต้องบอกว่าความถี่ที่ขอ
  อยู่ในช่วง sweep หรือไม่ แทนการแต่งค่า interpolation ขึ้นมา
- `.tran` เป็น time-domain: เห็นรูปคลื่นจริง วัด peak-to-peak จากรอบสุดท้าย และดูทิศทางเฟส
  จากสัญญาณจริง แต่จะบอก “−180° ที่ความถี่เดียว” ไม่ได้โดยตรง เลยรายงานเป็น `inverted`;
  ถ้าหน้าต่างไม่ครบ 1 รอบหรือ sample ต่อรอบน้อยไป จะแสดง note แทนป้าย `last cycle`
- ค่า phase ของ ngspice อยู่ใน radian ต้องแปลงเป็นองศาก่อน wrap (พิสูจน์ด้วย RC low-pass)

### Provenance และความซื่อสัตย์ของผล

- โมเดล `QT_NPN` เป็นโมเดลสอนที่โปรเจกต์เขียนเอง เพราะไม่มี Starter Kit ของอาจารย์
  การแสดงชื่อ/path/params ในตาราง Provenance ทำให้ผู้ใช้รู้ว่ากำลังดูผลของโมเดลไหน
- ผล SPICE ไม่บังคับให้ตรงกับผล Analytical ทุกหลัก เพราะคนละสมมติฐาน
  การตรวจรับจึงเทียบแต่ละแหล่งกับ contract ของตัวเอง ไม่ได้เอาตัวเลข Lab 03 ไปบังคับ Lab 04
- ตัวเลข IE ติดลบเป็น sign convention ของ ngspice ไม่ได้แก้ค่าดิบเพื่อความสวยงาม
  แต่เขียนคำอธิบายไว้ในหน้าเว็บ

### เครื่องมือ Browser และ UI

- ใบงานแนะนำ Playwright MCP แต่เครื่องนี้ไม่มี `node`/`npx` จึงใช้ **OpenCode Browser**
  และบันทึกชื่อเครื่องมือตามความจริงใน `docs/validation.md`
- OpenCode Browser ไม่มี tool ปรับ viewport จริง จึงใช้ iframe กว้าง 390 px ที่ media query
  `(max-width: 640px)` ทำงาน และวัด geometry แทนการอ้างว่าเป็นมือถือจริง
- การวัดนี้เจอ bug ที่ตาเปล่าอาจมองข้าม: กราฟล้นเพราะ grid item มี `min-width:auto`
  และตาราง Provenance มีข้อความยาวไม่ตัด — แก้ด้วย `minmax(0, 1fr)` และ `overflow-wrap`
  แล้ววัดซ้ำจน `scrollWidth ≤ innerWidth`
- โมเดล AI ที่เขียนเอกสารนี้ไม่สามารถเปิดดูภาพ screenshot ได้ จึงใช้ DOM geometry เป็นหลักฐาน
  และเก็บ screenshot ไว้ให้มนุษย์ตรวจ ไม่ได้อ้างว่าดูภาพแล้วเข้าใจว่าสวยงาม

## ข้อจำกัดและงานต่อยอด

- โมเดลนี้ไม่ใช่วงจรจริง — ไม่คิด Early effect, อุณหภูมิ, การกระจายของ β
- Lab 04 ยังไม่มี DC load line, parametric sweep, Monte Carlo, temperature sweep หรือ device model อื่น
- โหมด `bias` ยังเป็น analytical 3 วงจรเดิม; SPICE มีเฉพาะโหมด `dc`/`ac`/`tran` ของ fixture เดียว
