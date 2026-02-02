# render_url_finder.py - bu faylni yarating
import requests
import sys

BOT_TOKEN = "8516651908:AAGnEFmwlTyOzgR7QA9gfonzTVl5tDC6WwY"


def test_url(url):
    """URL ni test qilish"""
    try:
        print(f"\n🔍 Tekshirilmoqda: {url}")

        # 1. Render app ishlayotganini tekshirish
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"✅ Render app ishlayapti")
        else:
            print(f"❌ Render app ishlamayapti (status: {response.status_code})")
            return False

        # 2. Webhook test qilish
        webhook_url = f"{url}/webhook/{BOT_TOKEN}"
        print(f"🌐 Webhook URL: {webhook_url}")

        test_response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            params={"url": webhook_url}
        )

        result = test_response.json()
        print(f"📊 Natija: {result.get('description', 'Noma lum')}")

        return result.get('ok', False)

    except requests.exceptions.ConnectionError:
        print(f"❌ Ulanish xatosi - App mavjud emas yoki ishlamayapti")
        return False
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        return False


if __name__ == "__main__":
    print("🔍 RENDER URL TEKSHIRISH")
    print("=" * 50)

    # Foydalanuvchidan URL sorash
    test_urls = [
        "https://nakrutka-bot.onrender.com",
        "https://nakrutka-bot-1234.onrender.com",
        "https://telegram-nakrutka.onrender.com",
        input("\nO'z URL ingizni kiriting: ").strip()
    ]

    for url in test_urls:
        if url and url.startswith("http"):
            success = test_url(url)
            if success:
                print(f"\n🎊 TOPILDI! To'g'ri URL: {url}")
                print(f"\n📋 set_webhook.py da quyidagicha o'zgartiring:")
                print(f'RENDER_URL = "{url}"')
                break