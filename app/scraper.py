"""
ÖNEMLİ / DOĞRULANMAMIŞ KISIMLAR:
Aşağıdaki CSS selector'lar (login formu ve ilan kartları için) nebenan.de'nin
gerçek DOM yapısı incelenmeden yazılmıştır -> ÇALIŞMAYABİLİR.
Kurulumdan sonra ilk çalıştırmada `python -m app.scraper debug` ile
gerçek sayfa HTML'ini indirip selector'ları güncellemen gerekir.

nebenan.de bir React SPA'dır: form elemanları sayfa yüklendikten sonra
JavaScript ile çizilir. Bu yüzden wait_for_selector ile elemanların
belirmesini bekleriz ve birden fazla olası selector deneriz.
"""

import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

STORAGE_STATE_PATH = os.environ.get("STORAGE_STATE_PATH", "data/storage_state.json")

LOGIN_URL = "https://nebenan.de/login"

# Gerçek bir Chrome tarayıcısını taklit etmek için kullanılan User-Agent.
# Playwright'ın varsayılan UA'si bot tespiti sistemleri tarafından kolayca tanınır.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

# Tarayıcı başlatma argümanları: bot tespitini aşmak için.
BROWSER_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
    "--window-size=1920,1080",
]

# Sayfa yüklendiğinde çalıştırılan gizli script: navigator.webdriver gibi
# bot işaretlerini gizler.
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['de-DE', 'de', 'en-US', 'en'] });
window.chrome = { runtime: {} };
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);
"""

# Birden fazla olası selector; sırayla denenir.
LOGIN_USERNAME_SELECTORS = [
    "input[name='email']",
    "input[type='email']",
    "input[name='username']",
    "input[name='login']",
    "input[autocomplete='email']",
    "input[autocomplete='username']",
    "input[placeholder*='mail' i]",
    "input[placeholder*='E-Mail' i]",
    "input[placeholder*='Benutzer' i]",
    "form input:first-of-type",
]

LOGIN_PASSWORD_SELECTORS = [
    "input[name='password']",
    "input[type='password']",
    "input[autocomplete='current-password']",
    "input[placeholder*='asswort' i]",
    "form input[type='password']",
]

LOGIN_SUBMIT_SELECTORS = [
    "button[type='submit']",
    "button[data-testid*='login' i]",
    "button[data-testid*='submit' i]",
    "input[type='submit']",
    "button:has-text('Anmelden')",
    "button:has-text('Einloggen')",
    "button:has-text('Login')",
    "form button",
]

# --- TODO: gerçek DOM'a göre doğrula ---
SELECTORS = {
    "listing_card": "[data-testid='marketplace-item'], article",
    "listing_title": "h2, h3, [data-testid='title']",
    "listing_price": "[data-testid='price']",
    "listing_link": "a",
    "listing_image": "img",
}
# ----------------------------------------


def _find_first(page, selectors, timeout=10000):
    """Verilen selector listesinden ilk eşleşeni bulur ve döner; yoksa None.
    Tüm selector'ları tek bir CSS grubu olarak birleştirir ve aynı anda bekler;
    böylece sırayla denemek yerine hepsini paralel arar."""
    combined = ", ".join(selectors)
    try:
        el = page.wait_for_selector(combined, timeout=timeout, state="visible")
        if el:
            return el
    except Exception:
        pass
    # Birleşik selector başarısız olursa, kısa timeout ile tek tek dene
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=2000, state="visible")
            if el:
                return el
        except Exception:
            continue
    return None


def is_logged_in():
    return os.path.exists(STORAGE_STATE_PATH)


def login_nebenan(username, password):
    """Kullanıcı adı/şifre ile otomatik giriş yapar, session'ı diske kaydeder.
    Site captcha/2FA gösterirse bu otomatik akış başarısız olur -> False döner."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=BROWSER_LAUNCH_ARGS)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="de-DE",
            extra_http_headers={
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        context.add_init_script(STEALTH_JS)
        page = context.new_page()
        try:
            resp = page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)

            # 403/503 kontrolü: site bot tespiti yapıyor olabilir
            if resp and resp.status in (403, 503):
                _save_debug_artifacts(page, "login_blocked")
                browser.close()
                return False, (
                    f"Site erişimi engellendi (HTTP {resp.status}). "
                    "nebenan.de bot koruması (Cloudflare vb.) devrede. "
                    "Daha sonra tekrar deneyin veya IP/VPN değiştirin."
                )

            # React uygulamasının formu çizmesi için biraz bekle
            username_el = _find_first(page, LOGIN_USERNAME_SELECTORS, timeout=15000)
            if not username_el:
                _save_debug_artifacts(page, "login_no_username")
                browser.close()
                return False, (
                    "Giriş formundaki e-posta alanı bulunamadı. "
                    "Sayfa tam yüklenmemiş olabilir veya giriş formunun yapısı farklı. "
                    "data/debug_page.html ve data/debug_login.png dosyalarını inceleyip "
                    "app/scraper.py içindeki selector listesini güncelle."
                )

            password_el = _find_first(page, LOGIN_PASSWORD_SELECTORS, timeout=10000)
            if not password_el:
                _save_debug_artifacts(page, "login_no_password")
                browser.close()
                return False, "Giriş formundaki şifre alanı bulunamadı."

            username_el.fill(username)
            password_el.fill(password)

            # Formu gönder: submit butonuna tıkla veya Enter'a bas
            submit_el = _find_first(page, LOGIN_SUBMIT_SELECTORS, timeout=5000)
            if submit_el:
                submit_el.click()
            else:
                password_el.press("Enter")

            # networkidle yerine domcontentloaded + kısa bekleme kullan;
            # React SPA'lerde networkidle asla tetiklenmeyebilir.
            try:
                page.wait_for_load_state("domcontentloaded", timeout=20000)
            except Exception:
                pass
            # Sayfanın yerleşmesi için ekstra bekleme
            page.wait_for_timeout(3000)

            # Login başarı kontrolü: login sayfasından ayrıldık mı?
            if "login" in page.url:
                _save_debug_artifacts(page, "login_stuck")
                browser.close()
                return False, (
                    "Giriş başarısız görünüyor (login sayfasında kaldı). "
                    "Captcha/2FA olabilir veya kullanıcı adı/şifre hatalı."
                )

            os.makedirs(os.path.dirname(STORAGE_STATE_PATH), exist_ok=True)
            context.storage_state(path=STORAGE_STATE_PATH)
            browser.close()
            return True, None
        except Exception as e:
            try:
                _save_debug_artifacts(page, "login_exception")
            except Exception:
                pass
            browser.close()
            return False, str(e)


