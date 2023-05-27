import time
import json
import logging

from binance.enums import *
from bs4 import BeautifulSoup
from telebot import TeleBot

from config import LVL


def on_close(ws, close_status_code, close_msg):
    logging.info("### closed ###")


def load_lvl_json():
    try:
        with open('lvl.json') as file:
            coins = json.load(file)
        return coins
    except:
        return {}


def dumb_lvl_json(coins):
    with open('lvl.json', 'w') as file:
        file.write(json.dumps(coins))


def write_new_lvl_coin(coin, lvl):
    coins = load_lvl_json()
    coin = coin.lower()
    coins[coin] = {
        'results': [],
        'lvl': lvl
    }
    dumb_lvl_json(coins)


def write_lvl_coin(coin):
    coins = load_lvl_json()
    coin = coin.lower()
    coins[coin]['lvl'] += 100000
    dumb_lvl_json(coins)


def get_count(number):
    s = str(number)
    if '.' in s:
        return abs(s.find('.') - len(s)) - 1
    else:
        return 0


def write_result(coin, result):
    coins = load_lvl_json()
    coin = coin.lower()
    coins[coin]['results'].append(result)
    dumb_lvl_json(coins)


def get_lvl(coin):
    coins = load_lvl_json()
    coin = coin.lower()
    try:
        return coins[coin]['lvl']
    except:
        return LVL


def get_ratio_wins(coin):
    coins = load_lvl_json()
    coin = coin.lower()
    results = coins[coin]['results']
    win = 0
    len_results = len(results)
    for i in results:
        if i:
            win += 1
    res = win / len_results * 100
    return res


def find_best_transaction(coin, order_book, lvl):
    bid = False
    ask = False
    for bids in order_book['bids']:
        total = float(bids[0]) * float(bids[1])
        price_now = order_book['bids'][0][0]
        delta = round((float(bids[0]) - float(price_now)) / float(price_now) * 100, 2)
        if total >= lvl and abs(delta) <= 0.3:
            bid = 'bid', coin, float(bids[0]), float(bids[1]), total, abs(delta)
    for asks in order_book['asks']:
        total = float(asks[0]) * float(asks[1])
        price_now = order_book['asks'][0][0]
        delta = round((float(asks[0]) - float(price_now)) / float(price_now) * 100, 2)
        if total >= lvl and abs(delta) <= 0.3:
            ask = 'ask', coin, float(asks[0]), float(asks[1]), total, abs(delta)
    if bid and ask:
        return False, False
    else:
        return bid, ask


def check_price(order_book, type_order_book, price):
    bool_price = False
    total = 0
    for i in order_book[type_order_book]:
        if float(i[0]) == price:
            bool_price = True
            total = float(i[0]) * float(i[1])
    return bool_price, total