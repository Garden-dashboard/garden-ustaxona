# Garden Retsept Atlasi — statik sayt generatori.
# data/dishes.json (yagona "baza") dan o'qiydi va site/index.html ni quradi.
# dishes.json'ni bevosita admin panel (admin/server.py) tahrirlaydi — bu skript
# faqat OQIYDI, hech qachon dishes.json'ni bu yerdan yozmaydi (buni sync_iiko.py qiladi).

import json
import time
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "dishes.json"
SITE_DIR = ROOT / "docs"
TEMPLATE_FILE = Path(__file__).with_name("template.html")

# Bo'limlar mijozlar menyusi (menu.olimpgarden.uz) bilan BIR XIL bo'lishi uchun:
# iikodagi xom guruh nomi -> menyudagi o'zbekcha bo'lim nomi.
# Manba: GardenMenu/scripts/build_menu_data.py (GROUP_TO_CATEGORY) va
#        GardenMenu/scripts/generate_menu.py (CATEGORY_LABEL, CATEGORY_ORDER).
GROUP_TO_CATEGORY = {
    "Сояли салатлар": "Salat", "Маянез салатлар": "Salat", "Свежый салатлар": "Salat",
    "Салёоный салатлар": "Salat", "Дисерт салат": "Salat", "Салат прочее": "Salat", "Салат": "Salat",
    "1-таом": "1-taomlar",
    "2-таом": "2-taomlar", "Мясной.": "2-taomlar",
    "Мариновка": "Shashliklar", "Шашлык на мангале": "Shashliklar", "Мангалы соусы": "Shashliklar",
    "Ассорти на мангале": "Assorti taomlar", "Ассорти блюда": "Assorti taomlar",
    "Баликлар": "Балик таомлар",
    "Барак": "Бараклар",
    "Сомса": "Somsa",
    "Нон чай": "Нон чой", "Гарден Перожний": "Shirinliklar",
    "Гарден Сет": "Сетлар",
    "Напитка": "Ichimlik", "Махито": "Ichimlik", "Кактейл": "Ichimlik", "Айронлар": "Ichimlik",
    "Табий шарбат": "Ichimlik", "Фруктовый чай": "Ichimlik", "Чакка чукка": "Ichimlik",
    "БАР 4": "Ichimlik", "Шоколад-комплимент": "Ichimlik", "Гарден Бутка": "Ichimlik",
    "Кофе": "Бариста", "Бариста дисерт": "Бариста", "Бариста марожный": "Бариста",
    "Дисерт кухня": "Shirinliklar",
    "Фрукты": "Mevalar",
    "Бургер": "1-taomlar",
    "Стейк": "2-taomlar",
    "Прочее": "Assorti taomlar",
}

CATEGORY_LABEL = {
    "Нон чой": "Non va choy", "Бариста": "Barista", "Salat": "Salatlar",
    "Бараклар": "Baraklar", "Somsa": "Somsa", "1-taomlar": "Birinchi taomlar",
    "2-taomlar": "Ikkinchi taomlar", "Assorti taomlar": "Assorti taomlar",
    "Mevalar": "Mevalar", "Shashliklar": "Shashliklar", "Shirinliklar": "Shirinliklar",
    "Ichimlik": "Ichimliklar", "Балик таомлар": "Baliq taomlari", "Сетлар": "Setlar",
}

CATEGORY_ORDER = [
    "Нон чой", "Бариста", "Salat", "Бараклар", "Somsa", "1-taomlar", "2-taomlar",
    "Assorti taomlar", "Mevalar", "Shashliklar", "Shirinliklar", "Ichimlik",
    "Балик таомлар", "Сетлар",
]

# Ko'rinadigan bo'lim nomlari shu tartibda; menyuda yo'q (xom) guruhlar oxirida.
LABEL_ORDER = [CATEGORY_LABEL[c] for c in CATEGORY_ORDER]


def display_group(iiko_group):
    """iikodagi guruh nomini menyudagi o'zbekcha bo'lim nomiga aylantiradi.
    Menyuda mos keladigani bo'lmasa (masalan faqat oshxona ichidagi yarim tayyor
    guruhlar), xom nomi o'zgarishsiz qoladi — ma'lumot yo'qolmaydi."""
    cat = GROUP_TO_CATEGORY.get(iiko_group)
    return CATEGORY_LABEL.get(cat, iiko_group) if cat else iiko_group


def group_order_key(name):
    try:
        return (0, LABEL_ORDER.index(name))
    except ValueError:
        return (1, name)


def fmt_price(p):
    return f"{round(p):,}".replace(",", " ") + " so'm"


def build_data():
    dishes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    dishes = [d for d in dishes if d.get("active", True)]

    by_group = OrderedDict()
    for d in dishes:
        by_group.setdefault(display_group(d["group"]), []).append(d)

    groups = []
    for gname in sorted(by_group.keys(), key=group_order_key):
        items = sorted(by_group[gname], key=lambda x: x["name"])
        filled = sum(1 for i in items if i.get("ingredients"))
        with_video = sum(1 for i in items if i.get("video"))
        groups.append({
            "name": gname,
            "items": items,
            "filled": filled,
            "withVideo": with_video,
        })

    total = len(dishes)
    total_filled = sum(1 for d in dishes if d.get("ingredients"))
    total_video = sum(1 for d in dishes if d.get("video"))
    total_photo = sum(1 for d in dishes if d.get("photo"))

    return {
        "groups": groups,
        "stats": {
            "total": total,
            "filled": total_filled,
            "video": total_video,
            "photo": total_photo,
        },
        "buildId": int(time.time()),
    }


def main():
    data = build_data()
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    html = template.replace("__DATA__", data_json)
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"OK: {len(data['groups'])} bo'lim, {data['stats']['total']} taom "
          f"({data['stats']['filled']} tarkibi to'ldirilgan, {data['stats']['video']} videosi bor) "
          f"-> {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
