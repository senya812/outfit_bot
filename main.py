import asyncio, os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db

load_dotenv()
tok = os.getenv("BOT_TOKEN")
adm = int(os.getenv("ADMIN_ID"))
bot = Bot(token=tok)
dp = Dispatcher()

class AdminStates(StatesGroup):
    cat = State()
    p_cat = State()
    p_name = State()
    p_desc = State()
    p_price = State()
    p_photo = State()
    # Стейты для мгновенной рассылки
    bc_text = State()
    bc_photo = State()

def get_main_menu_kb():
    cats = db.get_categories()
    btn = []
    for c_id, c_name in cats:
        b = InlineKeyboardButton(text=f"👕 {c_name}", callback_data=f"cat_{c_id}")
        btn.append([b])
    btn.append([InlineKeyboardButton(text="🛒 Мой Outfit (Корзина)", callback_data="view_cart")])
    return InlineKeyboardMarkup(inline_keyboard=btn)

def get_admin_menu_kb():
    b1 = InlineKeyboardButton(text="➕ Категория", callback_data="add_c")
    b2 = InlineKeyboardButton(text="🗑 Категория", callback_data="del_c")
    b3 = InlineKeyboardButton(text="➕ Товар", callback_data="add_p")
    b4 = InlineKeyboardButton(text="🗑 Товар", callback_data="del_p")
    b5 = InlineKeyboardButton(text="📊 Статистика CRM", callback_data="crm_stats")
    b6 = InlineKeyboardButton(text="📢 Рассылка", callback_data="mode_instant")
    b7 = InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_a")
    return InlineKeyboardMarkup(inline_keyboard=[[b1, b2], [b3, b4], [b5, b6], [b7]])

def get_post_kb():
    b1 = InlineKeyboardButton(text="➕ Еще товар", callback_data="add_p")
    b2 = InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_a")
    return InlineKeyboardMarkup(inline_keyboard=[[b1, b2]])

@dp.message(Command("start"))
async def cmd_start(m: Message):
    db.register_user(m.from_user.id, m.from_user.username, m.from_user.first_name)
    t = """✨ *Добро пожаловать в Outfit!*

Твой персональный бутик стиля. Выбери категорию:"""
    await m.answer(t, parse_mode="Markdown", reply_markup=get_main_menu_kb())

@dp.callback_query(F.data == "empty")
async def empty_cb(c: CallbackQuery):
    await c.answer("Магазин пуст!", show_alert=True)

@dp.callback_query(F.data.startswith("cat_"))
async def show_cat(c: CallbackQuery):
    c_id = int(c.data.split("_")[1])
    prods = db.get_products_by_category(c_id)
    c_name = db.get_category_name(c_id)
    await c.message.delete()
    if not prods:
        b = InlineKeyboardButton(text="↩️ Назад", callback_data="back_c")
        kb = InlineKeyboardMarkup(inline_keyboard=[[b]])
        await c.message.answer(f"📦 В категории *{c_name}* пока ничего нет.", parse_mode="Markdown", reply_markup=kb)
        return
    for p_id, p_name in prods:
        _, n, d, pr, ph = db.get_product_details(p_id)
        cap = f"""🔥 *{n}*

📝 {d}

💰 *Цена:* {pr} руб."""
        b1 = InlineKeyboardButton(text="🛍 Добавить в Outfit", callback_data=f"buy_{p_id}")
        b2 = InlineKeyboardButton(text="↩️ Назад", callback_data="back_c")
        kb = InlineKeyboardMarkup(inline_keyboard=[[b1], [b2]])
        await c.message.answer_photo(photo=ph, caption=cap, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.startswith("buy_"))
async def add_cart_cb(c: CallbackQuery):
    p_id = int(c.data.split("_")[1])
    db.add_to_cart(c.from_user.id, p_id)
    await c.answer("✅ Добавлено в ваш Outfit!", show_alert=True)

@dp.callback_query(F.data == "view_cart")
async def view_cart_cb(c: CallbackQuery):
    items = db.get_cart_items(c.from_user.id)
    try: await c.message.delete()
    except: pass
    if not items:
        b = InlineKeyboardButton(text="↩️ В магазин", callback_data="back_c")
        kb = InlineKeyboardMarkup(inline_keyboard=[[b]])
        await c.message.answer("🛒 Твой список Outfit пока пуст.", reply_markup=kb)
        return
    text = """📋 *Твой выбор Outfit:*

"""
    btn = []
    total = 0
    for idx, (cart_id, name, price, _) in enumerate(items, 1):
        text += f"{idx}. {name} — {price} руб.\n"
        total += price
        b = InlineKeyboardButton(text=f"❌ Удалить [{idx}]", callback_data=f"rem_{cart_id}")
        btn.append([b])
    text += f"""
💳 *Итого к оплате:* {total} руб."""
    b_back = InlineKeyboardButton(text="↩️ Назад", callback_data="back_c")
    b_clear = InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_c")
    btn.append([b_clear, b_back])
    await c.message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=btn))

