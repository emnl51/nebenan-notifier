"""
ÖNEMLİ / DOĞRULANMAMIŞ KISIMLAR:
Aşağıdaki CSS selector'lar (login formu ve ilan kartları için) nebenan.de'nin
gerçek DOM yapısı incelenmeden yazılmıştır -> ÇALIŞMAYABİLİR.
Kurulumdan sonra ilk çalıştırmada `python -m app.scraper debug` ile
gerçek sayfa HTML'ini indirip selector'ları güncellemen gerekir.
"""

import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

STORAGE_STATE_PATH = os.environ.get("STORAGE_STATE_PATH", "data/storage_state.json")

LOGIN_URL = "https://nebenan.de/login"

# --- TODO: gerçek DOM'a göre doğrula ---
SELECTORS = {
    "login_username": "input[name='email']",
    "login_password": "input[name='password']",
    "login_submit": "button[type='submit']",
    "listing_card": "[data-testid='marketplace-item'], article",
    "listing_title": "h2, h3, [data-testid='title']",
    "listing_price": "[data-testid='price']",
    "listing_link": "a",
    "listing_image": "img",
}
# ----------------------------------------


def is_logged_in():
    return os.path.exists(STORAGE_STATE_PATH)


def login_nebenan(username, password):
    """Kullanıcı adı/şifre ile otomatik giriş yapar, session'ı diske kaydeder.
    Site captcha/2FA gösterirse bu otomatik akış başarısız olur -> False döner."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
            page.fill(SELECTORS["login_username"], username)
            page.fill(SELECTORS["login_password"], password)
            page.click(SELECTORS["login_submit"])
            page.wait_for_load_state("networkidle", timeout=30000)

            # Login başarı kontrolü: login sayfasından ayrıldık mı?
            if "login" in page.url:
                browser.close()
                return False, "Giriş başarısız görünüyor (login sayfasında kaldı). Captcha/2FA olabilir."

            os.makedirs(os.path.dirname(STORAGE_STATE_PATH), exist_ok=True)
            context.storage_state(path=STORAGE_STATE_PATH)
            browser.close()
            return True, None
        except Exception as e:
            browser.close()
            return False, str(e)


def scrape_feed(feed_url):
    """Verilen URL'yi giriş yapılmış session ile açar, ilan kartlarını döner.
    Dönüş: liste of dict {external_id, title, price, url, image_url}"""
    if not is_logged_in():
        return None, "Önce nebenan.de girişi yapılmalı (Ayarlar sayfası)"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        try:
            page.goto(feed_url, wait_until="networkidle", timeout=30000)

            if "login" in page.url:
                browser.close()
                return None, "Session geçersiz/süresi dolmuş, yeniden giriş gerekiyor"

            cards = page.query_selector_all(SELECTORS["listing_card"])
            results = []
            for card in cards:
                try:
                    link_el = card.query_selector(SELECTORS["listing_link"])
                    href = link_el.get_attribute("href") if link_el else None
                    if not href:
                        continue
                    external_id = href.rstrip("/").split("/")[-1]

                    title_el = card.query_selector(SELECTORS["listing_title"])
                    title = title_el.inner_text().strip() if title_el else "(başlıksız)"

                    price_el = card.query_selector(SELECTORS["listing_price"])
                    price = price_el.inner_text().strip() if price_el else ""

                    img_el = card.query_selector(SELECTORS["listing_image"])
                    image_url = img_el.get_attribute("src") if img_el else None

                    full_url = href if href.startswith("http") else f"https://nebenan.de{href}"

                    results.append({
                        "external_id": external_id,
                        "title": title,
                        "price": price,
                        "url": full_url,
                        "image_url": image_url,
                    })
                except Exception:
                    continue

            browser.close()
            return results, None
        except Exception as e:
            browser.close()
            return None, str(e)


def matches_filters(title, keywords, blacklist):
    text = title.lower()

    if blacklist:
        for word in [w.strip().lower() for w in blacklist.split(",") if w.strip()]:
            if word in text:
                return False

    if keywords:
        kw_list = [w.strip().lower() for w in keywords.split(",") if w.strip()]
        if kw_list and not any(k in text for k in kw_list):
            return False

    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        url = sys.argv[2] if len(sys.argv) > 2 else LOGIN_URL
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                storage_state=STORAGE_STATE_PATH if is_logged_in() else None
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            with open("data/debug_page.html", "w") as f:
                f.write(html)
            print("Sayfa HTML'i data/debug_page.html dosyasına kaydedildi.")
            print("Bu dosyayı incele ve SELECTORS sözlüğünü buna göre güncelle.")
            browser.close()
