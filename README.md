# Nebenan Notifier

nebenan.de marketplace ilanlarını takip edip yeni ilanları Telegram'a bildiren,
basit web arayüzlü Docker uygulaması.

## Kurulum

```bash
git clone <bu-projeyi-koy> nebenan-notifier
cd nebenan-notifier
docker compose up -d --build
```

Arayüz: `http://<sunucu-ip>:5000`

## İlk kurulum sırası

1. **Ayarlar** sayfasında Telegram bot token + chat id gir, "Test mesajı gönder" ile doğrula.
2. Aynı sayfada nebenan.de kullanıcı adı/şifreni gir, "nebenan.de'ye giriş yap" butonuna bas.
   - Giriş başarısız olursa (`app/scraper.py` içindeki `SELECTORS` doğrulanmadığı için
     büyük ihtimalle ilk denemede başarısız olacaktır) aşağıdaki "Selector Doğrulama" adımını uygula.
3. **Yeni İş** ile takip etmek istediğin feed URL'sini, anahtar kelimeleri, kara listeyi
   ve kontrol aralığını gir.
4. Panelde "Şimdi çalıştır" ile ilk testi manuel tetikle, bulunan ilan kartlarını kontrol et.

## Selector Doğrulama (kritik adım)

Bu proje nebenan.de'nin gerçek HTML yapısı incelenmeden yazıldı çünkü site bu ortamdan
erişime kapalı. Container içinde şunu çalıştır:

```bash
docker compose exec nebenan-notifier python -m app.scraper debug "https://nebenan.de/feed/marketplace?content_types=marketplace_free&category=computer_electronics"
```

Bu, `data/debug_page.html` dosyasına sayfanın gerçek HTML'ini kaydeder. Bu dosyayı
tarayıcıda aç, ilan kartlarının ve login formunun gerçek CSS selector'larını
(`class`, `data-testid`, vb.) bul, `app/scraper.py` içindeki `SELECTORS` sözlüğünü
buna göre güncelle, container'ı yeniden build et.

## Bilinen sınırlamalar

- Şifre veritabanında düz metin saklanır — sadece kişisel/lokal kullanım için uygundur.
- nebenan.de captcha veya 2FA gösterirse otomatik login akışı çalışmaz; bu durumda
  manuel login + `storage_state.json` kopyalama yöntemine geçilmesi gerekir
  (önceki mesajdaki Yöntem A).
- Kullanım şartlarına (ToS) uygunluk kullanıcının sorumluluğundadır.
