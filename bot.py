import time
import json
import logging
import datetime

import websocket
from binance.enums import *

from config import chat_id, volume, balance, stop_loss_need, take_profit_need, delta_need, cound_takes, wait_close_position_minute
from functions import get_lvl, find_best_transaction, check_price, on_close

class Bot:
    def __init__(self, coin, client, telegram_bot):
        self.coin = coin
        self.total = 0
        self.position = [False, '']
        self.type_order_book = ''
        self.price_spot = 0
        self.price_fut = 0
        self.order_id_stop = ''
        self.orders_id_take = []
        self.qty = 0
        self.stop_loss_need = stop_loss_need
        self.take_profit_need = take_profit_need
        self.volume = volume
        self.balance = balance
        self.start_time = False
        self.client = client
        self.telegram_bot = telegram_bot
        self.precision_qty = 0

    def on_message(self, ws, message):
        data = json.loads(message)
        lvl = get_lvl(self.coin)
        bid, ask = find_best_transaction(self.coin, data, lvl)
        if self.balance >= self.volume:
            if self.total == 0:
                if ask:
                    self.total = ask[4]
                    self.price_spot = ask[2]
                    self.type_order_book = 'asks'
                    logging.info(ask)
                elif bid:
                    self.total = bid[4]
                    self.price_spot = bid[2]
                    self.type_order_book = 'bids'
                    logging.info(bid)
                else:
                    logging.info(f'[LOG] Снята плотность: {self.coin}')
                    ws.close()
            else:
                if not self.start_time:
                    self.start_time = datetime.datetime.now()
                time_now = datetime.datetime.now()
                time_delta = time_now - self.start_time
                if time_delta.seconds <= 1 * 60:
                    bool_price, total_new = check_price(data, self.type_order_book, self.price_spot)
                    if bool_price:
                        if self.type_order_book == 'asks':
                            if ask: logging.info(ask)
                            delta = abs(((total_new - self.total) / self.total * 100))
                            logging.info(
                                f'Coin: {self.coin}, Плотность: {bool_price}, В долларах: {total_new}, Остаток: {delta}')
                            if delta >= delta_need:
                                logging.info(f'LONG {self.coin}')
                                self.position = [True, 'LONG']
                                ws.close()
                        else:
                            if bid: logging.info(bid)
                            delta = abs(((total_new - self.total) / self.total * 100))
                            logging.info(
                                f'Coin: {self.coin}, Плотность: {bool_price}, В долларах: {total_new}, Остаток: {delta}')
                            if delta >= delta_need:
                                logging.info(f'SHORT {self.coin}')
                                self.position = [True, 'SHORT']
                                ws.close()
                    else:
                        if self.type_order_book == 'asks':
                            logging.info(f'LONG {self.coin}')
                            self.position = [True, 'LONG']
                        elif self.type_order_book == 'bids':
                            logging.info(f'SHORT {self.coin}')
                            self.position = [True, 'SHORT']
                        ws.close()
                else:
                    logging.info(f'[LOG] Твое время ВЫШЛО!!!!')
                    ws.close()
        else:
            logging.info(f'[LOG] Баланс меньше установленного объема')
            ws.close()

    def get_price_stop(self, stop_loss_need):
        precision = 2
        exchange_info = self.client.futures_exchange_info()['symbols']
        for i in exchange_info:
            if i['symbol'] == self.coin:
                precision = i['pricePrecision']
        if self.position[1] == 'LONG':
            value = self.client.futures_position_information(symbol=self.coin)[0]['entryPrice']
            if value[0] == '-':
                value = value[1:]
            price = float(value) - ((float(value) / 100) * stop_loss_need)
        else:
            value = self.client.futures_position_information(symbol=self.coin)[0]['entryPrice']
            if value[0] == '-':
                value = value[1:]
            price = float(value) + ((float(value) / 100) * stop_loss_need)
        return str(round(price, precision))

    def get_price_win(self, precision=None):
        if precision is None:
            exchange_info = self.client.futures_exchange_info()['symbols']
            for i in exchange_info:
                if i['symbol'] == self.coin:
                    precision = i['pricePrecision']
        if self.position[1] == 'LONG':
            value = self.client.futures_position_information(symbol=self.coin)[0]['entryPrice']
            if value[0] == '-':
                value = value[1:]
            price = float(value) + ((float(value) / 100) * self.take_profit_need)
        else:
            value = self.client.futures_position_information(symbol=self.coin)[0]['entryPrice']
            if value[0] == '-':
                value = value[1:]
            price = float(value) - ((float(value) / 100) * self.take_profit_need)
        return str(round(price, precision)), precision

    def stop_loss_limit(self, stop_loss_need):
        stop_loss_value = self.get_price_stop(stop_loss_need)
        try:
            if self.position[1] == 'LONG':
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_STOP,
                    quantity=str(self.qty),
                    price=stop_loss_value,
                    stopPrice=stop_loss_value
                )
            else:
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_STOP,
                    quantity=str(self.qty),
                    price=stop_loss_value,
                    stopPrice=stop_loss_value
                )
            self.order_id_stop = response['orderId']
            return True
        except:
            return False

    def stop_loss(self, stop_loss_need):
        try:
            stop_loss_value = self.get_price_stop(stop_loss_need)
            if self.position[1] == 'LONG':
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                    stopPrice=stop_loss_value,
                    closePosition='true'
                )
            else:
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                    stopPrice=stop_loss_value,
                    closePosition='true'
                )
            self.order_id_stop = response['orderId']
            return True
        except:
            return False

    def take_profit(self):
        try:
            take_profit_value = self.get_price_win()
            if self.position[1] == 'LONG':
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                    stopPrice=take_profit_value,
                    closePosition='true'
                )
            else:
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                    stopPrice=take_profit_value,
                    closePosition='true'
                )
            self.orders_id_take.append(response['orderId'])
            return True
        except:
            return False

    def take_profit_limit(self, precision_price=None):
        try:
            take_profit_value, precision_price = self.get_price_win(precision_price)
            qty = float(self.qty) / cound_takes
            qty = round(qty, self.precision_qty)
            if self.position[1] == 'LONG':
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_TAKE_PROFIT,
                    quantity=str(qty),
                    price=take_profit_value,
                    stopPrice=take_profit_value,
                )
            else:
                response = self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_TAKE_PROFIT,
                    quantity=str(qty),
                    price=take_profit_value,
                    stopPrice=take_profit_value,
                )
            self.orders_id_take.append(response['orderId'])
            return True
        except Exception as error:
            print(error)
            time.sleep(1)
            if len(error.args) >= 3:
                if json.loads(error.args[2])['msg'] != 'Precision is over the maximum defined for this asset.':
                    if precision_price < 0:
                        return False
                    else:
                        return self.take_profit_limit(precision_price-1)
            else:
                return False

    def long(self):
        precision = 3
        if self.position[0]:
            try:
                exchange_info = self.client.futures_exchange_info()['symbols']
                for i in exchange_info:
                    if i['symbol'] == self.coin:
                        precision = i['quantityPrecision']
                position = self.client.futures_position_information(symbol=self.coin)[0]
                if float(position['positionAmt']) != 0:
                    qty = float(position['positionAmt'].replace('-', ''))
                else:
                    qty = round(self.volume / float(self.price_fut), precision)
                self.precision_qty = precision
                self.qty = qty
                self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_MARKET,
                    quantity=str(qty)
                )
            except Exception as error:
                logging.info('Не сработал лонг')
                logging.info(error)
                time.sleep(1)
                return self.long()

    def short(self):
        precision = 3
        if self.position[0]:
            try:
                exchange_info = self.client.futures_exchange_info()['symbols']
                for i in exchange_info:
                    if i['symbol'] == self.coin:
                        precision = i['quantityPrecision']
                position = self.client.futures_position_information(symbol=self.coin)[0]
                if float(position['positionAmt']) != 0:
                    qty = float(position['positionAmt'].replace('-', ''))
                else:
                    qty = round(self.volume / float(self.price_fut), precision)
                self.precision_qty = precision
                self.qty = qty
                self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_MARKET,
                    quantity=str(qty),
                )
            except Exception as error:
                logging.info('Не сработал шорт')
                logging.info(error)
                time.sleep(1)
                return self.short()

    def tracking_stop_loss(self):
        try:
            if self.position[1] == 'LONG':
                self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_SELL,
                    type='TRAILING_STOP_MARKET',
                    callbackRate=self.take_profit_need,
                    quantity=self.qty,
                )
            else:
                self.client.futures_create_order(
                    symbol=self.coin,
                    side=SIDE_BUY,
                    type='TRAILING_STOP_MARKET',
                    callbackRate=self.take_profit_need,
                    quantity=self.qty,
                )
            return True
        except:
            return False

    def open_stop_loss(self):
        result = self.stop_loss(self.stop_loss_need)
        return result

    def open_take_profit(self):
        old_take_profit_need = self.take_profit_need
        for _ in range(cound_takes):
            result = self.take_profit_limit()
            if not result:
                return False
            self.take_profit_need += 0.25
        self.take_profit_need = old_take_profit_need
        return result

    def wait_close_position(self):
        n = 0
        try:
            position = self.client.futures_position_information(symbol=self.coin)[0]['positionAmt']
        except:
            position = 1
        while float(position) != 0:
            n += 1
            time.sleep(60)
            try:
                position = self.client.futures_position_information(symbol=self.coin)[0]['positionAmt']
            except:
                position = 1
            if n == wait_close_position_minute:
                for order_id_take in self.orders_id_take:
                    try:
                        self.client.futures_cancel_order(symbol=self.coin, orderId=order_id_take)
                    except:
                        time.sleep(5)
                self.close_position()
                break

    def clear_orders(self):
        try:
            self.client.futures_cancel_order(symbol=self.coin, orderId=self.order_id_stop)
            self.telegram_bot.send_message(chat_id, f'{self.position[1]}: {self.coin} +++')
        except Exception:
            for order_id_take in self.orders_id_take:
                try:
                    self.client.futures_cancel_order(symbol=self.coin, orderId=order_id_take)
                except:
                    time.sleep(5)
            self.telegram_bot.send_message(chat_id, f'{self.position[1]}: {self.coin} ---')

    def close_position(self):
        position = self.client.futures_position_information(symbol=self.coin)[0]
        if float(position['positionAmt']) != 0:
            if self.position[1] == 'LONG':
                self.short()
            if self.position[1] == 'SHORT':
                self.long()

    def open_position(self):
        self.telegram_bot.send_message(chat_id, f'[Открываем позицию]{self.position[1]}: {self.coin}')
        if self.position[1] == 'LONG':
            self.long()
        if self.position[1] == 'SHORT':
            self.short()
        self.telegram_bot.send_message(chat_id, f'[Открыта позиция]{self.position[1]}: {self.coin}')
        status_stop_loss = self.open_stop_loss()
        if status_stop_loss:
            self.telegram_bot.send_message(chat_id, f'[Открыт стоп лосс]{self.position[1]}: {self.coin}')
            status_take_profit = self.open_take_profit()
            if not status_take_profit:
                self.close_position()
                self.telegram_bot.send_message(chat_id, f'[Закрыта из-за не открытых тейков]{self.position[1]}: {self.coin}')

            else:
                self.telegram_bot.send_message(chat_id, f'[Открыты тейки]{self.position[1]}: {self.coin}')
        else:
            self.close_position()
            self.telegram_bot.send_message(chat_id, f'[Закрыта из-за не открытого стоп лосса]{self.position[1]}: {self.coin}')

    def run(self):
        if not self.position[0]:
            ws = websocket.WebSocketApp(f"wss://stream.binance.com:9443/ws/{self.coin.lower()}@depth10@100ms",
                                        on_message=self.on_message,
                                        on_close=on_close)
            ws.run_forever()
        if self.position[0]:
            price_fut = False
            try:
                price_fut = self.client.futures_symbol_ticker(symbol=self.coin)['price']
                self.price_fut = price_fut
            except Exception as error:
                logging.info('Не получен прайс: ', self.coin)
                logging.info(error)
            if price_fut:
                self.open_position()
                self.wait_close_position()
                self.clear_orders()