@dp.callback_query(F.data.startswith("rem_"))
async def remove_cart_item_cb(c: CallbackQuery):
    cart_id = int(c.data.split("_"))
    db.delete_from_cart(cart_id)
    await c.answer("Удалено!")
    await view_cart_cb(c)

@dp.callback_query(F.data == "clear_c")
async def clear_cart_cb(c: CallbackQuery):
    db.clear_cart(c.from_user.id)
    await c.answer("Корзина очищена!")
    await view_cart_cb(c)

@dp.callback_query(F.data == "back_c")
async def back_c(c: CallbackQuery):
    try: await c.message.delete()
    except: pass
    await c.message.answer("✨ Выберите категорию товара:", reply_markup=get_main_menu_kb())

# --- АДМИНКА И CRM-МОДУЛИ ---

@dp.message(Command("admin"))
async def cmd_admin(m: Message):
    if m.from_user.id == adm:
        await m.answer("🛠 Панель Outfit Admin:", reply_markup=get_admin_menu_kb())

@dp.callback_query(F.data == "menu_a")
async def menu_a(c: CallbackQuery):
    if c.from_user.id == adm:
        await c.message.edit_text("🛠 Панель Outfit Admin:", reply_markup=get_admin_menu_kb())

@dp.callback_query(F.data == "crm_stats")
async def show_crm_stats(c: CallbackQuery):
    if c.from_user.id != adm: return
    t_users, t_prods, a_carts = db.get_crm_stats()
    
    # Исправлено: убрали, так как теперь переменные — это обычные числа, а не кортежи
    text = f"""📊 *Статистика магазина Outfit:*

👥 Всего клиентов в базе: *{t_users}* чел.
📦 Активных товаров на витрине: *{t_prods}* шт.
🛒 Клиентов с товарами в корзине: *{a_carts}* чел."""
    
    b = InlineKeyboardButton(text="↩️ Меню", callback_data="menu_a")
    await c.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[b]]))


@dp.callback_query(F.data == "exit_a")
async def exit_a(c: CallbackQuery):
    if c.from_user.id != adm: return
    await c.message.delete()
    await c.message.answer("🚪 Вы вышли из админки.")
    await c.message.answer("✨ Выберите категорию товара:", reply_markup=get_main_menu_kb())

# --- МГНОВЕННАЯ РАССЫЛКА ПО ВСЕЙ БАЗЕ ---

