import MetaTrader5 as mt5
import pandas as pd
import time
import ta



# Main settings
magic = 12345678
account_id = 1234567890

# Symbol settings
symbol = 'EURUSD'
sl_multiplier = 13

lot = 0.1
add_lot = 0.01
min_deleverage = 15
deleverage_steps = 7
take_profit_short = 21
sl_short = take_profit_short * sl_multiplier


# Init
if not mt5.initialize():
    print('initialize() failed, error code =', mt5.last_error())
    quit()

# Timeframe settings
timeframe = mt5.TIMEFRAME_M1

selected = mt5.symbol_select(symbol)
if not selected:
    print('symbol_select({}) failed, error code = {}'.format(symbol, mt5.last_error()))
    quit()

# Get bars and calculate SMA
def get_sma():
    bars = mt5.copy_rates_from_pos(symbol, timeframe, 0, 240)
    if bars is None:
        print('copy_rates_from_pos() failed, error code =', mt5.last_error())
        quit()

    df = pd.DataFrame(bars)
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    df.drop(columns=['time'], inplace=True)
    df['sma_6H'] = ta.trend.sma_indicator(df['high'], window=6)
    df['sma_6L'] = ta.trend.sma_indicator(df['low'], window=6)
    df['sma_33'] = ta.trend.sma_indicator(df['close'], window=33)
    df['sma_60'] = ta.trend.sma_indicator(df['close'], window=60)
    df['sma_120'] = ta.trend.sma_indicator(df['close'], window=120)
    df['sma_240'] = ta.trend.sma_indicator(df['close'], window=240)

    global sma6H, sma6L, sma33, sma60, sma120, sma240
    sma6H = df['sma_6H'].iloc[-1]
    sma6L = df['sma_6L'].iloc[-1]
    sma33 = df['sma_33'].iloc[-1]
    sma60 = df['sma_60'].iloc[-1]
    sma120 = df['sma_120'].iloc[-1]
    sma240 = df['sma_240'].iloc[-1]

    # print("SMA 6H:", sma6H)
    # print("SMA 6L:", sma6L)
    # print("SMA 33:", sma33)
    # print("SMA 60:", sma60)
    # print("SMA 120:", sma120)
    # print("SMA 240:", sma240)

def get_position_data():
    positions=mt5.positions_get(symbol=symbol)
    # print(positions)
    if positions == None:
        print(f'No positions on {symbol}')
    elif len(positions) > 0:
        # print(f'Total positions on {symbol} =',len(positions))
        for position in positions:
            post_dict = position._asdict()
            global pos_price, identifier, volume
            pos_price = post_dict['price_open']
            identifier = post_dict['identifier']
            volume = post_dict['volume']
            print(pos_price, identifier, volume)


# Define prices
def get_ask_bid():
    global ask, bid
    ask = mt5.symbol_info_tick(symbol).ask
    bid = mt5.symbol_info_tick(symbol).bid

point = mt5.symbol_info(symbol).point
deviation = 20


while True:

    identifier = 0
    volume = 0
    pos_price = 0 

    get_sma()
    get_ask_bid()
    get_position_data()

    # Define Sell Order

    sell_order = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "price": ask,
        "sl": ask + sl_short * point,
        "tp": ask - take_profit_short * point,
        "deviation": deviation,
        "magic": magic,
        "comment": "python short",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        }

    additional_sell_order = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": add_lot,
        "type": mt5.ORDER_TYPE_SELL,
        "price": ask,
        "sl": pos_price + sl_short * point,
        "tp": pos_price - take_profit_short * point,
        "deviation": deviation,
        "magic": magic,
        "comment": "python short",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        }

    sltp_request_sell_pos = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_SELL,
        "position": identifier,
        "sl": pos_price + sl_short * point,
        "tp": pos_price - take_profit_short * point,
        "magic": magic,
        "comment": "Change stop loss for Sell position",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    sltp_request_buy_pos = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY,
        "position": identifier,
        "sl": pos_price - sl_short * point,
        "tp": pos_price + take_profit_short * point,
        "magic": magic,
        "comment": "Change stop loss for Buy position",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Check if MA order os OK
    good_long_ma_order = ask > sma6H

    # First Entry
    if pos_price == 0 and good_long_ma_order:
        sell = mt5.order_send(sell_order)
    else:
        print(f' {symbol} Not Ready')

    # Additional Entry
    if pos_price > 0 and good_long_ma_order and sma6L > pos_price:
        sell = mt5.order_send(additional_sell_order)
        time.sleep(0.01)
        check_sl = mt5.order_send(sltp_request_sell_pos)

    time.sleep(0.1)
