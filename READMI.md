# Автоматизированная торговля через плотности на futures binance
Алгорим торговли основан на поиске плотности, которая сможет способствовать быстрому движении цены

## Содержание
- [Алгоритм программы](#алгоритм)
- [Настройка](#настройка)
- [Запуск](#запуск)

## Алгоритм
1 Определение высоковолатильночти монеты, за счет изменения ее за последние 5 минут
2 Определение плотности(в долларах), которую нужно искать для высоковолатильных монет
3 При нахождении плотности, слежка за ней в течении минуты
4 Когда разъедена плотность больше установленного порога, заход в позицию (ask-long, bid-short)
5 Выставление стоп лосса и несколько тейков с разницей 0,25%

## Настройка
Для начала нужно указать данные в config.py:
```python
telegram_key = ''
chat_id = ''
api_key = ''
api_secret = ''
LVL = 1000000
volume = 50
balance = 50000
stop_loss_need = 0.3
take_profit_need = 1
delta_need = 90
cound_takes = 4
lvl_percent = 100
wait_find_coin_minute = 10
wait_close_position_minute = 5
```
Пояснение по данным
```python
telegram_key = ''
```
Api-ключ бота телеграм, создаем в @BotFather. Нужно для получения уведомлений в телеграм.
```python
chat_id = ''
```
Id вашего телеграм аккаунта, получаем в @userinfobot.
```python
api_key = ''
api_secret = ''
```
Api-key и api-secret создаем здесь [binance](https://www.binance.com/ru/my/settings/api-management).
Обязательно включить фьючерсы.
```python
LVL = 1000000
```
Значение в долларах, если не смогли найти среднюю плотность + lvl_percent в монете, используем это значение
```python
volume = 50
balance = 50000
```
Volume - размер позиции в долларах. Balance - условное значение, не имеет никакого смысла, но должно быть больше volume.
```python
stop_loss_need = 0.3
take_profit_need = 1
```
Stop_loss_need - значение в %, установка порога стоп-лосс. Take_profit_need - аналогично с stop_loss_need
```python
delta_need = 90
```
Значение в процентах, порог разъедания плотности который нужно преодолеть для захода в позицию
```python
cound_takes = 4
```
Количество тейков, который выставяться для закрытия позиции, шаг в 0,25%
```python
wait_find_coin_minute = 10
wait_close_position_minute = 5
```
Wait_find_coin_minute - Значение в минутах, используется при поиске плотностей в монете, если прошло столько времени сколько указано, передстаем искать в этом монете плотность.
wait_close_position_minute - Значение в минутах, используется когда мы находимся в сделке, когда пройдет установленное значение, происходит принудительный выход из позиции, не смотря на исход текущей позиции.

## Запуск
Для работы программы нужно установить [Docker](https://www.docker.com/products/docker-desktop/).
Сборка
```bash
$ git clone https://github.com/PyRasta/test_task_.git <your project name>
$ cd <your project name>
$ docker build -t your_project_name .
```
Запуск
```bash
$ docker run -d --name your_project_name --restart always your_project_name
```
Просмотр логов
```bash
$ docker logs your_project_name
```