def _save_debug_artifacts(page, label):
    """Hata ayıklama için sayfanın HTML'ini ve ekran görüntüsünü kaydeder."""
    os.makedirs("data", exist_ok=True)
    try:
        with open("data/debug_page.html", "w") as f:
            f.write(page.content())
    except Exception:
        pass
    try:
        page.screenshot(path=f"data/debug_{label}.png", full_page=True)
    except Exception:
        pass


def scrape_feed(feed_url):
    """Verilen URL'yi giriş yapılmış session ile açar, ilan kartlarını döner.
    Dönüş: liste of dict {external_id, title, price, url, image_url}"""
    if not is_logged_in():
        return None, "Önce nebenan.de girişi yapılmalı (Ayarlar sayfası)"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=BROWSER_LAUNCH_ARGS)
        context = browser.new_context(
            storage_state=STORAGE_STATE_PATH,
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="de-DE",
            extra_http_headers={
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        context.add_init_script(STEALTH_JS)
        page = context.new_page()
        try:
            page.goto(feed_url, wait_until="domcontentloaded", timeout=45000)

            # Sayfanın yerleşmesi için kısa bekleme
            page.wait_for_timeout(3000)

            if "login" in page.url:
                browser.close()
                return None, "Session geçersiz/süresi dolmuş, yeniden giriş gerekiyor"

            # İlan kartlarının yüklenmesini bekle
            try:
                page.wait_for_selector(SELECTORS["listing_card"], timeout=15000)
            except Exception:
                pass

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
            browser = p.chromium.launch(headless=True, args=BROWSER_LAUNCH_ARGS)
            context = browser.new_context(
                storage_state=STORAGE_STATE_PATH if is_logged_in() else None,
                user_agent=USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                locale="de-DE",
                extra_http_headers={
                    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            context.add_init_script(STEALTH_JS)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            html = page.content()
            with open("data/debug_page.html", "w") as f:
                f.write(html)
            try:
                page.screenshot(path="data/debug_page.png", full_page=True)
            except Exception:
                pass
            print("Sayfa HTML'i data/debug_page.html dosyasına kaydedildi.")
            print("Ekran görüntüsü data/debug_page.png dosyasına kaydedildi.")
            print("Bu dosyaları incele ve selector listelerini buna göre güncelle.")
            browser.close()
