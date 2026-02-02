import asyncio
import logging
import sqlite3
import re
import os
from datetime import datetime
from aiohttp import web

# ==================== AIOGRAM IMPORTLARI ====================
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ==================== KONFIGURATSIYA ====================
BOT_TOKEN = os.getenv('BOT_TOKEN', "8516651908:AAGnEFmwlTyOzgR7QA9gfonzTVl5tDC6WwY")
ADMINS = [8579193650]  # O'z ID raqamingizni qo'ying

# MAJBURIY OBUNA KANALLARI
REQUIRED_CHANNELS = ["@nakurtka_top"]

# Narxlar (so'mda) - Instagram uchun
INSTAGRAM_PRICES = {
    'likes': {
        '1000 ta': 25000,
        '1500 ta': 38000,
        '2000 ta': 50000,
        '3000 ta': 75000,
        '3000+ ta': 'admin'
    },
    'followers': {
        '1000 ta': 25000,
        '1500 ta': 38000,
        '2000 ta': 50000,
        '3000 ta': 75000,
        '3000+ ta': 'admin'
    },
    'views': {
        '1000 ta': 3000,
        '5000 ta': 12000,
        '10000 ta': 20000,
        '50000 ta': 80000
    },
    'comments': {
        '10 ta': 15000,
        '50 ta': 60000,
        '100 ta': 100000
    }
}

# Narxlar (so'mda) - Telegram uchun
TELEGRAM_PRICES = {
    'followers': {
        '1000 ta': 50000,
        '2000 ta': 95000,
        '3000 ta': 140000,
        '3000+ ta': 'admin'
    }
}

# To'lov kartalari - SIZNING KARTANGIZ
PAYMENT_CARDS = {
    'uzum': '4916990341229786',  # SIZNING KARTANGIZ
}


# ==================== STATES ====================
class OrderStates(StatesGroup):
    choosing_platform = State()
    choosing_service = State()
    choosing_quantity = State()
    waiting_screenshot = State()
    waiting_username = State()
    waiting_link = State()
    waiting_phone = State()


# ==================== BOT INIT ====================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ==================== DATABASE ====================
def get_db_path():
    """Render uchun database yo'lini aniqlash"""
    if 'RENDER' in os.environ:
        # Render.com da
        os.makedirs('/opt/render/project/src/data', exist_ok=True)
        return '/opt/render/project/src/data/nakrutka_bot.db'
    else:
        # Local da
        os.makedirs('data', exist_ok=True)
        return 'data/nakrutka_bot.db'


def init_database():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       user_id
                       INTEGER
                       PRIMARY
                       KEY,
                       username
                       TEXT,
                       full_name
                       TEXT,
                       phone
                       TEXT,
                       join_date
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       subscribed
                       BOOLEAN
                       DEFAULT
                       FALSE
                   )
                   ''')

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS orders
                   (
                       order_id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       user_id
                       INTEGER,
                       platform
                       TEXT,
                       service_type
                       TEXT,
                       quantity
                       TEXT,
                       amount
                       INTEGER,
                       username
                       TEXT,
                       link
                       TEXT,
                       phone
                       TEXT,
                       status
                       TEXT
                       DEFAULT
                       'pending',
                       payment_screenshot
                       TEXT,
                       payment_date
                       TIMESTAMP,
                       admin_check_date
                       TIMESTAMP,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES users
                   (
                       user_id
                   )
                       )
                   ''')

    conn.commit()
    conn.close()
    print(f"✅ Database yaratildi: {db_path}")


