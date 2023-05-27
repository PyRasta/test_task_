import time
import json
import logging
import datetime
import statistics

import websocket
import multiprocessing
import requests

from binance import Client
from binance.enums import *
from telebot import TeleBot

from config import api_key, api_secret, telegram_key, lvl_percent, wait_find_coin_minute
from functions import get_lvl, find_best_transaction, on_close, write_new_lvl_coin
from bot import Bot


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
client = Client(api_key=api_key, api_secret=api_secret)
telegram_bot = TeleBot(telegram_key)


class WatchDensity:
    def __init__(self):
        self.start_time = datetime.datetime.now()

    def run(self, ws, message):
        data = json.loads(message)
        coin = multiprocessing.current_process().name
        lvl = get_lvl(coin)
        bid, ask = find_best_transaction(coin, data, lvl)
        time_now = datetime.datetime.now()
        time_delta = time_now - self.start_time
        if time_delta.seconds >= wait_find_coin_minute * 60:
            ws.close()
        elif bid or ask:
            ws.close()
            logging.info(f'Find coin: {coin.upper()}')
            bot = Bot(coin.upper(), client, telegram_bot)
            multiprocessing.Process(target=bot.run, name=coin).start()


def watching_coin(coin):
    watching_density = WatchDensity()
    ws = websocket.WebSocketApp(f"wss://stream.binance.com:9443/ws/{coin}@depth10@100ms",
                                on_message=watching_density.run,
                                on_close=on_close)
    ws.run_forever()


def get_coins():
    coins = []
    with open('coins.txt', 'r') as file:
        start_coins = file.readlines()
    start_coins = list(map(lambda x: x.replace('\n', ''), start_coins))
    for coin in start_coins:
        try:
            klines = client.get_klines(symbol=coin, interval=KLINE_INTERVAL_5MINUTE, limit=2)
            delta = abs(round((float(klines[0][4]) - float(klines[1][4])) / float(klines[1][4]) * 100, 2))
            if delta >= 1:
                coins.append(coin)
        except Exception:
            print('Плохой ', coin)
    return coins


def get_lvl_for_klines(coin):
    volumes = []
    for kline in client.get_klines(symbol=coin, interval=KLINE_INTERVAL_1MINUTE, limit=60):
        volumes.append(float(kline[5]) * float(kline[4]))
    mid_volume = statistics.mean(volumes)
    return mid_volume + ((mid_volume) / 100) * lvl_percent


def main():
    while True:
        try:
            logging.info('Поиск крипты')
            coins = get_coins()
            active_children = multiprocessing.active_children()
            name_active_children = list(map(lambda x: x.name.upper(), active_children))
            logging.info(coins)
            for coin in coins:
                if coin not in name_active_children:
                    lvl = get_lvl_for_klines(coin)
                    write_new_lvl_coin(coin, lvl)
                    logging.info(f'{coin}, {lvl}')
                    multiprocessing.Process(target=watching_coin, args=(coin.lower(),), name=coin.lower()).start()
                time.sleep(10)
            time.sleep(80)
        except Exception as error:
            logging.info(error)


if __name__ == "__main__":
    main()

