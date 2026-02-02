import requests

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8516651908:AAGnEFmwlTyOzgR7QA9gfonzTVl5tDC6WwY"
RENDER_URL = "https://nakrutka-bot.onrender.com"  # O'z app nomingiz


# ==================== WEBHOOK O'RNATISH ====================
def set_webhook():
    """Telegram webhook ni o'rnatish"""
    try:
        # Webhook URL ni tayyorlash
        webhook_url = f"{RENDER_URL}/webhook/{BOT_TOKEN}"

        print("🔄 Webhook o'rnatilmoqda...")
        print(f"📱 Bot Token: {BOT_TOKEN[:10]}...")
        print(f"🌐 Webhook URL: {webhook_url}")

        # Telegram API ga so'rov
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            params={"url": webhook_url}
        )

        # Natijani ko'rsatish
        result = response.json()
        print("\n" + "=" * 50)
        print("📊 NATIJA:")
        print(f"✅ Muvaffaqiyat: {result.get('ok', False)}")
        print(f"📝 Xabar: {result.get('description', 'Noma lum')}")

        if result.get('ok'):
            print("\n🎉 Webhook muvaffaqiyatli o'rnatildi!")
            print("🤖 Bot endi Render.com da ishlaydi.")
        else:
            print("\n❌ Webhook o'rnatilmadi!")
            print("ℹ️ Sabab:", result.get('description'))

    except Exception as e:
        print(f"\n❌ Xatolik yuz berdi: {e}")
        print("🔧 Tuzatish uchun:")
        print("1. Bot tokenini tekshiring")
        print("2. Render URL ni tekshiring")
        print("3. Internet ulanishini tekshiring")


# ==================== WEBHOOK MA'LUMOTLARNI TEKSHIRISH ====================
def get_webhook_info():
    """Webhook ma'lumotlarini olish"""
    try:
        print("\n" + "=" * 50)
        print("🔍 Webhook ma'lumotlari olinmoqda...")

        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        )

        info = response.json()
        if info.get('ok'):
            webhook_info = info.get('result', {})

            print("\n📋 WEBHOOK MA'LUMOTLARI:")
            print(f"🔗 URL: {webhook_info.get('url', 'Yo q')}")
            print(f"✅ Faol: {webhook_info.get('pending_update_count', 0)} ta kutayotgan so'rov")
            print(f"📅 Oxirgi xato: {webhook_info.get('last_error_date', 'Yo q')}")
            print(f"💬 Xato xabari: {webhook_info.get('last_error_message', 'Yo q')}")
            print(f"📊 Max. ulanishlar: {webhook_info.get('max_connections', 'Noma lum')}")
        else:
            print("❌ Webhook ma'lumotlari olinmadi")

    except Exception as e:
        print(f"❌ Xatolik: {e}")


# ==================== WEBHOOK NI O'CHIRISH ====================
def delete_webhook():
    """Webhook ni o'chirish (polling uchun)"""
    try:
        print("\n" + "=" * 50)
        print("🗑️ Webhook o'chirilmoqda...")

        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        )

        result = response.json()
        print(f"✅ Natija: {result.get('description', 'Noma lum')}")

    except Exception as e:
        print(f"❌ Xatolik: {e}")


# ==================== ASOSIY FUNKSIYA ====================
if __name__ == "__main__":
    print("🤖 TELEGRAM BOT WEBHOOK O'RNATISH")
    print("=" * 50)

    # Foydalanuvchidan tanlov
    print("\nTanlang:")
    print("1. Webhook o'rnatish")
    print("2. Webhook ma'lumotlarini ko'rish")
    print("3. Webhook o'chirish (polling uchun)")
    print("4. Hammasini bajarish")

    choice = input("\nTanlovingiz (1-4): ").strip()

    if choice == "1":
        set_webhook()
    elif choice == "2":
        get_webhook_info()
    elif choice == "3":
        delete_webhook()
    elif choice == "4":
        print("\n" + "=" * 50)
        print("🔄 Hammasini bajarish...")
        delete_webhook()
        set_webhook()
        get_webhook_info()
    else:
        print("❌ Noto'g'ri tanlov!")