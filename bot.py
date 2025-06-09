# bot.py
import os
import asyncio
from aiogram import Bot, Dispatcher, types
import aiohttp
from datetime import datetime, timedelta

TOKEN = os.getenv("TG_TOKEN")
bot = Bot(TOKEN)
dp = Dispatcher(bot)

user_settings = {}

def parse_dates(cmd):
    cmd = cmd.replace("/даты", "").strip()
    if "-" in cmd:
        start_str, end_str = cmd.split("-")
        if "." not in start_str:
            d,e= start_str, cmd.split("-")[1]
            _,m,y = e.split(".")
            start_str = f"{d}.{m}.{y}"
        dates = []
        start = datetime.strptime(start_str, "%d.%m.%Y")
        end = datetime.strptime(end_str, "%d.%m.%Y")
        cur = start
        while cur <= end:
            dates.append(cur.strftime("%d.%m.%Y"))
            cur += timedelta(days=1)
        return dates
    else:
        dt = datetime.strptime(cmd, "%d.%m.%Y")
        return [dt.strftime("%d.%m.%Y")]

@dp.message_handler(commands=["start"])
async def cmd_start(m: types.Message):
    user_settings[m.chat.id] = {"step":"none", "dates":[], "direction":None, "type":None, "running":False}
    await m.answer("Привет! /направление СПБ-СЕВ или СЕВ-СПБ")

@dp.message_handler(lambda m: m.text.startswith("/направление"))
async def cmd_dir(m: types.Message):
    _, val = m.text.split(maxsplit=1)
    if val not in ["СПБ-СЕВ", "СЕВ-СПБ"]:
        return await m.answer("Используй СПБ-СЕВ или СЕВ-СПБ")
    user_settings[m.chat.id]["direction"] = val
    await m.answer(f"Направление: {val}. Теперь /даты dd.mm.yyyy или диапазон.")

@dp.message_handler(lambda m: m.text.startswith("/даты"))
async def cmd_dates(m: types.Message):
    lst = parse_dates(m.text)
    if not lst:
        return await m.answer("Неверный формат дат.")
    user_settings[m.chat.id]["dates"] = lst
    await m.answer(f"Даты: {lst}. Теперь /тип купе или плацкарт.")

@dp.message_handler(lambda m: m.text.startswith("/тип"))
async def cmd_typ(m: types.Message):
    _, val = m.text.split(maxsplit=1)
    if val not in ["купе", "плацкарт"]:
        return await m.answer("Выбирай купе или плацкарт")
    user_settings[m.chat.id]["type"] = val
    await m.answer(f"Тип: {val}. Запуск: /старт_поиск")

@dp.message_handler(commands=["старт_поиск"])
async def cmd_start_search(m: types.Message):
    cfg = user_settings[m.chat.id]
    if not all(cfg.values()):
        return await m.answer("Сначала настрой направление, даты, тип.")
    cfg["running"] = True
    await m.answer("Поиск запущен.")
    asyncio.create_task(check_loop(m.chat.id))

@dp.message_handler(commands=["стоп"])
async def cmd_stop(m: types.Message):
    user_settings[m.chat.id]["running"] = False
    await m.answer("Поиск остановлен.")

@dp.message_handler(commands=["статус"])
async def cmd_status(m: types.Message):
    await m.answer(str(user_settings[m.chat.id]))

async def check_loop(chat_id):
    cfg = user_settings[chat_id]
    while cfg["running"]:
        await check_once(chat_id)
        await asyncio.sleep(300)
    await bot.send_message(chat_id, "Поиск завершён.")

async def check_once(chat_id):
    cfg = user_settings[chat_id]
    base = "https://grandtrain.ru/search/2004000-2078750/" if cfg["direction"]=="СПБ-СЕВ" else "https://grandtrain.ru/search/2078750-2004000/"
    for dt in cfg["dates"]:
        url = base + dt + "/"
        try:
            async with aiohttp.ClientSession() as s, s.get(url) as r:
                txt = await r.text()
            # базовая проверка: появление куцев/плцкарт
            if cfg["type"] in txt.lower():
                await bot.send_message(chat_id, f"🎉 {cfg['type'].capitalize()} найдено на {dt}\n{url}")
                cfg["running"] = False
                return
        except Exception as e:
            await bot.send_message(chat_id, "Ошибка при проверке: " + str(e))

if __name__=="__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