@dp.callback_query(F.data == "mode_instant")
async def mode_instant(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != adm: return
    await c.message.answer("✍️ Введите текст рекламного сообщения:")
    await state.set_state(AdminStates.bc_text)

@dp.message(AdminStates.bc_text)
async def proc_bc_text(m: Message, state: FSMContext):
    await state.update_data(text=m.text)
    b1 = InlineKeyboardButton(text="🖼 С картинкой", callback_data="inst_img")
    b2 = InlineKeyboardButton(text="⏩ Без фото", callback_data="inst_skip")
    await m.answer("Добавить изображение к рассылке?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[b1, b2]]))

@dp.callback_query(F.data == "inst_skip", AdminStates.bc_text)
async def inst_skip(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await run_broadcast(c.message, data['text'], None)

@dp.callback_query(F.data == "inst_img", AdminStates.bc_text)
async def inst_img(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text("🖼 Отправьте изображение для рассылки:")
    await state.set_state(AdminStates.bc_photo)

@dp.message(AdminStates.bc_photo, F.photo)
async def proc_bc_photo(m: Message, state: FSMContext):
    ph = m.photo[-1].file_id
    data = await state.get_data()
    await state.clear()
    await run_broadcast(m, data['text'], ph)

async def run_broadcast(m: Message, text: str, photo_id: str = None):
    users = db.get_all_users()
    if not users:
        await m.answer("❌ База пуста, рассылать некому.")
        return
    await m.answer(f"🚀 Запущена массовая рассылка на {len(users)} пользователей...")
    success, failed = 0, 0
    for u in users:
        u_id = u[0] if isinstance(u, tuple) else u
        try:
            if photo_id: 
                await bot.send_photo(chat_id=u_id, photo=photo_id, caption=text, parse_mode="Markdown")
            else: 
                await bot.send_message(chat_id=u_id, text=text, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)
        except Exception: 
            failed += 1
    await m.answer(f"""📊 *Итог рассылки:*
✅ Доставлено: {success}
❌ Блок бота: {failed}""", parse_mode="Markdown", reply_markup=get_admin_menu_kb())

# --- УПРАВЛЕНИЕ КАТЕГОРИЯМИ И ТОВАРАМИ ---

@dp.callback_query(F.data == "add_c")
async def add_c(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != adm: return
    await c.message.answer("✏️ Напишите название категории:")
    await state.set_state(AdminStates.cat)

@dp.message(AdminStates.cat)
async def proc_c(m: Message, state: FSMContext):
    db.add_category(m.text)
    await m.answer("✅ Категория добавлена!", reply_markup=get_admin_menu_kb())
    await state.clear()

@dp.callback_query(F.data == "del_c")
async def del_c(c: CallbackQuery):
    if c.from_user.id != adm: return
    cats = db.get_categories()
    if not cats: return await c.answer("Категорий нет!", show_alert=True)
    btn = [[InlineKeyboardButton(text=f"❌ {c_name}", callback_data=f"dc_{c_id}")] for c_id, c_name in cats]
    btn.append([InlineKeyboardButton(text="↩️... Меню", callback_data="menu_a")])
    await c.message.edit_text("🗑 Удалить категорию и все товары в ней?", reply_markup=InlineKeyboardMarkup(inline_keyboard=btn))

@dp.callback_query(F.data.startswith("dc_"))
async def proc_del_c(c: CallbackQuery):
    c_id = int(c.data.split("_")[1])
    db.delete_category(c_id)
    await c.message.edit_text("✅ Категория удалена!", reply_markup=get_admin_menu_kb())

@dp.callback_query(F.data == "add_p")
async def add_p(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != adm: return
    cats = db.get_categories()
    if not cats: return await c.answer("Сначала создайте категорию!", show_alert=True)
    btn = [[InlineKeyboardButton(text=c_name, callback_data=f"sc_{c_id}")] for c_id, c_name in cats]
    await c.message.answer("📁 Выберите категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btn))
    await state.set_state(AdminStates.p_cat)

@dp.callback_query(AdminStates.p_cat, F.data.startswith("sc_"))
async def proc_p_cat(c: CallbackQuery, state: FSMContext):
    c_id = int(c.data.split("_")[1])
    await state.update_data(c_id=c_id)
    await c.message.answer("✏️ Введите название товара:")
    await state.set_state(AdminStates.p_name)

@dp.message(AdminStates.p_name)
async def proc_p_name(m: Message, state: FSMContext):
    await state.update_data(n=m.text)
    await m.answer("✏️ Введите описание товара:")
    await state.set_state(AdminStates.p_desc)

@dp.message(AdminStates.p_desc)
async def proc_p_desc(m: Message, state: FSMContext):
    await state.update_data(d=m.text)
    await m.answer("✏️ Введите цену (только числа):")
    await state.set_state(AdminStates.p_price)

@dp.message(AdminStates.p_price)
async def proc_p_price(m: Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("⚠️ Введите число цифрами:")
        return
    await state.update_data(pr=int(m.text))
    await m.answer("🖼 Отправьте фото товара:")
    await state.set_state(AdminStates.p_photo)

@dp.message(AdminStates.p_photo, F.photo)
async def proc_p_photo(m: Message, state: FSMContext):
    ph = m.photo[-1].file_id
    data = await state.get_data()
    db.add_product(data['c_id'], data['n'], data['d'], data['pr'], ph)
    await m.answer("🎉 Товар успешно добавлен!", reply_markup=get_post_kb())
    await state.clear()

@dp.callback_query(F.data == "del_p")
async def del_p(c: CallbackQuery):
    if c.from_user.id != adm: return
    cats = db.get_categories()
    if not cats: return await c.answer("Категорий нет!", show_alert=True)
    btn = [[InlineKeyboardButton(text=c_name, callback_data=f"dpc_{c_id}")] for c_id, c_name in cats]
    btn.append([InlineKeyboardButton(text="↩️ Меню", callback_data="menu_a")])
    await c.message.edit_text("📁 Выберите категорию товара:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btn))

@dp.callback_query(F.data.startswith("dpc_"))
async def del_p_list(c: CallbackQuery):
    c_id = int(c.data.split("_")[1])
    prods = db.get_products_by_category(c_id)
    btn = [[InlineKeyboardButton(text=f"🗑 {p_name}", callback_data=f"dp_{p_id}")] for p_id, p_name in prods]
    btn.append([InlineKeyboardButton(text="↩️ Назад", callback_data="del_p")])
    await c.message.edit_text("📦 Выберите товар для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btn))

@dp.callback_query(F.data.startswith("dp_"))
async def proc_del_p(c: CallbackQuery):
    p_id = int(c.data.split("_")[1])
    db.delete_product(p_id)
    await c.message.edit_text("✅ Товар удален!", reply_markup=get_admin_menu_kb())

async def main():
    db.init_db()
    print("Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
