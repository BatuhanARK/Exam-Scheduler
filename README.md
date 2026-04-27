# Exam Schedule Management System


## Installation

### 1. Install Python dependencies
```
pip install -r requirements.txt
```

---

### 2. Install the ODBC Driver (if not available)
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server  
→ Download and install **ODBC Driver 17 for SQL Server**

---

### 3. Create the Database
1. Open SQL Server Management Studio (SSMS)
2. Click **New Query**
3. Open the file:
```
/database/init.sql
```
4. Execute the script (F5)

➡️ This will automatically create the database, tables, and sample data.

---

### 4. Update connection settings in main.py
```python
SERVER   = "localhost"   # Example: DESKTOP-ABC\\SQLEXPRESS
DATABASE = "SinavTakvimiDB"
DRIVER   = "ODBC Driver 17 for SQL Server"
```

---

### 5. Activate SQL Server Authentication
SSMS → Right-click on the server → Properties → Security  
→ Select **SQL Server and Windows Authentication mode** → OK  
→ Restart SQL Server service

---

### 6. Launch the application
```
cd sinav_app
uvicorn main:app --reload --port 8000
```

---

### 7. Open in browser
http://localhost:8000

---

## Pages
| URL | Description | User |
|-----|------------|------|
| / | Login screen | — |
| /sinav-programi | Exam schedule table | App_Viewer |
| /gozetmen-yuk | Invigilator load distribution | App_Viewer |
| /salon-doluluk | Salon occupancy calendar | App_Viewer |
| /yonetim | SP calls + log | App_Admin |

---

## API Endpoints
| Method | URL | SP/UDF/View |
|--------|-----|-------------|
| GET | /api/sinav-programi | vw_SinavProgrami |
| GET | /api/gozetmen-yuk | vw_GozetmenYukDagilimi |
| GET | /api/salon-doluluk | vw_SalonDolulukDurumu |
| POST | /api/sinav-ekle | sp_SinavEkle |
| POST | /api/salon-ata | sp_SalonAta |
| POST | /api/gozetmen-ata | sp_GozetmenAta |
| POST | /api/yedek-al | sp_VeritabaniYedekle |
| GET | /api/musait-personel | fn_MusaitPersonelListesi |
| GET | /api/personel-gorev-sayisi/{id} | fn_PersonelGorevSayisi |
| GET | /api/sinav-kapasite/{id} | fn_SinavKapasite |
| GET | /api/log | Log_Tablosu |

---

## Automatic API Documentation
http://localhost:8000/docs (FastAPI Swagger UI)
