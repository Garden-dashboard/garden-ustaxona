# Garden Retsept Atlasi — admin panel.
# Har bir taom uchun: tarkib (ingredient) ro'yxati, tayyorlash videosi (URL),
# surat tasdiqlash/almashtirish, faol/faolsiz belgisi.
# data/dishes.json — yagona "baza"; bu server to'g'ridan-to'g'ri shu faylni o'qiydi/yozadi.

import functools
import json
import os
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, Response, session, redirect, url_for, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "dishes.json"
UPLOADS_DIR = ROOT / "docs" / "uploads"
LOGIN_PASSWORD = "200211"

app = Flask(__name__)
app.secret_key = "garden-ustaxona-mahalliy-sir-2026"  # faqat 127.0.0.1'da ishlaydi
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


LOGIN_PAGE = """<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kirish — Garden Retsept Atlasi</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#FAFAF7;font-family:'Segoe UI',sans-serif;}
.card{background:#fff;border:1px solid rgba(32,33,28,.14);border-radius:14px;padding:32px;width:100%;max-width:320px;box-shadow:0 10px 28px rgba(20,22,16,.10);}
h1{font-family:Georgia,serif;font-weight:600;font-size:21px;margin:0 0 18px;color:#20211C;text-align:center;}
input{width:100%;font-size:15px;padding:11px 14px;border-radius:8px;border:1.5px solid rgba(32,33,28,.26);margin-bottom:14px;box-sizing:border-box;}
button{width:100%;font-size:14px;font-weight:700;padding:11px;border-radius:8px;border:none;background:#3D6B4C;color:#fff;cursor:pointer;}
.err{color:#B5581F;font-size:13px;text-align:center;margin-bottom:10px;}
</style></head>
<body><form class="card" method="POST">
  <h1>Garden Retsept Atlasi</h1>
  __ERROR__
  <input type="password" name="password" placeholder="Parol" autofocus required>
  <button type="submit">Kirish</button>
</form></body></html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password") == LOGIN_PASSWORD:
            session["authed"] = True
            session.permanent = True
            return redirect(url_for("index"))
        error = '<div class="err">Parol noto\'g\'ri</div>'
    return LOGIN_PAGE.replace("__ERROR__", error)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def load_dishes():
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_dishes(dishes):
    DATA_FILE.write_text(json.dumps(dishes, ensure_ascii=False, indent=1), encoding="utf-8")


@app.get("/")
@login_required
def index():
    return Response(open(Path(__file__).with_name("index.html"), encoding="utf-8").read(), mimetype="text/html")


@app.get("/uploads/<path:filename>")
@login_required
def serve_upload(filename):
    return send_from_directory(UPLOADS_DIR, filename)


@app.get("/api/dishes")
@login_required
def api_dishes():
    return jsonify(load_dishes())


@app.post("/api/dish/<dish_id>")
@login_required
def save_dish(dish_id):
    patch = request.get_json() or {}
    dishes = load_dishes()
    found = None
    for d in dishes:
        if d["id"] == dish_id:
            found = d
            break
    if not found:
        return jsonify({"ok": False, "error": "Taom topilmadi"}), 404

    if "ingredients" in patch:
        found["ingredients"] = patch["ingredients"]
    if "video" in patch:
        found["video"] = patch["video"] or None
    if "active" in patch:
        found["active"] = bool(patch["active"])
    if "confirmPhoto" in patch and patch["confirmPhoto"]:
        # taklif qilingan suratni haqiqiy surat sifatida tasdiqlash
        if found.get("suggestedPhoto"):
            found["photo"] = found["suggestedPhoto"]
            found["suggestedPhoto"] = None
            found["photoStatus"] = "confirmed"
    if "rejectPhoto" in patch and patch["rejectPhoto"]:
        found["suggestedPhoto"] = None
        found["photoStatus"] = "missing"

    save_dishes(dishes)
    return jsonify({"ok": True, "dish": found})


@app.post("/api/dish/<dish_id>/photo")
@login_required
def upload_photo(dish_id):
    file = request.files.get("file")
    if not file:
        return jsonify({"ok": False, "error": "Fayl topilmadi"}), 400
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    file.save(UPLOADS_DIR / fname)

    dishes = load_dishes()
    for d in dishes:
        if d["id"] == dish_id:
            d["photo"] = f"uploads/{fname}"
            d["suggestedPhoto"] = None
            d["photoStatus"] = "confirmed"
            save_dishes(dishes)
            return jsonify({"ok": True, "url": f"uploads/{fname}"})
    return jsonify({"ok": False, "error": "Taom topilmadi"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5056))
    print(f"Garden Retsept Atlasi admin: http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
