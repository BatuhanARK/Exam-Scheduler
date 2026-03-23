"""
SINAV TAKVİMİ YÖNETİM SİSTEMİ
YZM 2126 - Veritabanı Sistemlerine Giriş
Backend: FastAPI + pyodbc
"""

from fastapi import FastAPI, HTTPException, Query, Cookie, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
import pyodbc
import secrets

# ── Uygulama ──────────────────────────────────────────────────
app = FastAPI(title="Sınav Takvimi Yönetim Sistemi", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Basit Session Deposu (bellek içi) ─────────────────────────
# { token: "admin" | "viewer" }
sessions: dict[str, str] = {}

def get_role(session_token: Optional[str] = Cookie(None)) -> Optional[str]:
    """Cookie'den kullanıcı rolünü döndürür. Yoksa None."""
    if not session_token:
        return None
    return sessions.get(session_token)

# ── Bağlantı Ayarları ─────────────────────────────────────────
SERVER   = "localhost"          # veya bilgisayar adın, örn: DESKTOP-ABC\SQLEXPRESS
DATABASE = "SinavTakvimiDB"
DRIVER   = "ODBC Driver 17 for SQL Server"

def get_conn(role: str = "admin") -> pyodbc.Connection:
    if role == "admin":
        uid, pwd = "App_Admin", "Admin@12345!"
    else:
        uid, pwd = "App_Viewer", "Viewer@12345!"
    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={uid};"
        f"PWD={pwd};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def rows_to_dict(cursor) -> list[dict]:
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ── Pydantic Modeller (Request Body) ─────────────────────────
class SinavEkleModel(BaseModel):
    ders_id:   int
    tarih:     str   # "2026-01-15"
    oturum_id: int

class SalonAtaModel(BaseModel):
    sinav_id: int

class GozetmenAtaModel(BaseModel):
    sinav_id:   int
    derslik_id: int


# ═══════════════════════════════════════════════════════════════
# LOGIN / LOGOUT
# ═══════════════════════════════════════════════════════════════

@app.post("/api/login")
async def login(rol: str = Query(...), response: Response = None):
    if rol not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Geçersiz rol.")
    token = secrets.token_hex(32)
    sessions[token] = rol
    response.set_cookie(key="session_token", value=token,
        httponly=True, samesite="lax", max_age=3600)
    return {"success": True, "rol": rol}

@app.get("/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token and session_token in sessions:
        del sessions[session_token]
    response.delete_cookie("session_token")
    return RedirectResponse(url="/", status_code=302)


# ═══════════════════════════════════════════════════════════════
# SAYFA ROUTE'LARI (HTML döndürür)
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def anasayfa(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/sinav-programi", response_class=HTMLResponse)
async def sinav_programi_sayfa(request: Request, session_token: Optional[str] = Cookie(None)):
    if not get_role(session_token):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("sinav_programi.html", {"request": request, "rol": get_role(session_token)})

@app.get("/gozetmen-yuk", response_class=HTMLResponse)
async def gozetmen_yuk_sayfa(request: Request, session_token: Optional[str] = Cookie(None)):
    if not get_role(session_token):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("gozetmen_yuk.html", {"request": request, "rol": get_role(session_token)})

@app.get("/salon-doluluk", response_class=HTMLResponse)
async def salon_doluluk_sayfa(request: Request, session_token: Optional[str] = Cookie(None)):
    if not get_role(session_token):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("salon_doluluk.html", {"request": request, "rol": get_role(session_token)})

@app.get("/program-tablosu", response_class=HTMLResponse)
async def program_tablosu_sayfa(request: Request, session_token: Optional[str] = Cookie(None)):
    if not get_role(session_token):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("program_tablosu.html", {"request": request, "rol": get_role(session_token)})

@app.get("/yonetim", response_class=HTMLResponse)
async def yonetim_sayfa(request: Request, session_token: Optional[str] = Cookie(None)):
    if get_role(session_token) != "admin":
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("yonetim.html", {"request": request, "rol": "admin"})


# ═══════════════════════════════════════════════════════════════
# API ROUTE'LARI — VIEW SORGULARI (App_Viewer ile bağlanır)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/sinav-programi")
async def api_sinav_programi(
    tarih:    Optional[str] = Query(None, description="2026-01-06"),
    yariyil:  Optional[int] = Query(None),
    bolum:    Optional[str] = Query(None)
):
    """vw_SinavProgrami view'ını filtreli döndürür."""
    try:
        conn   = get_conn("viewer")
        cursor = conn.cursor()

        sql    = "SELECT * FROM vw_SinavProgrami WHERE 1=1"
        params = []

        if tarih:
            sql += " AND Tarih = ?"
            params.append(tarih)
        if yariyil:
            sql += " AND Yariyil = ?"
            params.append(yariyil)
        if bolum:
            sql += " AND Bolum = ?"
            params.append(bolum)

        sql += " ORDER BY Tarih, BaslangicSaat"
        cursor.execute(sql, params)
        data = rows_to_dict(cursor)
        conn.close()

        # DATE ve TIME nesnelerini string'e çevir
        for row in data:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = str(v)

        return {"success": True, "data": data, "count": len(data)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gozetmen-yuk")
async def api_gozetmen_yuk(
    bolum:        Optional[str] = Query(None),
    yuk_seviyesi: Optional[str] = Query(None)
):
    """vw_GozetmenYukDagilimi view'ını döndürür."""
    try:
        conn   = get_conn("viewer")
        cursor = conn.cursor()

        sql    = "SELECT * FROM vw_GozetmenYukDagilimi WHERE 1=1"
        params = []

        if bolum:
            sql += " AND Bolum = ?"
            params.append(bolum)
        if yuk_seviyesi:
            sql += " AND YukSeviyesi = ?"
            params.append(yuk_seviyesi)

        sql += " ORDER BY ToplamGorev DESC"
        cursor.execute(sql, params)
        data = rows_to_dict(cursor)
        conn.close()

        for row in data:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = str(v)

        return {"success": True, "data": data, "count": len(data)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/salon-doluluk")
async def api_salon_doluluk(
    tarih:    Optional[str] = Query(None),
    durum:    Optional[str] = Query(None)   # "Dolu" veya "Bos"
):
    """vw_SalonDolulukDurumu view'ını döndürür."""
    try:
        conn   = get_conn("viewer")
        cursor = conn.cursor()

        sql    = "SELECT * FROM vw_SalonDolulukDurumu WHERE 1=1"
        params = []

        if tarih:
            sql += " AND Tarih = ?"
            params.append(tarih)
        if durum:
            sql += " AND Durum = ?"
            params.append(durum)

        sql += " ORDER BY Tarih, BaslangicSaat, SalonAdi"
        cursor.execute(sql, params)
        data = rows_to_dict(cursor)
        conn.close()

        for row in data:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = str(v)

        return {"success": True, "data": data, "count": len(data)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# API — PROGRAM MATRİSİ (tarih × oturum pivot)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/program-matrisi")
async def api_program_matrisi():
    """
    Sınav programını tarih × oturum pivot formatında döndürür.
    Her hücre: {ders, bolum, salonlar, ogrenci, kapasite, gozetmenler}
    UDF fn_SinavKapasite her sınav için çağrılır.
    """
    try:
        conn   = get_conn("viewer")
        cursor = conn.cursor()

        # Tüm sınav programını çek (view'dan)
        cursor.execute("""
            SELECT SinavID, Tarih, GunAdi, OturumID, Oturum, BaslangicSaat,
                   DersKodu, DersAdi, Bolum, Yariyil, OgrenciSayisi,
                   Salonlar, ToplamKapasite, GozetmenSayisi, KapasiteDurumu
            FROM vw_SinavProgrami
            ORDER BY Tarih, BaslangicSaat
        """)
        sinavlar = rows_to_dict(cursor)

        # Gözetmen adlarını önceden çek (SinavID → liste)
        cursor.execute("""
            SELECT ga.SinavID,
                   p.Unvan + ' ' + p.Ad + ' ' + p.Soyad AS AdSoyad,
                   dl.Ad AS SalonAdi
            FROM   Gozetmen_Atamalari ga
            JOIN   Personel           p  ON ga.PersonelID  = p.PersonelID
            JOIN   Derslikler         dl ON ga.DerslikID   = dl.DerslikID
            ORDER BY ga.SinavID, dl.Ad
        """)
        gozetmen_rows = rows_to_dict(cursor)
        # { sinav_id: ["Dr. Ali Kaya (Amfi-A)", ...] }
        gozetmen_map = {}
        for g in gozetmen_rows:
            sid = str(g["SinavID"])
            if sid not in gozetmen_map:
                gozetmen_map[sid] = []
            gozetmen_map[sid].append(f"{g['AdSoyad']} ({g['SalonAdi']})")

        # Benzersiz tarihler ve oturumlar
        tarihler = []
        oturumlar = []
        seen_t, seen_o = set(), set()
        for s in sinavlar:
            t = str(s["Tarih"])
            o_key = str(s["OturumID"])
            if t not in seen_t:
                seen_t.add(t)
                tarihler.append({"tarih": t, "gun": s["GunAdi"]})
            if o_key not in seen_o:
                seen_o.add(o_key)
                oturumlar.append({
                    "id": s["OturumID"],
                    "tanim": s["Oturum"],
                    "saat": str(s["BaslangicSaat"])
                })

        # Pivot: {tarih: {oturum_id: [sinavlar]}}
        pivot = {}
        for s in sinavlar:
            t = str(s["Tarih"])
            o = str(s["OturumID"])
            if t not in pivot:
                pivot[t] = {}
            if o not in pivot[t]:
                pivot[t][o] = []

            # fn_SinavKapasite UDF çağrısı (Admin conn gerekir)
            conn_admin = get_conn("admin")
            cur2 = conn_admin.cursor()
            cur2.execute("SELECT dbo.fn_SinavKapasite(?) AS Kap", s["SinavID"])
            kap_row = cur2.fetchone()
            udf_kapasite = kap_row[0] if kap_row else 0
            conn_admin.close()

            for k, v in s.items():
                if hasattr(v, "isoformat"):
                    s[k] = str(v)
            s["UDF_Kapasite"] = udf_kapasite
            s["Gozetmenler"]  = gozetmen_map.get(str(s["SinavID"]), [])
            pivot[t][o].append(s)

        conn.close()
        return {
            "success":   True,
            "tarihler":  tarihler,
            "oturumlar": oturumlar,
            "pivot":     pivot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/udf-ozet")
async def api_udf_ozet():
    """
    fn_PersonelGorevSayisi ve fn_SinavKapasite UDF'lerini
    tüm kayıtlar için çağırıp özet döndürür.
    """
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()

        # fn_PersonelGorevSayisi — her personel için
        cursor.execute("""
            SELECT p.PersonelID,
                   p.Unvan + ' ' + p.Ad + ' ' + p.Soyad AS AdSoyad,
                   b.Ad AS Bolum,
                   dbo.fn_PersonelGorevSayisi(p.PersonelID) AS GorevSayisi
            FROM Personel p
            JOIN Bolumler b ON p.BolumID = b.BolumID
            WHERE p.Aktif = 1
            ORDER BY GorevSayisi DESC
        """)
        personel_gorev = rows_to_dict(cursor)

        # fn_SinavKapasite — her sınav için
        cursor.execute("""
            SELECT s.SinavID, d.DersKodu, d.Ad AS DersAdi,
                   d.OgrenciSayisi,
                   dbo.fn_SinavKapasite(s.SinavID) AS AtananKapasite,
                   dbo.fn_SinavKapasite(s.SinavID) - d.OgrenciSayisi AS FazlaKapasite
            FROM Sinavlar s
            JOIN Dersler  d ON s.DersID = d.DersID
            ORDER BY s.SinavID
        """)
        sinav_kapasite = rows_to_dict(cursor)
        conn.close()

        return {
            "success":        True,
            "personel_gorev": personel_gorev,
            "sinav_kapasite": sinav_kapasite
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# API ROUTE'LARI — STORED PROCEDURE ÇAĞRILARI (App_Admin)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/sinav-ekle")
async def api_sinav_ekle(body: SinavEkleModel):
    """sp_SinavEkle stored procedure'ünü çağırır."""
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute(
            "EXEC sp_SinavEkle @DersID=?, @Tarih=?, @OturumID=?",
            body.ders_id, body.tarih, body.oturum_id
        )
        # SP'nin döndürdüğü sonuç setini al (SinavID, GunlukSinavSayisi, Durum)
        result = rows_to_dict(cursor)
        conn.commit()
        conn.close()
        return {"success": True, "data": result}

    except pyodbc.Error as e:
        # SQL Server'dan gelen THROW mesajını yakala
        error_msg = str(e.args[1]) if len(e.args) > 1 else str(e)
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/api/salon-ata")
async def api_salon_ata(body: SalonAtaModel):
    """sp_SalonAta stored procedure'ünü çağırır."""
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute("EXEC sp_SalonAta @SinavID=?", body.sinav_id)
        result = rows_to_dict(cursor)
        conn.commit()
        conn.close()
        return {"success": True, "data": result}

    except pyodbc.Error as e:
        error_msg = str(e.args[1]) if len(e.args) > 1 else str(e)
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/api/gozetmen-ata")
async def api_gozetmen_ata(body: GozetmenAtaModel):
    """sp_GozetmenAta stored procedure'ünü çağırır."""
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute(
            "EXEC sp_GozetmenAta @SinavID=?, @DerslikID=?",
            body.sinav_id, body.derslik_id
        )
        result = rows_to_dict(cursor)
        conn.commit()
        conn.close()
        return {"success": True, "data": result}

    except pyodbc.Error as e:
        error_msg = str(e.args[1]) if len(e.args) > 1 else str(e)
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/api/yedek-al")
async def api_yedek_al():
    """sp_VeritabaniYedekle stored procedure'ünü çağırır (BONUS)."""
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute("EXEC sp_VeritabaniYedekle")
        result = rows_to_dict(cursor)
        conn.commit()
        conn.close()
        return {"success": True, "data": result}

    except pyodbc.Error as e:
        error_msg = str(e.args[1]) if len(e.args) > 1 else str(e)
        raise HTTPException(status_code=400, detail=error_msg)


# ═══════════════════════════════════════════════════════════════
# API ROUTE'LARI — UDF ÇAĞRILARI
# ═══════════════════════════════════════════════════════════════

@app.get("/api/personel-gorev-sayisi/{personel_id}")
async def api_personel_gorev_sayisi(personel_id: int):
    """fn_PersonelGorevSayisi UDF'ini çağırır."""
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT dbo.fn_PersonelGorevSayisi(?) AS GorevSayisi",
            personel_id
        )
        row = cursor.fetchone()
        conn.close()
        return {"success": True, "personel_id": personel_id, "gorev_sayisi": row[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sinav-kapasite/{sinav_id}")
async def api_sinav_kapasite(sinav_id: int):
    """fn_SinavKapasite UDF'ini çağırır."""
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT dbo.fn_SinavKapasite(?) AS ToplamKapasite",
            sinav_id
        )
        row = cursor.fetchone()
        conn.close()
        return {"success": True, "sinav_id": sinav_id, "toplam_kapasite": row[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/musait-personel")
async def api_musait_personel(
    tarih:     str = Query(..., description="2026-01-15"),
    oturum_id: int = Query(..., description="1")
):
    """fn_MusaitPersonelListesi Table-Valued UDF'ini çağırır."""
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.fn_MusaitPersonelListesi(?, ?) ORDER BY ToplamGorev ASC",
            tarih, oturum_id
        )
        data = rows_to_dict(cursor)
        conn.close()
        return {"success": True, "data": data, "count": len(data)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# API — YARDIMCI VERİ ROUTE'LARI
# ═══════════════════════════════════════════════════════════════

@app.get("/api/dersler")
async def api_dersler():
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.DersID, d.DersKodu, d.Ad, d.Ders_Turu,
                   d.OgrenciSayisi, d.Yariyil, b.Ad AS BolumAdi
            FROM   Dersler  d
            JOIN   Bolumler b ON d.BolumID = b.BolumID
            ORDER BY d.Yariyil, d.DersKodu
        """)
        data = rows_to_dict(cursor)
        conn.close()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/oturumlar")
async def api_oturumlar():
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Oturumlar ORDER BY BaslangicSaat")
        data = rows_to_dict(cursor)
        conn.close()
        for row in data:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = str(v)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/log")
async def api_log(limit: int = Query(20)):
    try:
        conn   = get_conn("admin")
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT TOP {limit} * FROM Log_Tablosu ORDER BY LogID DESC"
        )
        data = rows_to_dict(cursor)
        conn.close()
        for row in data:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = str(v)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))