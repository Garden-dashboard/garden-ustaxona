# Garden Retsept Atlasi — iiko bilan sinxronlash.
# Har safar ishga tushganda: "Olimp Garden restaran" daraxtidagi DISH turidagi
# mahsulotlarni qayta oladi, data/dishes.json bilan solishtiradi:
#   - mavjud taom -> nom/narx/bo'lim yangilanadi, LEKIN tarkib/video/surat/faollik
#     (admin panelda kiritilgan ma'lumot) TEGILMAYDI
#   - yangi taom -> qo'shiladi (bo'sh tarkib/video bilan), fotosini CMS'dan avtomatik
#     moslashtirishga harakat qiladi
#   - iikoda endi yo'q taom -> active=False qilinadi (ma'lumoti o'chirilmaydi, faqat
#     saytda ko'rinmay qoladi — qayta paydo bo'lsa avtomatik qayta faollashadi)
# Muvaffaqiyatli bo'lsa generate.py'ni ham chaqiradi.

import difflib
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "dishes.json"

IIKO_BASE = "https://olimp-garden.iiko.it/resto"
IIKO_LOGIN = "Jurabek"
IIKO_PASS_SHA1 = hashlib.sha1("200211".encode()).hexdigest()
ROOT_GROUP_ID = "904469a5-8846-4356-a057-5f8b028c8b0c"  # "Olimp Garden restaran"
EXCLUDE_GROUPS = {"Одежда", "Пасуда"}  # oziq-ovqat bo'lmagan, iikoda DISH deb belgilangan bo'limlar

CMS_BASE = "http://178.104.44.177"
LIVE_MENU_URL = "https://garden-dashboard.github.io/olimp-garden-menu/"
CONFIRM_THRESHOLD = 0.72


def iiko_get(path, key):
    url = f"{IIKO_BASE}{path}{'&' if '?' in path else '?'}key={key}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8")


def fetch_iiko_dishes():
    key = iiko_get(f"/api/auth?login={IIKO_LOGIN}&pass={IIKO_PASS_SHA1}", "").strip()
    try:
        groups = json.loads(iiko_get("/api/v2/entities/products/group/list", key))
        products = json.loads(iiko_get("/api/v2/entities/products/list", key))
    finally:
        try:
            iiko_get("/api/logout", key)
        except Exception:
            pass

    by_id = {g["id"]: g for g in groups}

    def in_root_tree(gid, depth=0):
        if not gid or depth > 20:
            return False
        if gid == ROOT_GROUP_ID:
            return True
        g = by_id.get(gid)
        if not g:
            return False
        return in_root_tree(g.get("parent"), depth + 1)

    dishes = []
    for p in products:
        if p.get("deleted") or p.get("type") != "DISH":
            continue
        parent = p.get("parent")
        if not in_root_tree(parent):
            continue
        gname = (by_id.get(parent) or {}).get("name", "?")
        if gname in EXCLUDE_GROUPS:
            continue
        dishes.append({
            "id": p["id"],
            "name": p["name"].strip(),
            "price": p.get("defaultSalePrice") or 0,
            "group": gname,
        })
    return dishes


def norm(s):
    s = s.lower().strip()
    s = re.sub(r"\b\d+([.,]\d+)?\s*(кг|гр|л|мл|шт|порц|порц\.|п)\b", "", s)
    s = re.sub(r"[()]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch_cms_photos():
    """Eng oxirgi ishlagan tablet-menyu saytidan (CMS o'zi hozir buzilgan bo'lishi
    mumkinligi uchun undan emas) taom-surat lug'atini oladi."""
    try:
        html = urllib.request.urlopen(LIVE_MENU_URL, timeout=20).read().decode("utf-8")
    except Exception as e:
        print(f"OGOHLANTIRISH: CMS surat manbasi olinmadi: {e}", file=sys.stderr)
        return {}
    m = re.search(r'id="menu-data"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return {}
    data = json.loads(m.group(1))
    out = {}
    for c in data["categories"]:
        for it in c["items"]:
            if it.get("img"):
                out[norm(it["n"])] = LIVE_MENU_URL + it["img"]
    return out


def match_photo(name, cms_photos):
    n = norm(name)
    if n in cms_photos:
        return cms_photos[n], 1.0
    close = difflib.get_close_matches(n, list(cms_photos.keys()), n=1, cutoff=0.55)
    if not close:
        return None, 0
    score = difflib.SequenceMatcher(None, n, close[0]).ratio()
    return cms_photos[close[0]], score


def main():
    fresh = fetch_iiko_dishes()
    if len(fresh) < 100:
        print(f"OGOHLANTIRISH: faqat {len(fresh)} ta taom qaytdi, kutilganidan kam. To'xtatildi.", file=sys.stderr)
        sys.exit(1)

    existing = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_id = {d["id"]: d for d in existing}
    cms_photos = fetch_cms_photos()

    fresh_ids = set()
    added, updated, reactivated = 0, 0, 0
    for f in fresh:
        fresh_ids.add(f["id"])
        cur = by_id.get(f["id"])
        if cur:
            if cur["name"] != f["name"] or cur["price"] != f["price"] or cur["group"] != f["group"]:
                updated += 1
            cur["name"] = f["name"]
            cur["price"] = f["price"]
            cur["group"] = f["group"]
            if cur.get("active") is False:
                cur["active"] = True
                reactivated += 1
        else:
            photo, video_photo_status = None, "missing"
            suggested = None
            if cms_photos:
                url, score = match_photo(f["name"], cms_photos)
                if url and score >= CONFIRM_THRESHOLD:
                    photo, video_photo_status = url, "confirmed"
                elif url:
                    suggested, video_photo_status = url, "suggested"
            by_id[f["id"]] = {
                "id": f["id"], "name": f["name"], "price": f["price"], "group": f["group"],
                "photo": photo, "suggestedPhoto": suggested, "photoStatus": video_photo_status,
                "ingredients": [], "video": None, "active": True,
            }
            added += 1

    removed = 0
    for did, d in by_id.items():
        if did not in fresh_ids and d.get("active", True):
            d["active"] = False
            removed += 1

    merged = list(by_id.values())
    DATA_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(merged)} taom (+{added} yangi, {updated} yangilandi, "
          f"{removed} endi iikoda yo'q -> yashirildi, {reactivated} qayta faollashdi)")

    subprocess.run([sys.executable, str(Path(__file__).with_name("generate.py"))], check=True)


if __name__ == "__main__":
    main()
