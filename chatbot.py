import logging
import time
from aiogram import Bot, Dispatcher, types
from aiogram import Router
api_token='7428827735:AAGbsVtSefZP5tvOd4-l5qo7UoXsTR2cPGg'
logging.basicConfig(level=logging.INFO)

class teleg_bot:
    def __init__(self, token):
        self.bot=Bot(token=token)
        self.dp=Dispatcher(self.bot)
    def start(self):
        logging.info("Bot uruchomiony")
        self.bot.delete_webhook(drop_pending_updates=True)
        self.dp.start_polling()
    def handle_m(self, message: types.Message):
        uzyt_message = message.text
        logging.info(f"Otrzymano: {uzyt_message}.")
        self.N(uzyt_message)
        message.answer(f"Otrzymano: {uzyt_message}")
    def N(self, uzyt_message: str):
        logging.info(f"Wiadomosc: {uzyt_message}")
if __name__ == "__main__":
    bot = teleg_bot(api_token)
    bot.start()

    

