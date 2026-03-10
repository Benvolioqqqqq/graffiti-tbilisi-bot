import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import init_db, add_graffiti, get_all_graffiti, get_pending_graffiti, update_status, search_graffiti, delete_graffiti
from map_generator import generate_map
from aiogram.types import FSInputFile
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from web_server import create_app
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))



bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺 Карта"), KeyboardButton(text="➕ Добавить граффити")],
        [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="⚙️ Управление")]
    ],
    resize_keyboard=True
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)


# Определяем шаги диалога
class AddGraffiti(StatesGroup):
    photo = State()
    location = State()
    author = State()
    date = State()
    description = State()

class SearchGraffiti(StatesGroup):
    query = State()


# Команда /start
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привет! Я бот «Граффити Тбилиси» 🎨\n\n"
        "Нажмите кнопку ниже, чтобы начать:",
        reply_markup=main_keyboard
    )

@dp.message(F.text.in_({"/map", "🗺 Карта"}))
async def show_map(message: types.Message):
    graffiti_list = get_all_graffiti()
    if not graffiti_list:
        await message.answer("На карте пока нет граффити. Добавьте первое через /add", reply_markup=main_keyboard)
        return

    await generate_map(bot)

    web_app_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🗺 Открыть карту",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )]
        ]
    )
    await message.answer("Нажмите кнопку, чтобы открыть карту:", reply_markup=web_app_button)


@dp.message(F.text == "❌ Отмена")
async def cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_keyboard)


@dp.message(F.text.in_({"/search", "🔍 Поиск"}))
async def search_start(message: types.Message, state: FSMContext):
    await message.answer("Введите имя автора или ключевое слово:", reply_markup=cancel_keyboard)
    await state.set_state(SearchGraffiti.query)


@dp.message(SearchGraffiti.query)
async def search_results(message: types.Message, state: FSMContext):
    query = message.text.strip()
    results = search_graffiti(query)

    if not results:
        await message.answer(
            f"По запросу «{query}» ничего не найдено.",
            reply_markup=main_keyboard
        )
        await state.clear()
        return

    await message.answer(f"Найдено граффити: {len(results)}")

    for item in results:
        g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item

        text = (
            f"🎨 Автор: {author}\n"
            f"📅 Дата: {date}\n"
            f"📝 Описание: {description or 'Нет описания'}\n"
            f"📍 Координаты: {lat}, {lon}"
        )

        if photo_id:
            await message.answer_photo(photo=photo_id, caption=text)
        else:
            await message.answer(text)

    await message.answer("Поиск завершён.", reply_markup=main_keyboard)
    await state.clear()


# Команда /add — начало добавления
@dp.message(F.text.in_({"/add", "➕ Добавить граффити"}))
async def add_start(message: types.Message, state: FSMContext):
    await message.answer("📸 Отправьте фото граффити:", reply_markup=cancel_keyboard)
    await state.set_state(AddGraffiti.photo)


# Шаг 1: Получаем фото
@dp.message(AddGraffiti.photo, F.photo)
async def get_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer(
        "📍 Теперь отправьте геолокацию граффити.\n\n"
        "Нажмите скрепку 📎 → Геолокация → выберите точку на карте."
    )
    await state.set_state(AddGraffiti.location)


# Если отправили не фото
@dp.message(AddGraffiti.photo)
async def get_photo_wrong(message: types.Message):
    await message.answer("Пожалуйста, отправьте именно фото.")


# Шаг 2: Получаем геолокацию
@dp.message(AddGraffiti.location, F.location)
async def get_location(message: types.Message, state: FSMContext):
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    await message.answer("✍️ Введите никнейм автора граффити (или напишите «нет», если неизвестен):")
    await state.set_state(AddGraffiti.author)


# Если отправили не геолокацию
@dp.message(AddGraffiti.location)
async def get_location_wrong(message: types.Message):
    await message.answer("Пожалуйста, отправьте именно геолокацию (📎 → Геолокация).")


# Шаг 3: Получаем автора
@dp.message(AddGraffiti.author)
async def get_author(message: types.Message, state: FSMContext):
    author = message.text.strip()
    if author.lower() == "нет":
        author = "Неизвестен"
    await state.update_data(author=author)
    await message.answer("📅 Введите дату нанесения (например: 2024 или март 2024), или «нет»:")
    await state.set_state(AddGraffiti.date)


# Шаг 4: Получаем дату
@dp.message(AddGraffiti.date)
async def get_date(message: types.Message, state: FSMContext):
    date = message.text.strip()
    if date.lower() == "нет":
        date = "Неизвестна"
    await state.update_data(date=date)
    await message.answer("📝 Добавьте описание граффити (или «нет»):")
    await state.set_state(AddGraffiti.description)


# Шаг 5: Получаем описание и сохраняем
@dp.message(AddGraffiti.description)
async def get_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    if description.lower() == "нет":
        description = ""

    data = await state.get_data()

    graffiti_id = add_graffiti(
        latitude=data["latitude"],
        longitude=data["longitude"],
        photo_id=data["photo_id"],
        author=data["author"],
        date=data["date"],
        description=description,
        added_by=str(message.from_user.id)
    )

    await message.answer(
        "✅ Граффити отправлено на модерацию! После проверки оно появится на карте.",
        reply_markup=main_keyboard
    )

    # Уведомляем админа
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{graffiti_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{graffiti_id}")
            ]
        ]
    )
    await bot.send_photo(
        ADMIN_ID,
        photo=data["photo_id"],
        caption=f"Новое граффити на модерацию:\n\n"
                f"🎨 Автор: {data['author']}\n"
                f"📅 Дата: {data['date']}\n"
                f"📝 Описание: {description}\n"
                f"📍 Координаты: {data['latitude']}, {data['longitude']}\n"
                f"👤 Добавил: {message.from_user.full_name}",
        reply_markup=admin_keyboard
    )

    await state.clear()


@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    graffiti_id = int(callback.data.split("_")[1])
    update_status(graffiti_id, "approved")
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ ОДОБРЕНО",
        reply_markup=None
    )
    await callback.answer("Одобрено!")

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    graffiti_id = int(callback.data.split("_")[1])
    update_status(graffiti_id, "rejected")
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ ОТКЛОНЕНО",
        reply_markup=None
    )
    await callback.answer("Отклонено!")


@dp.message(F.text == "⚙️ Управление")
async def manage_graffiti(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Эта функция доступна только администратору.")
        return

    graffiti_list = get_all_graffiti()
    if not graffiti_list:
        await message.answer("На карте пока нет граффити.", reply_markup=main_keyboard)
        return

    await message.answer(f"На карте {len(graffiti_list)} граффити:")

    for item in graffiti_list:
        g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item

        text = (
            f"ID: {g_id}\n"
            f"🎨 Автор: {author}\n"
            f"📅 Дата: {date}\n"
            f"📝 Описание: {description or 'Нет описания'}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{g_id}")]
            ]
        )

        if photo_id:
            await message.answer_photo(photo=photo_id, caption=text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("delete_"))
async def delete_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    graffiti_id = int(callback.data.split("_")[1])

    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{graffiti_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
            ]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=confirm_keyboard)
    await callback.answer("Подтвердите удаление")


@dp.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    graffiti_id = int(callback.data.split("_")[2])
    delete_graffiti(graffiti_id)

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n🗑 УДАЛЕНО",
        reply_markup=None
    )
    await callback.answer("Граффити удалено!")


@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Отменено")



async def main():
    init_db()

    # Запускаем веб-сервер
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    import os
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print("Веб-сервер запущен на порту 8080")

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())