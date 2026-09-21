# Garden Retsept Atlasi — iikodan texnologik kartalarni (tarkib) olish.
#
# MUHIM KASHFIYOT (2026-09-21): iikoRMS REST API (/resto/api/...) da tex karta yo'q,
# LEKIN serverning veb-xizmat bo'limi (/resto/service/export/exportCsv.jsp) tex kartalarni
# CSV sifatida beradi:
#   /resto/service/export/csv/assemblyCharts.csv  — taom -> ingredientlar (brutto/netto)
#   /resto/service/export/csv/goods.csv           — kod -> nom / o'lchov birligi
# Kirish: /resto/j_spring_security_check (login+parol, ODDIY matn — SHA1 emas),
# chiqish: /resto/logout  (j_spring_security_logout emas — u 404 beradi).
#
# Bu modul FAQAT o'qiydi (GET), iikoda hech narsani o'zgartirmaydi.

import csv
import http.cookiejar
import io
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, date

IIKO_BASE = "https://olimp-garden.iiko.it/resto"
WEB_LOGIN = "Jurabek"
WEB_PASS = "200211"

UNIT_UZ = {"порц": "porsiya", "кг": "kg", "л": "litr", "шт": "dona", "гр": "gr", "мл": "ml"}


def _download_csvs():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_data = urllib.parse.urlencode({"j_username": WEB_LOGIN, "j_password": WEB_PASS}).encode()
    opener.open(f"{IIKO_BASE}/j_spring_security_check", login_data, timeout=30).read()
    try:
        out = {}
        for fname, marker in (("assemblyCharts.csv", b"PRODUCT_CODE"), ("goods.csv", b"TYPE;NUM")):
            raw = opener.open(f"{IIKO_BASE}/service/export/csv/{fname}", timeout=120).read()
            if marker not in raw[:200]:
                raise RuntimeError(f"{fname}: kutilgan CSV o'rniga boshqa narsa keldi (login muvaffaqiyatsiz bo'lishi mumkin)")
            out[fname] = raw.decode("utf-8-sig")
        return out
    finally:
        try:
            opener.open(f"{IIKO_BASE}/logout", timeout=20).read()
        except Exception:
            pass


def _f(s):
    try:
        return float(s.replace(",", "."))
    except Exception:
        return 0.0


def fmt_qty(value, unit):
    """kg/l ni kichik miqdorlarda gr/ml ga o'giradi (0.135 kg -> '135 gr')."""
    if unit in ("кг", "л"):
        base = "gr" if unit == "кг" else "ml"
        big = "kg" if unit == "кг" else "litr"
        if value >= 1:
            return f"{value:.3f}".rstrip("0").rstrip(".") + f" {big}"
        v = value * 1000
        s = f"{v:.0f}" if v >= 10 else f"{v:.1f}".rstrip("0").rstrip(".")
        return f"{s} {base}"
    if unit == "":
        return f"{value:g}"
    return f"{value:g} {UNIT_UZ.get(unit, unit)}"


def _pick_version(versions):
    """Bir mahsulotning bir nechta sanali kartalaridan bugungiga eng yaqin oxirgisini tanlaydi."""
    today = date.today()
    parsed = []
    for ds in versions:
        try:
            parsed.append((datetime.strptime(ds, "%d.%m.%Y").date(), ds))
        except Exception:
            parsed.append((date.min, ds))
    parsed.sort()
    past = [p for p in parsed if p[0] <= today]
    return (past[-1] if past else parsed[0])[1]


def build_recipes():
    """num (artikul) -> {"yield": "1 porsiya", "ingredients": [...], "technology": "..."} qaytaradi."""
    files = _download_csvs()

    goods = {}
    for row in csv.DictReader(io.StringIO(files["goods.csv"]), delimiter=";"):
        goods[row["NUM"]] = row

    charts = defaultdict(lambda: defaultdict(list))
    for row in csv.DictReader(io.StringIO(files["assemblyCharts.csv"]), delimiter=";"):
        charts[row["PRODUCT_CODE"]][row["DATE_FROM"]].append(row)

    def chart_rows(code):
        versions = charts.get(code)
        if not versions:
            return None
        return versions[_pick_version(list(versions.keys()))]

    def describe_item(row):
        code = row["ITEM_CODE"]
        g = goods.get(code)
        name = g["NAME"].strip() if g else f"Kod {code}"
        unit = g["MEASURE_UNIT"].strip() if g else ""
        gross = _f(row["ITEM_GROSS_WEIGHT"])
        net = _f(row["ITEM_NET_WEIGHT"])
        out_w = _f(row["ITEM_OUT_WEIGHT"])
        text = fmt_qty(gross, unit)
        extras = []
        # iikoda ba'zi ingredientlarda netto/chiqish 0 qilib qo'yilgan (ma'lumot kiritilmagan) —
        # "netto 0" o'quvchini chalg'itadi, shuning uchun 0 qiymatlar ko'rsatilmaydi.
        if net > 0 and abs(net - gross) > 1e-9:
            extras.append(f"netto {fmt_qty(net, unit)}")
        if out_w > 0 and abs(out_w - net) > 1e-9:
            extras.append(f"chiqishi {fmt_qty(out_w, unit)}")
        if extras:
            text = f"brutto {text} · " + " · ".join(extras)
        return code, g, name, text

    recipes = {}
    for num, g in goods.items():
        if g["TYPE"] != "DISH":
            continue
        rows = chart_rows(num)
        if not rows:
            continue
        ingredients = []
        for r in rows:
            code, ig, name, text = describe_item(r)
            item = {"name": name, "amount": text}
            # Yarim tayyor (п/ф) bo'lsa — uning O'Z retsepti AYNAN ISHLAB CHIQARISH
            # miqdori bilan (hisob-kitobsiz, manbadagidek) ko'rsatiladi.
            if ig and ig["TYPE"] == "PREPARED":
                sub_rows = chart_rows(code)
                if sub_rows:
                    sub_yield = _f(sub_rows[0]["AMOUNT"])
                    sub_unit = ig["MEASURE_UNIT"].strip()
                    sub_items = []
                    for sr in sub_rows:
                        _, _, sname, stext = describe_item(sr)
                        sub_items.append({"name": sname, "amount": stext})
                    item["sub"] = {"yield": fmt_qty(sub_yield, sub_unit) if sub_unit in ("кг", "л") else f"{sub_yield:g} {UNIT_UZ.get(sub_unit, sub_unit)}",
                                   "items": sub_items}
            ingredients.append(item)
        dish_yield = _f(rows[0]["AMOUNT"])
        dish_unit = g["MEASURE_UNIT"].strip()
        tech = " ".join(sorted({r["TECHNOLOGY"].strip() for r in rows if r["TECHNOLOGY"].strip()}))
        recipes[num] = {
            "yield": (fmt_qty(dish_yield, dish_unit) if dish_unit in ("кг", "л") else f"{dish_yield:g} {UNIT_UZ.get(dish_unit, dish_unit)}"),
            "ingredients": ingredients,
            "technology": tech,
        }
    return recipes