# ==================== KEYBOARDS ====================
def get_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    for channel in REQUIRED_CHANNELS:
        builder.button(
            text=f"📢 {channel} kanaliga obuna bo'lish",
            url=f"https://t.me/{channel[1:]}"
        )
    builder.button(
        text="✅ Obuna bo'ldim - Tekshirish",
        callback_data="check_subscription"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Instagram Nakrutka")
    builder.button(text="📲 Telegram Nakrutka")
    builder.button(text="💻 Maxsus Xizmatlar")
    builder.button(text="📢 Reklama Berish")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_admin_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Statistika")
    builder.button(text="📋 Buyurtmalar")
    builder.button(text="🏠 Foydalanuvchi menyusi")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_instagram_services():
    builder = ReplyKeyboardBuilder()
    builder.button(text="👍 Instagram Likes")
    builder.button(text="👥 Instagram Followers")
    builder.button(text="👁️ Instagram Views")
    builder.button(text="💬 Instagram Comments")
    builder.button(text="⬅️ Orqaga")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_telegram_services():
    builder = ReplyKeyboardBuilder()
    builder.button(text="👥 Telegram Followers")
    builder.button(text="⬅️ Orqaga")
    builder.adjust(1, 1)
    return builder.as_markup(resize_keyboard=True)


def get_back_button():
    builder = ReplyKeyboardBuilder()
    builder.button(text="⬅️ Orqaga")
    return builder.as_markup(resize_keyboard=True)


def get_payment_confirmation_keyboard(order_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"confirm_{order_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"cancel_{order_id}")
    return builder.as_markup()


def get_quantity_keyboard(platform, service_type):
    builder = ReplyKeyboardBuilder()
    if platform == 'instagram':
        prices = INSTAGRAM_PRICES[service_type]
    else:  # telegram
        prices = TELEGRAM_PRICES[service_type]

    for quantity in prices.keys():
        builder.button(text=quantity)
    builder.button(text="⬅️ Orqaga")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_contact_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="👨‍💼 Admin bilan bog'lanish", url="https://t.me/Nakurtkatop_bot")
    return builder.as_markup()


# ==================== FUNCTIONS ====================
async def check_user_subscription(user_id: int) -> bool:
    """Kanalga obuna bo'lganligini tekshirish"""
    try:
        for channel in REQUIRED_CHANNELS:
            if channel.startswith('@'):
                channel_username = channel[1:]
            else:
                channel_username = channel

            try:
                chat_member = await bot.get_chat_member(f"@{channel_username}", user_id)
                print(f"📊 Kanal: @{channel_username}, User: {user_id}, Status: {chat_member.status}")

                if chat_member.status == 'left':
                    print(f"❌ Foydalanuvchi {user_id} kanalga obuna emas")
                    return False
                else:
                    print(f"✅ Foydalanuvchi {user_id} kanalga obuna")
                    return True
            except Exception as e:
                print(f"⚠️ Kanal tekshirishda xatolik: {e}")
                # Test uchun TRUE qaytarish
                return True
        return False
    except Exception as e:
        print(f"⚠️ Umumiy xatolik: {e}")
        return True


def save_user(user_id, username, full_name, subscribed=False):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, username, full_name, subscribed) VALUES (?, ?, ?, ?)',
        (user_id, username, full_name, subscribed)
    )
    conn.commit()
    conn.close()


def update_user_subscription(user_id, subscribed):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET subscribed = ? WHERE user_id = ?', (subscribed, user_id))
    conn.commit()
    conn.close()


def is_user_subscribed(user_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT subscribed FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1


def create_order(user_id, platform, service_type, quantity, amount):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    if amount == 'admin':
        amount_value = 0
    else:
        amount_value = amount

    cursor.execute(
        'INSERT INTO orders (user_id, platform, service_type, quantity, amount, status) VALUES (?, ?, ?, ?, ?, "pending")',
        (user_id, platform, service_type, quantity, amount_value)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def update_order_info(order_id, username, link, phone):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE orders SET username = ?, link = ?, phone = ? WHERE order_id = ?',
        (username, link, phone, order_id)
    )
    conn.commit()
    conn.close()


def update_order_payment(order_id, file_path):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE orders SET payment_screenshot = ?, payment_date = CURRENT_TIMESTAMP WHERE order_id = ?',
        (file_path, order_id)
    )
    conn.commit()
    conn.close()


def update_order_status(order_id, status):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    if status == 'confirmed':
        cursor.execute(
            'UPDATE orders SET status = ?, admin_check_date = CURRENT_TIMESTAMP WHERE order_id = ?',
            (status, order_id)
        )
    else:
        cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', (status, order_id))
    conn.commit()
    conn.close()


