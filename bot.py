import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from model import Model

api_token = ''
logging.basicConfig(level=logging.INFO)


class TelegBot:
    def __init__(self, token):
        pdf_path = 'content/język_polski3.pdf'
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.dp.message.register(self.handle_m)

        self.model = Model(pdf_path)


    async def start(self):
        logging.info("Uruchomiony")

        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)

    async def handle_m(self, message: types.Message):
        question = message.text
        logging.info(f"Otrzymano: {question}.")
        answer = self.model.ask(question)
        await message.answer(answer)

bot = TelegBot(api_token)
asyncio.run(bot.start())
