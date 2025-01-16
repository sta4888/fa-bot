from aiogram import types
from .bot import dp

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    await message.reply("Это справка по командам.")