from flask import Flask, render_template, request, redirect, url_for, session, flash
import json, os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret-key-change-it")

# مسارات ملفات البيانات
DATA_FOLDER = "data"
POSTS_FILE = os.path.join(DATA_FOLDER, "posts.json")
ADS_FILE = os.path.join(DATA_FOLDER, "ads.json")
SETTINGS_FILE = os.path.join(DATA_FOLDER, "settings.json")


# ---------- أدوات قراءة/حفظ آمنة ----------
def ensure_data_folder_and_files():
    os.makedirs(DATA_FOLDER, exist_ok=True)
    if not os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
    if not os.path.exists(ADS_FILE):
        with open(ADS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
    if not os.path.exists(SETTINGS_FILE):
        default = {"title": "مدونتي", "description": "أهلاً بك", "password": "admin"}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)


def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data
        except json.JSONDecodeError:
            # إصلاح بسيط: نعيد كتابة القيمة الافتراضية لو الملف تًلف
            with open(path, "w", encoding="utf-8") as f2:
                json.dump(default, f2, ensure_ascii=False, indent=4)
            return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ---------- وظائف للبوستس والإعلانات (مع ids ثابتة) ----------
def load_posts():
    posts = load_json(POSTS_FILE, [])
    changed = False
    # إذا بعض البوستات مفيهاش id نضيف id متسلسل
    max_id = 0
    for i, p in enumerate(posts):
        if not isinstance(p, dict):
            posts[i] = {"id": i + 1, "title": str(p), "content": ""}
            changed = True
        if "id" not in posts[i]:
            posts[i]["id"] = i + 1
            changed = True
        if isinstance(posts[i].get("id"), int) and posts[i]["id"] > max_id:
            max_id = posts[i]["id"]
    if changed:
        save_json(POSTS_FILE, posts)
    return posts


def get_next_post_id(posts):
    max_id = 0
    for p in posts:
        try:
            if int(p.get("id", 0)) > max_id:
                max_id = int(p.get("id", 0))
        except:
            continue
    return max_id + 1


def load_ads():
    ads = load_json(ADS_FILE, [])
    changed = False
    for i, a in enumerate(ads):
        if not isinstance(a, dict):
            ads[i] = {"id": i + 1, "content": str(a)}
            changed = True
        if "id" not in ads[i]:
            ads[i]["id"] = i + 1
            changed = True
    if changed:
        save_json(ADS_FILE, ads)
    return ads


def get_next_ad_id(ads):
    max_id = 0
    for a in ads:
        try:
            if int(a.get("id", 0)) > max_id:
                max_id = int(a.get("id", 0))
        except:
            continue
    return max_id + 1


def load_settings():
    default = {"title": "مدونتي", "description": "أهلاً بك", "password": "admin"}
    settings = load_json(SETTINGS_FILE, default)
    # If settings is accidentally a list, fix it
    if isinstance(settings, list):
        settings = default
        save_json(SETTINGS_FILE, settings)
    return settings


# ---------- حماية صفحات الأدمن ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        flash("يجب تسجيل الدخول أولاً", "error")
        return redirect(url_for("login"))
    return decorated


# ---------- المسارات ----------
@app.route("/")
def index():
    posts = load_posts()
    ads = load_ads()
    settings = load_settings()
    # عرض الأحدث أولاً
    posts_sorted = sorted(posts, key=lambda x: x.get("id", 0), reverse=True)
    return render_template("index.html", posts=posts_sorted, ads=ads, settings=settings)


@app.route("/post/<int:post_id>")
def post_view(post_id):
    posts = load_posts()
    ads = load_ads()
    settings = load_settings()
    post = next((p for p in posts if int(p.get("id", 0)) == post_id), None)
    if not post:
        return render_template("errors/404.html"), 404 if os.path.exists("templates/errors/404.html") else ("المقال غير موجود", 404)
    return render_template("post.html", post=post, ads=ads, settings=settings)


@app.route("/login", methods=["GET", "POST"])
def login():
    settings = load_settings()
    admin_password = settings.get("password", "admin")
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == admin_password:
            session["logged_in"] = True
            flash("تم تسجيل الدخول بنجاح", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("كلمة المرور غير صحيحة", "error")
    return render_template("admin/login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    flash("تم تسجيل الخروج", "info")
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def dashboard():
    posts = load_posts()
    ads = load_ads()
    settings = load_settings()
    # نعرض الأحدث أولاً
    posts_sorted = sorted(posts, key=lambda x: x.get("id", 0), reverse=True)
    return render_template("admin/dashboard.html", posts=posts_sorted, ads=ads, settings=settings)


@app.route("/admin/new_post", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        posts = load_posts()
        new_id = get_next_post_id(posts)
        posts.append({"id": new_id, "title": title, "content": content})
        save_json(POSTS_FILE, posts)
        flash("تمت إضافة المقال بنجاح", "success")
        return redirect(url_for("dashboard"))
    return render_template("admin/editor.html", action="new")


@app.route("/admin/edit_post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    posts = load_posts()
    post = next((p for p in posts if int(p.get("id", 0)) == post_id), None)
    if not post:
        flash("المقال غير موجود", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        post["title"] = request.form.get("title", post.get("title", "")).strip()
        post["content"] = request.form.get("content", post.get("content", "")).strip()
        save_json(POSTS_FILE, posts)
        flash("تم تعديل المقال", "success")
        return redirect(url_for("dashboard"))
    return render_template("admin/editor.html", action="edit", post=post)


@app.route("/admin/delete_post/<int:post_id>")
@login_required
def delete_post(post_id):
    posts = load_posts()
    new_posts = [p for p in posts if int(p.get("id", 0)) != post_id]
    if len(new_posts) != len(posts):
        save_json(POSTS_FILE, new_posts)
        flash("تم حذف المقال", "success")
    else:
        flash("المقال غير موجود", "error")
    return redirect(url_for("dashboard"))


@app.route("/admin/ads", methods=["GET", "POST"])
@login_required
def manage_ads():
    ads = load_ads()
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        new_id = get_next_ad_id(ads)
        ads.append({"id": new_id, "content": content})
        save_json(ADS_FILE, ads)
        flash("تمت إضافة الإعلان", "success")
        return redirect(url_for("manage_ads"))
    return render_template("admin/ads.html", ads=ads)


@app.route("/admin/delete_ad/<int:ad_id>")
@login_required
def delete_ad(ad_id):
    ads = load_ads()
    new_ads = [a for a in ads if int(a.get("id", 0)) != ad_id]
    if len(new_ads) != len(ads):
        save_json(ADS_FILE, new_ads)
        flash("تم حذف الإعلان", "success")
    else:
        flash("الإعلان غير موجود", "error")
    return redirect(url_for("manage_ads"))


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings = load_settings()
    if request.method == "POST":
        settings["title"] = request.form.get("title", settings.get("title", "")).strip()
        settings["description"] = request.form.get("description", settings.get("description", "")).strip()
        # لو تركت كلمة المرور فارغة، لا نغيّرها
        new_password = request.form.get("password", None)
        if new_password:
            settings["password"] = new_password
        save_json(SETTINGS_FILE, settings)
        flash("تم حفظ الإعدادات", "success")
        return redirect(url_for("dashboard"))
    return render_template("admin/settings.html", settings=settings)


# ---------- بداية التطبيق ----------
if __name__ == "__main__":
    ensure_data_folder_and_files()
    app.run(host="0.0.0.0", port=5000, debug=True)