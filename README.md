# Sınav Takvimi Yönetim Sistemi
YZM 2126 — Veritabanı Sistemlerine Giriş

## Kurulum

### 1. Python bağımlılıklarını kur
```
pip install -r requirements.txt
```

### 2. ODBC Driver'ı kur (yoksa)
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
→ "ODBC Driver 17 for SQL Server" indir ve kur

### 3. main.py içinde bağlantı ayarlarını güncelle
```python
SERVER   = "localhost"   # Örn: DESKTOP-ABC\SQLEXPRESS
DATABASE = "SinavTakvimiDB"
DRIVER   = "ODBC Driver 17 for SQL Server"
```

### 4. SQL Server Authentication'ı aktif et
SSMS → Sunucuya sağ tıkla → Properties → Security
→ "SQL Server and Windows Authentication mode" seç → OK
→ SQL Server servisini yeniden başlat

### 5. Uygulamayı başlat
```
cd sinav_app
uvicorn main:app --reload --port 8000
```

### 6. Tarayıcıda aç
http://localhost:8000

## Sayfalar
| URL | Açıklama | Kullanıcı |
|-----|----------|-----------|
| / | Giriş ekranı | — |
| /sinav-programi | Sınav programı tablosu | App_Viewer |
| /gozetmen-yuk | Gözetmen yük dağılımı | App_Viewer |
| /salon-doluluk | Salon doluluk takvimi | App_Viewer |
| /yonetim | SP çağrıları + log | App_Admin |

## API Endpoint'leri
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

## Otomatik API Dökümantasyonu
http://localhost:8000/docs  (FastAPI Swagger UI)