"""TCMB EVDS'den kredi/mevduat faizleri ve TÜFE'yi alır, oranlar.json yazar.
Kredi (haftalık, yıllık basit %): TP.KTF10 ihtiyaç, TP.KTF11 taşıt, TP.KTF12 konut.
Mevduat (haftalık, yıllık brüt %): TP.TRY.MT01..MT05 (1 ay, 3 ay, 6 ay, 1 yıl, 1 yıl+).
TÜFE (aylık endeks): TP.FG.J0 -> yıllık değişim."""
import json, os, sys, urllib.request
from datetime import date, timedelta

ADRESLER = ["https://evds3.tcmb.gov.tr/igmevdsms-dis/", "https://evds2.tcmb.gov.tr/service/evds/"]
anahtar = os.environ.get("EVDS_KEY", "").strip()
if not anahtar:
    sys.exit("EVDS_KEY tanımlı değil")
bugun = date.today()

def cek(kodlar, gun, frekans):
    sorgu = "series=%s&startDate=%s&endDate=%s&type=json&frequency=%d" % (
        "-".join(kodlar), (bugun - timedelta(days=gun)).strftime("%d-%m-%Y"), bugun.strftime("%d-%m-%Y"), frekans)
    hatalar = []
    for adres in ADRESLER:
        try:
            istek = urllib.request.Request(adres + sorgu, headers={"key": anahtar, "User-Agent": "kredi-oranlari"})
            with urllib.request.urlopen(istek, timeout=60) as y:
                return json.loads(y.read().decode("utf-8")).get("items", [])
        except Exception as e:
            hatalar.append("%s -> %s" % (adres, e))
    print("UYARI: %s alınamadı: %s" % (kodlar, hatalar))
    return []

def sayi(v):
    try:
        return round(float(v), 2) if v not in (None, "", "null") else None
    except ValueError:
        return None

# Kredi: son 1 yıl haftalık
KREDI = {"ihtiyac": "TP.KTF10", "tasit": "TP.KTF11", "konut": "TP.KTF12"}
gecmis = []
for k in cek(list(KREDI.values()), 380, 1):
    satir = {ad: sayi(k.get(kod.replace(".", "_"))) for ad, kod in KREDI.items()}
    if any(v is not None for v in satir.values()):
        satir["hafta"] = k.get("Tarih")
        gecmis.append(satir)
if not gecmis:
    sys.exit("Kredi faizi verisi yok")
son = gecmis[-1]
yillik, hafta = {}, son["hafta"]
for ad in KREDI:
    for s in reversed(gecmis):
        if s.get(ad) is not None:
            yillik[ad] = s[ad]
            break

# Mevduat: son değerler
MEV = {"1ay": "TP.TRY.MT01", "3ay": "TP.TRY.MT02", "6ay": "TP.TRY.MT03", "1yil": "TP.TRY.MT04", "1yil_ustu": "TP.TRY.MT05"}
mevduat, mev_hafta = {}, None
for k in reversed(cek(list(MEV.values()), 70, 1)):
    for ad, kod in MEV.items():
        v = sayi(k.get(kod.replace(".", "_")))
        if ad not in mevduat and v is not None:
            mevduat[ad] = v
            mev_hafta = mev_hafta or k.get("Tarih")

# TÜFE: aylık endeks -> yıllık %
tufe = [(k.get("Tarih"), sayi(k.get("TP_FG_J0"))) for k in cek(["TP.FG.J0"], 460, 5)]
tufe = [t for t in tufe if t[1]]
tufe_yillik, tufe_ay = None, None
if len(tufe) >= 13:
    tufe_yillik = round((tufe[-1][1] / tufe[-13][1] - 1) * 100, 2)
    tufe_ay = tufe[-1][0]

veri = {
    "kaynak": "TCMB EVDS - ağırlıklı ortalama faizler (yıllık, basit) ve TÜFE",
    "hafta": hafta,
    "guncelleme": bugun.isoformat(),
    "yillik": yillik,
    "gecmis": gecmis[-26:],
    "mevduat": mevduat,
    "mevduat_hafta": mev_hafta,
    "tufe_yillik": tufe_yillik,
    "tufe_ay": tufe_ay,
}
with open("oranlar.json", "w", encoding="utf-8") as f:
    json.dump(veri, f, ensure_ascii=False, indent=2)
print(json.dumps(veri, ensure_ascii=False)[:1500])
