from flask import Flask, render_template, request, redirect, url_for, flash

from app import database as db
from app import scraper
from app import telegram
from app import scheduler
from app.runner import run_job

app = Flask(__name__)
app.secret_key = "change-me-in-production"

CATEGORIES = [
    "computer_electronics",
    "furniture",
    "clothing",
    "kids",
    "sports",
    "books_media",
    "household",
    "other",
]


@app.route("/")
def index():
    jobs = db.list_jobs()
    listings = db.recent_listings(limit=60)
    return render_template("index.html", jobs=jobs, listings=listings)


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    if request.method == "POST":
        db.create_job(
            name=request.form["name"],
            feed_url=request.form["feed_url"],
            category=request.form.get("category", ""),
            keywords=request.form.get("keywords", ""),
            blacklist=request.form.get("blacklist", ""),
            interval_minutes=int(request.form.get("interval_minutes", 15)),
        )
        scheduler.refresh()
        flash("İş oluşturuldu.", "success")
        return redirect(url_for("index"))
    return render_template("job_form.html", job=None, categories=CATEGORIES)


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = db.get_job(job_id)
    if not job:
        flash("İş bulunamadı.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        db.update_job(
            job_id,
            name=request.form["name"],
            feed_url=request.form["feed_url"],
            category=request.form.get("category", ""),
            keywords=request.form.get("keywords", ""),
            blacklist=request.form.get("blacklist", ""),
            interval_minutes=int(request.form.get("interval_minutes", 15)),
            active=1 if request.form.get("active") == "on" else 0,
        )
        scheduler.refresh()
        flash("İş güncellendi.", "success")
        return redirect(url_for("index"))
    return render_template("job_form.html", job=job, categories=CATEGORIES)


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def job_delete(job_id):
    db.delete_job(job_id)
    scheduler.refresh()
    flash("İş silindi.", "success")
    return redirect(url_for("index"))


@app.route("/jobs/<int:job_id>/run-now", methods=["POST"])
def job_run_now(job_id):
    run_job(job_id)
    flash("İş manuel tetiklendi, sonuç için birkaç saniye bekleyin ve sayfayı yenileyin.", "success")
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_telegram":
            db.update_settings(
                telegram_bot_token=request.form.get("telegram_bot_token", ""),
                telegram_chat_id=request.form.get("telegram_chat_id", ""),
            )
            flash("Telegram ayarları kaydedildi.", "success")

        elif action == "test_telegram":
            s = db.get_settings()
            ok, err = telegram.test_connection(s.get("telegram_bot_token"), s.get("telegram_chat_id"))
            flash("Test mesajı gönderildi." if ok else f"Hata: {err}", "success" if ok else "error")

        elif action == "save_nebenan":
            db.update_settings(
                nebenan_username=request.form.get("nebenan_username", ""),
                nebenan_password=request.form.get("nebenan_password", ""),
            )
            flash("nebenan.de bilgileri kaydedildi.", "success")

        elif action == "login_nebenan":
            s = db.get_settings()
            ok, err = scraper.login_nebenan(s.get("nebenan_username"), s.get("nebenan_password"))
            from datetime import datetime
            db.update_settings(login_ok=1 if ok else 0,
                                last_login_at=datetime.utcnow().isoformat())
            flash("Giriş başarılı, session kaydedildi." if ok else f"Giriş başarısız: {err}",
                  "success" if ok else "error")

        return redirect(url_for("settings"))

    s = db.get_settings()
    return render_template("settings.html", settings=s, logged_in=scraper.is_logged_in())


if __name__ == "__main__":
    db.init_db()
    scheduler.start()
    app.run(host="0.0.0.0", port=5000)
