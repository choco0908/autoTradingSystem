# STockDataTaLib.py Merge
import talib
import talib.abstract as ta
from talib import MA_Type

import pandas as pd
import numpy as np
from scipy.stats import zscore

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from DataBase.SqliteDB import StockDB

COLUMNS_CHART_DATA = ['date', 'open', 'high', 'low', 'close', 'volume']

COLUMNS_TRAINING_DATA_V1 = [
    'open_lastclose_ratio', 'high_close_ratio', 'low_close_ratio',
    'close_lastclose_ratio', 'volume_lastvolume_ratio',
    'close_ma5_ratio', 'volume_ma5_ratio',
    'close_ma10_ratio', 'volume_ma10_ratio',
    'close_ma20_ratio', 'volume_ma20_ratio',
    'close_ma60_ratio', 'volume_ma60_ratio',
    'close_ma120_ratio', 'volume_ma120_ratio',
    'rsi', 'macdhist'
]

COLUMNS_TRAINING_DATA_V2 = [
    'open_lastclose_ratio', 'high_close_ratio', 'low_close_ratio',
    'close_lastclose_ratio', 'volume_lastvolume_ratio',
    'close_ma5_ratio', 'volume_ma5_ratio',
    'close_ma10_ratio', 'volume_ma10_ratio',
    'close_ma20_ratio', 'volume_ma20_ratio',
    'close_ma60_ratio', 'volume_ma60_ratio',
    'close_ma120_ratio', 'volume_ma120_ratio',
    'market_kospi_ma5_ratio', 'market_kospi_ma20_ratio',
    'market_kospi_ma60_ratio', 'market_kospi_ma120_ratio',
    'rsi', 'macdhist'
]
'''
COLUMNS_TRAINING_DATA_V2 = [
    'open_lastclose_ratio', 'high_close_ratio', 'low_close_ratio',
    'close_lastclose_ratio', 'volume_lastvolume_ratio',
    'close_ma5_ratio', 'volume_ma5_ratio',
    'close_ma10_ratio', 'volume_ma10_ratio',
    'close_ma20_ratio', 'volume_ma20_ratio',
    'close_ma60_ratio', 'volume_ma60_ratio',
    'close_ma120_ratio', 'volume_ma120_ratio',
    'market_kospi_ma5_ratio', 'market_kospi_ma20_ratio',
    'market_kospi_ma60_ratio', 'market_kospi_ma120_ratio',
    'bond_k3y_ma5_ratio', 'bond_k3y_ma20_ratio',
    'bond_k3y_ma60_ratio', 'bond_k3y_ma120_ratio'
]
'''

def preprocess(data, ver='v1'):
    close_list = np.asarray(data['close'], dtype='f8')
    volume_list = np.asarray(data['volume'], dtype='f8')
    if ver == 'v2':
        kospi_list = np.asarray(data['kospi'], dtype='f8')

    windows = [5, 10, 20, 60, 120]
    for window in windows: # ?????? ???????????? ?????? ???????????? ??? ????????? ?????? ????????? ????????? ??????
        data['close_ma{}'.format(window)] = data['close'].rolling(window).mean()
        #data['close_sma{}'.format(window)] = ta._ta_lib.SMA(close_list, window)
        #data['close_ema{}'.format(window)] = ta._ta_lib.EMA(close_list, window)
        #data['close_wma{}'.format(window)] = ta._ta_lib.WMA(close_list, window)
        data['volume_ma{}'.format(window)] = data['volume'].rolling(window).mean()
        #data['volume_sma{}'.format(window)] = ta._ta_lib.SMA(volume_list, window)
        #data['volume_ema{}'.format(window)] = ta._ta_lib.EMA(volume_list, window)
        #data['volume_wma{}'.format(window)] = ta._ta_lib.WMA(volume_list, window)
        data['close_ma%d_ratio' % window] = (data['close'] - data['close_ma%d' % window]) / data['close_ma%d' % window]
        data['volume_ma%d_ratio' % window] = (data['volume'] - data['volume_ma%d' % window]) / data['volume_ma%d' % window]
        if ver == 'v2':
            data['market_kospi_ma{}'.format(window)] = data['kospi'].rolling(window).mean()
            data['market_kospi_ma%d_ratio' % window] = (data['kospi'] - data['market_kospi_ma%d' % window]) / data['market_kospi_ma%d' % window]

    # ?????? ?????? ?????? ?????? : (?????? ?????? - ???????????????)/???????????????

    data['open_lastclose_ratio'] = np.zeros(len(data))
    data.loc[1:, 'open_lastclose_ratio'] = (data['open'][1:].values - data['close'][:-1].values) / data['close'][:-1].values
    data['high_close_ratio'] = (data['high'].values - data['close'].values) / data['close'].values
    data['low_close_ratio'] = (data['low'].values - data['close'].values) / data['close'].values
    data['close_lastclose_ratio'] = np.zeros(len(data))
    data.loc[1:, 'close_lastclose_ratio'] = (data['close'][1:].values - data['close'][:-1].values) / data['close'][:-1].values
    data['volume_lastvolume_ratio'] = np.zeros(len(data))
    data.loc[1:, 'volume_lastvolume_ratio'] = (data['volume'][1:].values - data['volume'][:-1].values)/ data['volume'][:-1].replace(to_replace=0, method='ffill').replace(to_replace=0, method='bfill').values

    # RSI ?????? ??????
    data['rsi'] = ta._ta_lib.RSI(close_list, 14)

    # MACD ?????? ??????
    macd, macdsignal, macdhist = ta._ta_lib.MACD(close_list, 12, 26, 9)
    data['macd'] = macd
    data['macdsignal'] = macdsignal
    data['macdhist'] = macdhist

    return data

def load_data(code, date_from, date_to, ver='v2'):
    stock_db = StockDB()
    tname = stock_db.getTableName(code)
    df = stock_db.load(tname)
    if ver == 'v2':
        kname = stock_db.getTableName('kospi')
        kdf = stock_db.load(kname)
        kdf = kdf[['date', 'close']]
        kdf.columns = ['date', 'kospi']
        result = pd.merge(df, kdf, how='inner', on='date')

    if ver == 'v1':
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    elif ver == 'v2':
        result.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'kospi']
        df = result


    # ?????? ???????????? ??????
    data = df.sort_values(by='date').reset_index()

    # ????????? ?????????
    data = preprocess(data, ver=ver)

    # ?????? ?????????
    data = data.astype({'date': 'str'})
    data = data[(data['date'] >= date_from) & (data['date'] <= date_to)]
    data = data.dropna()

    # ?????? ????????? ??????
    chart_data = data[COLUMNS_CHART_DATA]

    # ?????? ????????? ??????
    training_data = None
    if ver == 'v1':
        training_data = data[COLUMNS_TRAINING_DATA_V1]
    elif ver == 'v2':
        training_data = data[COLUMNS_TRAINING_DATA_V2]
        training_data['rsi'] = zscore(training_data['rsi'])
        training_data['macdhist'] = zscore(training_data['macdhist'])
        training_data = training_data.apply(np.tanh)
    else:
        raise Exception('Invalid version.')

    return chart_data, training_data