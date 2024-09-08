import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import Router
import asyncio

api_token='7428827735:AAGbsVtSefZP5tvOd4-l5qo7UoXsTR2cPGg'
logging.basicConfig(level=logging.INFO)

class teleg_bot:
    def __init__(self, token):
        self.bot=Bot(token=token)
        self.dp=Dispatcher()
        self.router = Router()
        self.router.message.register(self.handle_m)
        self.dp.include_router(self.router)
    async def start(self):
        logging.info("Bot uruchomiony")
        await self.bot.delete_webhook(drop_pending_updates=True)
    async def handle_m(self, message: types.Message):
        uzyt_message=message.text
        logging.info(f"Otrzymano: {uzyt_message}.")
        await message.answer(f"Otrzymano wiadomość: {uzyt_message}")

    async def run(self):
        await self.start()
        await self.dp.start_polling(self.bot)
    async def N(self, uzyt_message: str):
        logging.info(f"Wiadomosc: {uzyt_message}")
if __name__ == "__main__":
    bot = teleg_bot(api_token)
    asyncio.run(bot.run())


    

