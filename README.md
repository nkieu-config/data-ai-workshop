# 🎓 Thammasat Data & AI Workshop Assessment

ยินดีต้อนรับสู่ระบบโครงงาน Data Pipeline และ Analytics สำหรับจัดการข้อมูลประวัตินักศึกษา (Mock Dataset)
โปรเจกต์นี้ได้รับการพัฒนาและจัดระเบียบใหม่ทั้งหมด เพื่อให้สอดคล้องกับข้อกำหนดการส่งมอบงาน (Submission Checklist) อย่างครบถ้วน

---

## ✅ Submission Checklist Mapping (จุดตรวจสอบการส่งงาน)

เพื่อให้กรรมการผู้ประเมินสามารถตรวจสอบผลงานได้อย่างรวดเร็วและครบถ้วน เราได้จัดทำแผนที่เอกสารดังนี้:

| ข้อกำหนด (Requirement) | ไฟล์อ้างอิงหลัก (Supporting Files) | คำอธิบาย (Remarks) |
| :--- | :--- | :--- |
| **1. Architecture diagram** | 🔗 `architecture.md` | แผนภาพทางเดินข้อมูล (Data Flow) ตั้งแต่ไฟล์ Excel จนถึงชั้นประมวลผล (วาดด้วย Mermaid) |
| **2. README / Setup Guide** | 🔗 `README.md` (ไฟล์นี้) | คู่มือการรันระบบ ข้อยกเว้น และข้อจำกัดในการทำงาน |
| **3. Code for Pipeline & RAG** | 🔗 `pipeline.py`, `dashboard.py` | `pipeline.py` จัดการ Ingestion/Transformation ส่วน `dashboard.py` จัดการ Analytics/RAG |
| **4. Data Specification** | 🔗 `data_specification.md` | พจนานุกรมข้อมูล (Data Dictionary), แผนผังคอลัมน์, และ Data Security Access Matrix (Part 3) |
| **5. Evidence of idempotent re-run**| 🔗 `evidence_idempotent_and_quality.txt` | แสดง Log การรันซ้ำ 2 ครั้ง ที่จำนวนแถวคงที่ 180 แถวไม่เกิดการเบิ้ล |
| **6. Quality summary evidence** | 🔗 `evidence_idempotent_and_quality.txt` | มีการเทียบ Count, Sum ของข้อมูลต้นทางและปลายทางผ่านระบบ QC checks ก่อนบันทึก |
| **7. RAG examples & Interface** | 🔗 `dashboard.py` (แท็บ RAG Q&A) | มีหน้าจอค้นหาข้อมูล RAG ผ่าน Streamlit พร้อมแสดง Context chunk และ LLM Prompt |
| **8. No masked/encrypted columns** | 🔗 `data_specification.md` (Part 3) | คงโครงสร้าง Excel เดิมไว้ทั้งหมด 100% ตามคำสั่ง และอธิบายเงื่อนไขความปลอดภัยไว้ในเอกสารแทน |

---

## 🛠️ ขั้นตอนการรันระบบ (Setup & Run Steps)

### 1. การติดตั้งไลบรารี
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. การรันระบบเพื่อสร้างข้อมูล (Idempotent Batch Pipeline)
รันสคริปต์ตรวจสอบการโหลดซ้ำแบบ Idempotency:
```bash
python3 verify_idempotency.py
```
*(เมื่อรันแล้ว ไฟล์ข้อมูลจำลองแบบ Parquet จะถูกสร้างในโฟลเดอร์ `data/raw/` และ `data/stg/` พร้อมอัปเดตฐานข้อมูล DuckDB)*

### 3. การเปิดหน้าจอ Data Product & RAG Interface
ใช้คำสั่งนี้เพื่อเปิดแผงควบคุมบนเบราว์เซอร์:
```bash
python3 -m streamlit run dashboard.py
```
แผงควบคุมประกอบด้วย 3 แท็บหลัก:
1. **Analytics Dashboard:** ดูสรุปกราฟสถิติตามสาขา
2. **Audit Logs:** ดูประวัติการรัน Batch Pipeline
3. **RAG Q&A:** หน้าต่างจำลองการถามตอบ (Keyword Retrieval + LLM Prompt Generator)

---

## 📌 สมมติฐานและข้อจำกัด (Assumptions and Limitations)
1. **Idempotency Strategy:** ระบบใช้กลยุทธ์ *Delete-before-insert* โดยอ้างอิงจาก `snapshot_date` ของวันนั้นๆ ซึ่งปลอดภัยและจัดการกับการรันข้อมูลย้อนหลัง (Backfill) ได้ง่ายที่สุดสำหรับ DuckDB
2. **LLM Availability:** เนื่องจากโจทย์ไม่ได้บังคับให้ต่อ API LLM จริงเพื่อป้องกันค่าใช้จ่าย เราจึงออกแบบ RAG Interface ในโหมด *Keyword-based Retrieval* โดยระบบจะทำการค้นหาประโยคจาก `rag_document_text` และโชว์ **Prompt** ที่สมบูรณ์พร้อมส่งต่อให้ LLM แทน
3. **Data Masking:** ข้อมูลเป็นชุดทดสอบ (Synthetic) จึงไม่มีการปิดบัง (Masking) ข้อมูล PII ใน Database ตามที่โจทย์ระบุ แต่เราได้เขียนนโยบายควบคุมหากต้องใช้ข้อมูลจริงไว้ในไฟล์ `data_specification.md`
