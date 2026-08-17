from app import database as db
from app import scraper
from app import telegram


def run_job(job_id):
    job = db.get_job(job_id)
    if not job or not job["active"]:
        return

    settings = db.get_settings()
    results, error = scraper.scrape_feed(job["feed_url"])

    if error:
        db.mark_job_run(job_id, f"HATA: {error}")
        return

    new_count = 0
    for item in results:
        if db.listing_exists(job_id, item["external_id"]):
            continue

        if not scraper.matches_filters(item["title"], job["keywords"], job["blacklist"]):
            continue

        db.add_listing(
            job_id, item["external_id"], item["title"],
            item["price"], item["url"], item["image_url"],
        )
        new_count += 1

        text = (
            f"🆕 {job['name']}\n"
            f"{item['title']}\n"
            f"{item['price']}\n"
            f"{item['url']}"
        )
        ok, err = telegram.send_message(
            settings.get("telegram_bot_token"),
            settings.get("telegram_chat_id"),
            text,
        )
        if ok:
            db.mark_notified(job_id, item["external_id"])

    db.mark_job_run(job_id, f"OK ({new_count} yeni ilan)")


def run_all_active_jobs():
    for job in db.list_jobs():
        if job["active"]:
            run_job(job["id"])
