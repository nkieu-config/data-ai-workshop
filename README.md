# 🎓 Thammasat Data & AI Workshop Assessment (Parts 0 - 3)

ยินดีต้อนรับทีมงานทุกคนเข้าสู่โปรเจกต์เวิร์กชอป! Repository นี้เก็บซอร์สโค้ดและข้อมูลสำหรับการทำระบบ Data Pipeline เพื่อจัดการข้อมูลประวัตินักศึกษา (ถึงระดับ Part 3)

---

## 🛠️ ขั้นตอนการติดตั้งสำหรับทีมงาน (Installation Guide)

เพื่อให้ทุกคนรันโปรเจกต์บนเครื่องตัวเองได้ตรงกัน ให้ทำตามขั้นตอนดังนี้:

### 1. โคลนคลังข้อมูล (Clone Repository)
```bash
git clone <url-ของ-github-คุณ>
cd "Data & Ai Workshop"
```

### 2. สร้าง Virtual Environment (แนะนำ)
เพื่อป้องกันไม่ให้เวอร์ชันของไลบรารีตีกับงานอื่นในเครื่อง:
*   **macOS / Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
*   **Windows (PowerShell):**
    ```bash
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

### 3. ติดตั้งไลบรารีที่จำเป็น
```bash
pip install -r requirements.txt
```

---

## 🚀 วิธีการรันและทดสอบระบบ (How to Run)

### 1. ทดสอบการรันระบบและตรวจสอบความถูกต้องแบบอัตโนมัติ
รันคำสั่งนี้เพื่อดึงข้อมูลดิบแปลงเป็น Parquet และบันทึกเข้า DuckDB พร้อมตรวจสอบความซ้ำซ้อนของข้อมูล (Idempotency Check) และตรวจสอบความถูกต้อง (QC checks):
```bash
python3 verify_idempotency.py
```
*หากการทำงานถูกต้อง คุณจะเห็นข้อความ: `✅ SUCCESS: Idempotent behavior confirmed! Rerunning didn't double the rows.` ปรากฏขึ้น*

### 2. เปิดหน้าเว็บ Dashboard เพื่อนำเสนอผลงาน
รันคำสั่งเปิดระบบแดชบอร์ดบนเบราว์เซอร์เพื่อดูกราฟข้อมูลและประวัติการทำงานของระบบ (Audit Logs):
```bash
python3 -m streamlit run dashboard.py
```
*(หาก PATH ถูกต้อง สามารถใช้ `streamlit run dashboard.py` ได้เช่นกัน)*

---

## 📂 โครงสร้างโฟลเดอร์ของโปรเจกต์ (Project Structure)
เมื่อรันคำสั่งติดตั้งและประมวลผลแล้ว โครงสร้างโฟลเดอร์จะเป็นดังนี้:
```text
├── data/                             # [GitIgnored] โฟลเดอร์เก็บข้อมูลดิบและ Database
│   ├── raw/                          # ไฟล์ข้อมูล Parquet ดิบ (Immutable)
│   ├── stg/                          # ไฟล์ข้อมูล Parquet ที่ล้างและแปลงประเภทแล้ว
│   └── trusted_database.db           # ฐานข้อมูล DuckDB (Trusted Layer)
├── pipeline.py                       # โค้ดระบบท่อข้อมูลหลัก (ETL Pipeline)
├── verify_idempotency.py             # สคริปต์รันทดสอบระบบอัตโนมัติ
├── dashboard.py                      # แดชบอร์ดสรุปผลและแสดงประวัติระบบ (Streamlit)
├── requirements.txt                  # รายชื่อไลบรารีที่ต้องติดตั้ง
├── .gitignore                        # ไฟล์ยกเว้นการ Commit ข้อมูลส่วนตัว/ฐานข้อมูลขึ้น GitHub
└── README.md                         # คู่มือการติดตั้งและใช้งานโปรเจกต์ (ไฟล์นี้)
```

---

## 📌 วิธีการอัปโหลดขึ้น GitHub (สำหรับ PM/หัวหน้าทีม)
หากคุณเป็นคนเริ่มอัพโปรเจกต์ขึ้น GitHub เป็นคนแรก ให้ทำตามขั้นตอนนี้ใน Terminal:

1.  **Initialize Git Local Repository:**
    ```bash
    git init
    ```
2.  **Add all files (ระบบจะทำการข้ามฐานข้อมูลและโฟลเดอร์ data/ ให้ตามกฎใน .gitignore):**
    ```bash
    git add .
    ```
3.  **Commit ไฟล์แรก:**
    ```bash
    git commit -m "feat: init data pipeline and analytics dashboard templates"
    ```
4.  **สร้างคลังบน GitHub (สร้างเป็น Private หรือ Public ก็ได้) จากนั้นนำคำสั่งรีโมทลิงก์มารัน:**
    ```bash
    git branch -M main
    git remote add origin <URL-จาก-GitHub-ของคุณ>
    git push -u origin main
    ```