def get_order_by_id(order_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order


def get_statistics():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
    subscribed_users = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(*) FROM orders')
    total_orders = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(amount) FROM orders WHERE status = "confirmed"')
    total_income = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"')
    pending_orders = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(*) FROM orders WHERE DATE(payment_date) = DATE("now") AND status = "confirmed"')
    today_orders = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(amount) FROM orders WHERE DATE(payment_date) = DATE("now") AND status = "confirmed"')
    today_income = cursor.fetchone()[0] or 0

    conn.close()

    return {
        'total_users': total_users,
        'subscribed_users': subscribed_users,
        'total_orders': total_orders,
        'total_income': total_income,
        'pending_orders': pending_orders,
        'today_orders': today_orders,
        'today_income': today_income
    }


def get_pending_orders():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
                   SELECT o.*, u.username, u.full_name
                   FROM orders o
                            LEFT JOIN users u ON o.user_id = u.user_id
                   WHERE o.status = "pending"
                   ORDER BY o.payment_date DESC
                   ''')
    orders = cursor.fetchall()
    conn.close()
    return orders


async def save_payment_screenshot(file_id, order_id):
    """Rasmni saqlash (Render uchun moslashtirilgan)"""
    try:
        # Fayl nomini yaratish
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"payment_{order_id}_{timestamp}.jpg"

        # Render uchun papka yo'li
        if 'RENDER' in os.environ:
            save_dir = '/opt/render/project/src/data/payments'
        else:
            save_dir = 'data/payments'

        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, file_name)

        # Rasmni yuklab olish va saqlash
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_path)

        return file_path
    except Exception as e:
        print(f"❌ Rasmni saqlashda xatolik: {e}")
        return None


# ==================== HANDLERS ====================
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Noma'lum"
    full_name = message.from_user.full_name or "Noma'lum"

    print(f"🚀 Yangi foydalanuvchi: {full_name} (@{username})")

    save_user(user_id, username, full_name, False)
    is_subscribed = await check_user_subscription(user_id)

    if is_subscribed:
        update_user_subscription(user_id, True)
        welcome_text = f"""✅ <b>Xush kelibsiz, {full_name}!</b>

🤖 <b>Nakrutka Botiga</b> xush kelibsiz!

📊 <b>Bizning xizmatlar:</b>
• 📱 Instagram Nakrutka
• 📲 Telegram Nakrutka  
• 💻 Maxsus Xizmatlar
• 📢 Reklama Xizmatlari

⚡ <b>Tez va arzon narxlarda!</b>
💯 <b>Kafolat bilan ishlaymiz!</b>

<b>Quyidagi tugmalardan birini tanlang:</b>"""
        await message.answer(welcome_text, reply_markup=get_main_menu())
    else:
        await ask_for_subscription(message)


async def ask_for_subscription(message: Message):
    subscription_text = f"""👋 <b>Assalomu alaykum {message.from_user.full_name}!</b>

🤖 <b>Nakrutka Botiga</b> xush kelibsiz!

⚠️ <b>Botdan foydalanish uchun MAJBURIY kanalga obuna bo'ling:</b>

✅ @nakurtka_top

<b>Qadamlar:</b>
1️⃣ Yuqoridagi kanalga obuna bo'ling
2️⃣ "✅ Obuna bo'ldim - Tekshirish" tugmasini bosing
3️⃣ Botdan foydalanishni boshlang

❗️ <b>DIQQAT:</b> Agar obuna bo'lmasangiz, bot ishlamaydi!"""
    await message.answer(subscription_text, reply_markup=get_subscription_keyboard())


@dp.callback_query(F.data == "check_subscription")
async def verify_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(user_id)

    if is_subscribed:
        update_user_subscription(user_id, True)
        await callback.message.edit_text(
            "✅ <b>Tabriklaymiz! Siz kanalga obuna bo'ldingiz.</b>\n\n" +
            "🤖 Endi botdan to'liq foydalanishingiz mumkin!",
            reply_markup=None
        )
        welcome_text = f"""✅ <b>Xush kelibsiz, {callback.from_user.full_name}!</b>
🤖 <b>Nakrutka Botiga</b> xush kelibsiz!
📊 <b>Bizning xizmatlar:</b>
• 📱 Instagram Nakrutka
• 📲 Telegram Nakrutka  
• 💻 Maxsus Xizmatlar
• 📢 Reklama Xizmatlari
<b>Quyidagi tugmalardan birini tanlang:</b>"""
        await callback.message.answer(welcome_text, reply_markup=get_main_menu())
    else:
        await callback.answer(
            "❌ Hali kanalga obuna bo'lmadingiz!\n" +
            "Iltimos, kanalga obuna bo'ling va yana tekshiring.",
            show_alert=True
        )


@dp.message(F.text == "📱 Instagram Nakrutka")
async def instagram_nakrutka(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    await message.answer(
        "📱 <b>Instagram Nakrutka Xizmatlari</b>\n\n"
        "Instagram uchun quyidagi nakrutka turlaridan birini tanlang:\n\n"
        "👍 <b>Instagram Likes</b> - Postingizga like lar\n"
        "👥 <b>Instagram Followers</b> - Obunachilar\n"
        "👁️ <b>Instagram Views</b> - Ko'rishlar soni\n"
        "💬 <b>Instagram Comments</b> - Izohlar",
        reply_markup=get_instagram_services()
    )
    await state.update_data(platform='instagram')
    await state.set_state(OrderStates.choosing_service)


@dp.message(F.text == "📲 Telegram Nakrutka")
async def telegram_nakrutka(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    await message.answer(
        "📲 <b>Telegram Nakrutka Xizmatlari</b>\n\n"
        "Telegram uchun quyidagi nakrutka turlaridan birini tanlang:\n\n"
        "👥 <b>Telegram Followers</b> - Obunachilar\n\n"
        "📊 <b>Narxlar:</b>\n"
        "• 1000 ta Followers - 50,000 so'm\n"
        "• 2000 ta Followers - 95,000 so'm\n"
        "• 3000 ta Followers - 140,000 so'm\n"
        "• 3000+ ta Followers - Admin bilan kelishish",
        reply_markup=get_telegram_services()
    )
    await state.update_data(platform='telegram')
    await state.set_state(OrderStates.choosing_service)


@dp.message(OrderStates.choosing_service)
async def choose_service(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    data = await state.get_data()
    platform = data.get('platform')

    if platform == 'instagram':
        service_map = {
            '👍 Instagram Likes': 'likes',
            '👥 Instagram Followers': 'followers',
            '👁️ Instagram Views': 'views',
            '💬 Instagram Comments': 'comments'
        }
    else:
        service_map = {'👥 Telegram Followers': 'followers'}

    if message.text not in service_map:
        await message.answer("❌ <b>Iltimos, tugmalardan birini tanlang!</b>")
        return

    service_type = service_map[message.text]
    await state.update_data(service_type=service_type)

    if platform == 'instagram':
        prices = INSTAGRAM_PRICES[service_type]
        platform_name = "Instagram"
    else:
        prices = TELEGRAM_PRICES[service_type]
        platform_name = "Telegram"

    text = f"📊 <b>{platform_name} {message.text.split(' ')[1]} Narxlari:</b>\n\n"
    for quantity, price in prices.items():
        if price == 'admin':
            text += f"• {quantity}: <b>Admin bilan kelishish</b>\n"
        else:
            text += f"• {quantity}: <b>{price:,} so'm</b>\n"
    text += "\n<b>Miqdorni tanlang:</b>"
    await message.answer(text, reply_markup=get_quantity_keyboard(platform, service_type))
    await state.set_state(OrderStates.choosing_quantity)


@dp.message(OrderStates.choosing_quantity)
async def choose_quantity(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    data = await state.get_data()
    platform = data.get('platform')
    service_type = data.get('service_type')

    if platform == 'instagram':
        prices = INSTAGRAM_PRICES[service_type]
    else:
        prices = TELEGRAM_PRICES[service_type]

    if message.text not in prices:
        await message.answer("❌ <b>Iltimos, tugmalardan birini tanlang!</b>")
        return

    quantity = message.text
    amount = prices[quantity]
    await state.update_data(quantity=quantity, amount=amount)

    if amount == 'admin':
        admin_text = f"""👑 <b>ADMIN BILAN BOG'LANISH</b>
📱 <b>Platforma:</b> {'Instagram' if platform == 'instagram' else 'Telegram'}
📊 <b>Xizmat turi:</b> {service_type.capitalize()}
🔢 <b>Miqdor:</b> {quantity}
💰 <b>Narx:</b> Admin bilan kelishiladi
📞 <b>Admin bilan bog'laning:</b>
🤖 @nakurtkatop_bot
⚡ <b>Tez aloqa va yaxshi narxlar kafolatlanadi!</b>"""
        await message.answer(admin_text, reply_markup=get_contact_admin_keyboard())
        await state.clear()
        return

    order_id = create_order(user_id, platform, service_type, quantity, amount)
    await state.update_data(order_id=order_id)
    platform_name = 'Instagram' if platform == 'instagram' else 'Telegram'

    payment_text = f"""💰 <b>TO'LOV MA'LUMOTLARI</b>
🛒 <b>Buyurtma ID:</b> #{order_id}
📱 <b>Platforma:</b> {platform_name}
📊 <b>Xizmat turi:</b> {service_type.capitalize()}
🔢 <b>Miqdor:</b> {quantity}
💸 <b>Summa:</b> {amount:,} so'm
💳 <b>TO'LOV KARTASI:</b>
<b>Uzum Bank:</b> <code>{PAYMENT_CARDS['uzum']}</code>
📝 <b>Eslatma:</b>
1. Yuqoridagi kartaga {amount:,} so'm to'lang
2. To'lov chekini (screenshot) yuboring
3. Admin 1 soat ichida tekshiradi
4. Natijani olasiz
⚠️ <b>Diqqat!</b> Soxta chek yuborilsa, hisob bloklanadi!
📎 <b>Iltimos, to'lov chekini yuboring:</b>"""
    await message.answer(payment_text, reply_markup=get_back_button())
    await state.set_state(OrderStates.waiting_screenshot)


@dp.message(F.text == "💻 Maxsus Xizmatlar")
async def special_services(message: Message):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    services_text = """💼 <b>MAXSUS XIZMATLAR</b>
👨‍💼 <b>Maxsus xizmatlar admini:</b>
🤖 @Islomovo24
🛠️ <b>Xizmat turlari:</b>
• Python Script dasturlash
• Telegram bot yaratish  
• Web saytlar yaratish
• Boshqa maxsus dasturlar
• Instagram/TikTok/YouTube botlari
• SMM xizmatlari
💰 <b>Narxlar:</b> Kelishilgan holda
⏰ <b>Ish vaqti:</b> 24/7
🔄 <b>Kafolat:</b> 100% ishonch"""
    builder = InlineKeyboardBuilder()
    builder.button(text="👨‍💼 Admin bilan bog'lanish", url="https://t.me/Islomovo24")
    await message.answer(services_text, reply_markup=builder.as_markup())


@dp.message(F.text == "📢 Reklama Berish")
async def advertisement(message: Message):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    ad_text = """📢 <b>REKLAMA BERISH</b>
👨‍💼 <b>Reklama admini:</b>
🤖 @nakurtkatop_bot
💬 <b>Reklama turlari:</b>
• Banner reklama
• Post reklama  
• Bot ichida reklama
• Maxsus takliflar
• Kanal/Group reklama
💰 <b>Narxlar:</b> Kelishilgan holda
⏰ <b>Ish vaqti:</b> 24/7
🎯 <b>Auditoriya:</b> Katta auditoriya
⚡ <b>Tez natijalar!</b>"""
    builder = InlineKeyboardBuilder()
    builder.button(text="👨‍💼 Admin bilan bog'lanish", url="https://t.me/Nakurtka_rek")
    await message.answer(ad_text, reply_markup=builder.as_markup())


@dp.message(OrderStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    data = await state.get_data()
    order_id = data.get('order_id')
    amount = data.get('amount')
    platform = data.get('platform')
    service_type = data.get('service_type')
    quantity = data.get('quantity')

    try:
        # Rasmni saqlash
        photo = message.photo[-1]
        file_path = await save_payment_screenshot(photo.file_id, order_id)

        if file_path:
            # Buyurtmani yangilash
            update_order_payment(order_id, file_path)

            await message.answer(
                "✅ <b>Chek qabul qilindi!</b>\n\n" +
                "Admin tekshiruvi uchun yuborildi. 1 soat ichida javob beriladi.\n\n" +
                f"📝 <b>Iltimos, {'Instagram' if platform == 'instagram' else 'Telegram'} username (nik) ni yuboring:</b>"
            )

            # Adminlarga xabar yuborish
            for admin_id in ADMINS:
                try:
                    admin_message = (
                        "🆕 <b>YANGI BUYURTMA!</b>\n\n"
                        f"📝 <b>Buyurtma ID:</b> #{order_id}\n"
                        f"👤 <b>Foydalanuvchi:</b> @{message.from_user.username or 'Noma lum'}\n"
                        f"👤 <b>Ism:</b> {message.from_user.full_name}\n"
                        f"📱 <b>Platforma:</b> {'Instagram' if platform == 'instagram' else 'Telegram'}\n"
                        f"📊 <b>Xizmat:</b> {service_type} - {quantity}\n"
                        f"💰 <b>Summa:</b> {amount:,} so'm\n\n"
                        "<b>Chekni tekshiring:</b>"
                    )
                    await bot.send_message(
                        admin_id,
                        admin_message,
                        reply_markup=get_payment_confirmation_keyboard(order_id)
                    )

                    # Chek rasmni yuborish
                    with open(file_path, 'rb') as photo_file:
                        await bot.send_photo(admin_id, photo_file, caption=f"Buyurtma #{order_id} cheki")

                    print(f"✅ Admin #{admin_id} ga xabar yuborildi")
                except Exception as e:
                    print(f"❌ Adminga xabar yuborishda xatolik: {e}")

            await state.set_state(OrderStates.waiting_username)
        else:
            await message.answer("❌ <b>Rasmni saqlashda xatolik yuz berdi. Iltimos, qayta yuboring.</b>")
    except Exception as e:
        print(f"❌ Rasmni qayta ishlashda xatolik: {e}")
        await message.answer("❌ <b>Xatolik yuz berdi. Iltimos, qayta yuboring.</b>")


@dp.message(OrderStates.waiting_screenshot)
async def wrong_screenshot_format(message: Message):
    await message.answer("❌ <b>Iltimos, faqat to'lov chekini rasm formatida yuboring!</b>")


@dp.message(OrderStates.waiting_username)
async def receive_username(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    username = message.text.strip()
    if not username:
        await message.answer("❌ <b>Iltimos, username ni kiriting!</b>")
        return

    await state.update_data(username=username)
    data = await state.get_data()
    platform = data.get('platform')

    if platform == 'instagram':
        link_text = "Instagram post linkini yuboring:\nMasalan: https://www.instagram.com/p/CxZyAbCdeFg/\n\nAgar followers/views bo'lsa, profil linkini yuboring:\nMasalan: https://www.instagram.com/username/"
    else:
        link_text = "Telegram kanal yoki guruh linkini yuboring:\nMasalan: https://t.me/kanal_nomi"

    await message.answer(f"🔗 <b>Linkni yuboring:</b>\n\n{link_text}")
    await state.set_state(OrderStates.waiting_link)


@dp.message(OrderStates.waiting_link)
async def receive_link(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    link = message.text.strip()
    data = await state.get_data()
    platform = data.get('platform')

    if platform == 'instagram':
        if not link.startswith('https://www.instagram.com/'):
            await message.answer("❌ <b>Noto'g'ri Instagram linki! Qaytadan kiriting:</b>")
            return
    else:
        if not (link.startswith('https://t.me/') or link.startswith('@')):
            await message.answer("❌ <b>Noto'g'ri Telegram linki! Qaytadan kiriting:</b>")
            return

    await state.update_data(link=link)
    await message.answer(
        "📞 <b>Telefon raqamingizni yuboring:</b>\n\n" +
        "Masalan: +998901234567 yoki 901234567"
    )
    await state.set_state(OrderStates.waiting_phone)


@dp.message(OrderStates.waiting_phone)
async def receive_phone(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        is_subscribed = await check_user_subscription(user_id)
        if not is_subscribed:
            await ask_for_subscription(message)
            return

    phone = message.text.strip()
    cleaned_phone = phone.replace(" ", "").replace("+", "")
    if not cleaned_phone.isdigit() or len(cleaned_phone) < 9:
        await message.answer("❌ <b>Noto'g'ri telefon raqami format! Qaytadan kiriting:</b>\n\nMasalan: +998901234567")
        return

    data = await state.get_data()
    order_id = data.get('order_id')
    username = data.get('username')
    link = data.get('link')
    platform = data.get('platform')
    service_type = data.get('service_type')
    quantity = data.get('quantity')
    amount = data.get('amount')

    update_order_info(order_id, username, link, phone)
    platform_name = 'Instagram' if platform == 'instagram' else 'Telegram'

    success_text = f"""✅ <b>BUYURTMA MUVOFFAQIYATLI QABUL QILINDI!</b>
📊 <b>Buyurtma ID:</b> #{order_id}
📱 <b>Platforma:</b> {platform_name}
👤 <b>Username:</b> @{username}
🔗 <b>Link:</b> {link}
📞 <b>Telefon:</b> {phone}
📊 <b>Xizmat:</b> {service_type} - {quantity}
💰 <b>Summa:</b> {amount:,} so'm
⏳ <b>Admin tekshiruvi:</b> 1 soat ichida
📬 <b>Natija Telegram orqali yuboriladi.</b>
🎯 Nakrutka boshlangandan so'ng sizga xabar beramiz!
<b>Rahmat! 🤝</b>"""
    await message.answer(success_text, reply_markup=get_main_menu())

    # Adminlarga qo'shimcha ma'lumot
    for admin_id in ADMINS:
        try:
            await bot.send_message(
                admin_id,
                f"📋 <b>Buyurtma #{order_id} ma'lumotlari to'ldirildi:</b>\n\n" +
                f"📱 Platforma: {platform_name}\n" +
                f"👤 Username: @{username}\n" +
                f"🔗 Link: {link}\n" +
                f"📞 Telefon: {phone}\n" +
                f"📊 Xizmat: {service_type} - {quantity}\n" +
                f"💰 Summa: {amount:,} so'm"
            )
        except:
            pass

    await state.clear()


@dp.message(Command("admin"))
async def admin_panel_command(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("❌ <b>Siz admin emassiz!</b>", reply_markup=get_main_menu())
        return

    await message.answer(
        "👑 <b>ADMIN PANELI</b>\n\n" +
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=get_admin_menu()
    )


@dp.message(F.text == "📊 Statistika")
async def admin_statistics(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("❌ <b>Siz admin emassiz!</b>")
        return

    stats = get_statistics()
    stats_text = f"""📊 <b>BOT STATISTIKALARI</b>
👥 <b>Umumiy foydalanuvchilar:</b> {stats['total_users']}
✅ <b>Obuna bo'lganlar:</b> {stats['subscribed_users']}
📋 <b>Jami buyurtmalar:</b> {stats['total_orders']}
💰 <b>Jami daromad:</b> {stats['total_income']:,} so'm
⏳ <b>Kutayotgan buyurtmalar:</b> {stats['pending_orders']}
📅 <b>Bugungi statistika:</b>
📋 <b>Buyurtmalar:</b> {stats['today_orders']}
💰 <b>Daromad:</b> {stats['today_income']:,} so'm
⏰ <b>Sana:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    await message.answer(stats_text, reply_markup=get_admin_menu())


@dp.message(F.text == "📋 Buyurtmalar")
async def admin_orders(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("❌ <b>Siz admin emassiz!</b>")
        return

    orders = get_pending_orders()
    if not orders:
        await message.answer("✅ <b>Hozircha kutayotgan buyurtmalar yo'q.</b>", reply_markup=get_admin_menu())
        return

    text = "📋 <b>KUTAYOTGAN BUYURTMALAR:</b>\n\n"
    for order in orders[:10]:
        order_id = order[0]
        platform = order[2]
        service_type = order[3]
        quantity = order[4]
        amount = order[5]
        username = order[12] or "Noma'lum"
        full_name = order[13] or "Noma'lum"
        platform_name = 'Instagram' if platform == 'instagram' else 'Telegram'
        text += f"""🆔 <b>#{order_id}</b>
👤 {full_name} (@{username})
📱 {platform_name} - {service_type}
🔢 {quantity}
💰 {amount:,} so'm
════════════════════════════════════\n"""

    if len(orders) > 10:
        text += f"\n📄 ...va yana {len(orders) - 10} ta buyurtma"

    await message.answer(text, reply_markup=get_admin_menu())


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_payment(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if admin_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    order_id = int(callback.data.split("_")[1])
    update_order_status(order_id, 'confirmed')
    await callback.message.edit_text(
        f"✅ <b>Buyurtma #{order_id} tasdiqlandi!</b>\n\n" +
        f"Foydalanuvchiga xabar yuborildi.",
        reply_markup=None
    )

    order = get_order_by_id(order_id)
    if order:
        user_id = order[1]
        try:
            await bot.send_message(
                user_id,
                f"🎉 <b>YAXSHI XABAR!</b>\n\n" +
                f"✅ <b>Buyurtmangiz tasdiqlandi!</b>\n\n" +
                f"🆔 <b>Buyurtma ID:</b> #{order_id}\n" +
                f"⏳ <b>Nakrutka boshlanishi:</b> 1 soat ichida\n" +
                f"📊 <b>Progress haqida keyinroq xabar beramiz.</b>\n\n" +
                f"<b>Rahmat! 🎊</b>"
            )
            print(f"✅ Foydalanuvchi #{user_id} ga tasdiq xabari yuborildi")
        except Exception as e:
            print(f"❌ Foydalanuvchiga xabar yuborishda xatolik: {e}")

    await callback.answer(f"✅ #{order_id} tasdiqlandi!")


@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_payment(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if admin_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    order_id = int(callback.data.split("_")[1])
    update_order_status(order_id, 'cancelled')
    await callback.message.edit_text(
        f"❌ <b>Buyurtma #{order_id} bekor qilindi!</b>\n\n" +
        f"Foydalanuvchiga xabar yuborildi.",
        reply_markup=None
    )

    order = get_order_by_id(order_id)
    if order:
        user_id = order[1]
        try:
            await bot.send_message(
                user_id,
                f"❌ <b>AFSUSKI...</b>\n\n" +
                f"🆔 <b>Buyurtma ID:</b> #{order_id}\n" +
                f"💰 <b>Sabab:</b> To'lov tekshiruvidan o'tmadi\n\n" +
                f"ℹ️ <b>Agar xato bo'lsa, admin bilan bog'laning:</b>\n" +
                f"🤖 @nakurtkatop_bot"
            )
            print(f"❌ Foydalanuvchi #{user_id} ga bekor qilish xabari yuborildi")
        except Exception as e:
            print(f"❌ Foydalanuvchiga xabar yuborishda xatolik: {e}")

    await callback.answer(f"❌ #{order_id} bekor qilindi!")


@dp.message(F.text == "🏠 Foydalanuvchi menyusi")
async def admin_to_main(message: Message):
    await message.answer("🏠 <b>Asosiy menyuga qaytingiz</b>", reply_markup=get_main_menu())


@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 <b>Asosiy menyuga qaytingiz</b>", reply_markup=get_main_menu())


# ==================== WEBHOOK HANDLERS ====================
async def handle_webhook(request):
    """Telegram webhook ni qayta ishlash"""
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"Webhook xatosi: {e}")
        return web.Response(text="Error", status=500)


async def on_startup(app):
    """Bot ishga tushganda"""
    print("=" * 50)
    print("🤖 NAKRUTKA BOTI ISHGA TUSHDI...")
    print("=" * 50)

    # Database yaratish
    init_database()

    # Adminlarga xabar
    for admin_id in ADMINS:
        try:
            await bot.send_message(
                admin_id,
                f"✅ <b>Bot ishga tushdi!</b>\n\n" +
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" +
                f"📢 Majburiy kanal: {REQUIRED_CHANNELS[0]}\n" +
                f"💳 Karta: {PAYMENT_CARDS['uzum']}\n\n" +
                "Admin panel: /admin"
            )
            print(f"✅ Admin #{admin_id} ga xabar yuborildi")
        except Exception as e:
            print(f"❌ Admin #{admin_id} ga xabar yuborishda xatolik: {e}")


async def create_app():
    """Render uchun asosiy ilova"""
    app = web.Application()

    # Webhook endpoint
    app.router.add_post(f'/webhook/{BOT_TOKEN}', handle_webhook)

    # Asosiy sahifa (UptimeRobot uchun)
    async def home(request):
        return web.Response(text="🤖 Nakrutka Bot ishlamoqda!")

    app.router.add_get('/', home)

    # Startup ishlari
    app.on_startup.append(on_startup)

    return app


# ==================== MAIN ====================
if __name__ == "__main__":
    # Logging sozlash
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Render.com da webhook ishlatish
    if 'RENDER' in os.environ:
        print("🌐 Render.com muhitida ishlayapti...")
        # Webhook ni o'rnatish
        import nest_asyncio

        nest_asyncio.apply()

        # Serverni ishga tushirish
        app = create_app()
        web.run_app(app, host='0.0.0.0', port=8080)
    else:
        # Local da polling ishlatish
        print("💻 Local muhitda ishlayapti...")


        async def main():
            await dp.start_polling(bot)


        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n\n🛑 Bot to'xtatildi!")