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
SITE_DIR = ROOT / "site"
TEMPLATE_FILE = Path(__file__).with_name("template.html")

# Guruhlarni mantiqiy tartibda ko'rsatish uchun ustuvorlik ro'yxati — qolganlari
# (bu yerda yo'qlar) soni bo'yicha kamayish tartibida qo'shiladi.
GROUP_PRIORITY = [
    "1-таом", "2-таом", "Ассорти блюда", "Мясной.",
    "Шашлык на мангале", "Ассорти на мангале", "Стейк", "Мариновка", "Мангалы соусы",
    "Барак", "Сомса", "Баликлар",
    "Сояли салатлар", "Маянез салатлар", "Свежый салатлар", "Салёоный салатлар",
    "Дисерт салат", "Салат прочее",
    "Нон чай", "Гарден Перожний", "Фрукты",
    "Гарден Сет", "Гарден Бутка",
    "Напитка", "Махито", "Кактейл", "Айронлар", "Табий шарбат", "Фруктовый чай",
    "Чакка чукка", "Барное прочее", "БАР 4", "Шоколад-комплимент",
    "Кофе", "Бариста дисерт", "Бариста марожный",
    "Дисерт кухня", "Бургер", "Прочее",
]


def group_order_key(name):
    try:
        return (0, GROUP_PRIORITY.index(name))
    except ValueError:
        return (1, name)


def fmt_price(p):
    return f"{round(p):,}".replace(",", " ") + " so'm"


def build_data():
    dishes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    dishes = [d for d in dishes if d.get("active", True)]

    by_group = OrderedDict()
    for d in dishes:
        by_group.setdefault(d["group"], []).append(d)

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
