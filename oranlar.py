"""TCMB EVDS'den haftalık ağırlıklı ortalama kredi faizlerini alır, oranlar.json yazar.
Seriler (yıllık basit %): TP.KTF10 ihtiyaç, TP.KTF11 taşıt, TP.KTF12 konut."""
import json, os, sys, urllib.request
from datetime import date, timedelta

SERILER = {"ihtiyac": "TP.KTF10", "tasit": "TP.KTF11", "konut": "TP.KTF12"}
ADRESLER = [
    "https://evds3.tcmb.gov.tr/igmevdsms-dis/",
    "https://evds2.tcmb.gov.tr/service/evds/",
]
anahtar = os.environ.get("EVDS_KEY", "").strip()
if not anahtar:
    sys.exit("EVDS_KEY tanımlı değil")

bit = date.today()
bas = bit - timedelta(days=70)
sorgu = "series=%s&startDate=%s&endDate=%s&type=json&frequency=1" % (
    "-".join(SERILER.values()), bas.strftime("%d-%m-%Y"), bit.strftime("%d-%m-%Y"))

veri, hata = None, []
for adres in ADRESLER:
    try:
        istek = urllib.request.Request(adres + sorgu, headers={"key": anahtar, "User-Agent": "kredi-oranlari"})
        with urllib.request.urlopen(istek, timeout=60) as y:
            veri = json.loads(y.read().decode("utf-8"))
        break
    except Exception as e:
        hata.append("%s -> %s" % (adres, e))
if veri is None:
    sys.exit("EVDS'ye ulaşılamadı:\n" + "\n".join(hata))

oranlar, tarih = {}, None
for kalem in reversed(veri.get("items", [])):
    for ad, kod in SERILER.items():
        deger = kalem.get(kod.replace(".", "_"))
        if ad not in oranlar and deger not in (None, "", "null"):
            oranlar[ad] = round(float(deger), 2)
            tarih = tarih or kalem.get("Tarih")
if not oranlar:
    sys.exit("Seride değer yok: " + json.dumps(veri)[:500])

with open("oranlar.json", "w", encoding="utf-8") as f:
    json.dump({
        "kaynak": "TCMB EVDS - Bankalarca açılan kredilere uygulanan ağırlıklı ortalama faiz (yıllık, basit)",
        "hafta": tarih,
        "guncelleme": bit.isoformat(),
        "yillik": oranlar,
    }, f, ensure_ascii=False, indent=2)
print(open("oranlar.json", encoding="utf-8").read())
