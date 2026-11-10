# AGENTS.md

Conventions สำหรับ AI coding agent ที่ทำงานในโปรเจกต์นี้

## กติกาหลัก

- สมการวิศวกรรมทั้งหมดอยู่ใน `dc_bias.py` เท่านั้น — ห้ามคำนวณ DC bias ใน template หรือ JavaScript
- `dc_bias.py` รับ/คืนค่าเป็น SI units (V, Ω, A) — การแปลง kΩ/MΩ อยู่ที่ `app.py`
- ห้ามฝังค่าผลลัพธ์ (เช่น 9.294) ลงใน `templates/index.html` — ต้องมาจาก `solve()` เสมอ
- เพิ่ม/แก้ test ทุกครั้งที่เปลี่ยนสมการหรือ validation
- ใช้ `unittest` ตามคำสั่ง `python -m unittest discover -s tests -v` (ไม่ใช้ pytest)

## โครงสร้างความรับผิดชอบ

| ไฟล์ | รับผิดชอบ |
|---|---|
| `dc_bias.py` | สมการ, region detection, warnings |
| `app.py` | HTTP routes, parse form, unit conversion, validation, status code |
| `templates/index.html` | การแสดงผลเท่านั้น |
| `static/style.css` | หน้าตา/ responsive |

## สถานะ HTTP

- อินพุตถูกต้อง → 200
- อินพุตผิด (ว่าง / ไม่ใช่ตัวเลข / ค่า ≤ 0 / หน่วยผิด) → 400 พร้อม error รายช่อง

## ข้อห้าม

- ห้าม commit `.venv/`, `__pycache__/`, `.env`
- ห้ามใช้ `app.run(debug=True)` เปิดให้เครือข่ายภายนอกเข้าถึง
