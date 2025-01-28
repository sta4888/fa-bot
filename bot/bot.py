import logging
import os
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram_calendar import SimpleCalendar, DialogCalendar
from dotenv import load_dotenv
import asyncio

# Загрузка переменных окружения из .env файла
load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Список популярных городов
CITIES = [
    "Москва", "Санкт-Петербург", "Казань", "Сочи", "Екатеринбург",
    "Новосибирск", "Краснодар", "Калининград", "Владивосток"
]

# Состояния FSM
class FlightForm(StatesGroup):
    waiting_for_departure = State()
    waiting_for_destination = State()
    waiting_for_departure_date = State()
    waiting_for_return_date = State()
    waiting_for_passengers = State()

# Функция создания клавиатуры с городами
def get_cities_keyboard():
    buttons = [[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in CITIES]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🔍 Поиск авиабилетов", callback_data="search_tickets")
        ]]
    )
    
    await message.reply(
        "Привет! Я помогу вам найти авиабилеты! 🛫\n"
        "Нажмите кнопку ниже, чтобы начать поиск.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "search_tickets")
async def process_search_tickets(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "Откуда вы хотите вылететь? Выберите город отправления:",
        reply_markup=get_cities_keyboard()
    )
    await state.set_state(FlightForm.waiting_for_departure)

@dp.callback_query(F.data.startswith("city_"), FlightForm.waiting_for_departure)
async def process_departure_city(callback_query: types.CallbackQuery, state: FSMContext):
    departure_city = callback_query.data.replace('city_', '')
    await state.update_data(departure_city=departure_city)
    
    await callback_query.message.edit_text(
        f"Отлично! Вылет из города: {departure_city}\n\nТеперь выберите город прибытия:",
        reply_markup=get_cities_keyboard()
    )
    await state.set_state(FlightForm.waiting_for_destination)

@dp.callback_query(F.data.startswith("city_"), FlightForm.waiting_for_destination)
async def process_destination_city(callback_query: types.CallbackQuery, state: FSMContext):
    destination_city = callback_query.data.replace('city_', '')
    await state.update_data(destination_city=destination_city)
    
    calendar = DialogCalendar(locale='ru')  # добавляем локализацию
    await callback_query.message.edit_text(
        f"Выберите дату вылета:",
        reply_markup=await calendar.start_calendar()
    )
    await state.set_state(FlightForm.waiting_for_departure_date)

# Общий обработчик для всех callback_query
@dp.callback_query()
async def process_all_callbacks(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    logging.info(f"Received callback with data: {callback_query.data}, state: {current_state}")
    
    if current_state == FlightForm.waiting_for_departure_date.state:
        calendar = DialogCalendar(locale='ru')
        selected, date = await calendar.process_selection(callback_query)
        if selected:
            await state.update_data(departure_date=date)
            calendar = DialogCalendar(locale='ru')
            await callback_query.message.edit_text(
                'Выберите дату возвращения:',
                reply_markup=await calendar.start_calendar()
            )
            await state.set_state(FlightForm.waiting_for_return_date)
    
    elif current_state == FlightForm.waiting_for_return_date.state:
        calendar = DialogCalendar(locale='ru')
        selected, date = await calendar.process_selection(callback_query)
        if selected:
            await state.update_data(return_date=date)
            
            # Создаем клавиатуру для выбора количества пассажиров
            buttons = [[InlineKeyboardButton(text=str(i), callback_data=f"passengers_{i}") for i in range(1, 5)],
                      [InlineKeyboardButton(text=str(i), callback_data=f"passengers_{i}") for i in range(5, 9)]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback_query.message.edit_text(
                "Выберите количество пассажиров:",
                reply_markup=keyboard
            )
            await state.set_state(FlightForm.waiting_for_passengers)
    
    elif current_state == FlightForm.waiting_for_passengers.state and callback_query.data.startswith("passengers_"):
        passengers = int(callback_query.data.replace('passengers_', ''))
        user_data = await state.get_data()
        
        # Формируем итоговое сообщение
        summary = (
            f"✈️ Ваш запрос на поиск билетов:\n\n"
            f"🛫 Откуда: {user_data['departure_city']}\n"
            f"🛬 Куда: {user_data['destination_city']}\n"
            f"📅 Дата вылета: {user_data['departure_date'].strftime('%d.%m.%Y')}\n"
            f"📅 Дата возвращения: {user_data['return_date'].strftime('%d.%m.%Y')}\n"
            f"👥 Количество пассажиров: {passengers}\n\n"
            f"🔄 Идет поиск билетов..."
        )
        
        await callback_query.message.edit_text(summary)
        await state.clear()
    
    # Не забываем ответить на callback_query
    await callback_query.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())