import talib
import talib.abstract as ta
from talib import MA_Type
import dataframe

import pandas as pd
import numpy as np

COLUMNS_TRAINING_DATA_V2 = [
    'per', 'pbr', 'roe',
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

class StockData:
    def __init__(self, code, dataframe):
        self.code = code
        self.dataframe = dataframe

    def calcIndicators(self):
        close_list = np.asarray(self.dataframe["close"], dtype='f8')
        volume_list = np.asarray(self.dataframe["volume"], dtype='f8')

        # 이평선 계산
        self.dataframe["close_sma5"] = ta._ta_lib.SMA(close_list, 5)
        self.dataframe["close_sma10"] = ta._ta_lib.SMA(close_list, 10)
        self.dataframe["close_sma20"] = ta._ta_lib.SMA(close_list, 20)
        self.dataframe["close_sma60"] = ta._ta_lib.SMA(close_list, 60)
        self.dataframe["close_sma120"] = ta._ta_lib.SMA(close_list, 120)

        self.dataframe["close_ema5"] = ta._ta_lib.EMA(close_list, 5)
        self.dataframe["close_ema10"] = ta._ta_lib.EMA(close_list, 10)
        self.dataframe["close_ema20"] = ta._ta_lib.EMA(close_list, 20)
        self.dataframe["close_ema60"] = ta._ta_lib.EMA(close_list, 60)
        self.dataframe["close_ema120"] = ta._ta_lib.EMA(close_list, 120)

        self.dataframe["close_wma5"] = ta._ta_lib.WMA(close_list, 5)
        self.dataframe["close_wma10"] = ta._ta_lib.WMA(close_list, 10)
        self.dataframe["close_wma20"] = ta._ta_lib.WMA(close_list, 20)
        self.dataframe["close_wma60"] = ta._ta_lib.WMA(close_list, 60)
        self.dataframe["close_wma120"] = ta._ta_lib.WMA(close_list, 120)

        self.dataframe["volume_sma5"] = ta._ta_lib.SMA(volume_list, 5)
        self.dataframe["volume_sma10"] = ta._ta_lib.SMA(volume_list, 10)
        self.dataframe["volume_sma20"] = ta._ta_lib.SMA(volume_list, 20)
        self.dataframe["volume_sma60"] = ta._ta_lib.SMA(volume_list, 60)
        self.dataframe["volume_sma120"] = ta._ta_lib.SMA(volume_list, 120)

        self.dataframe["volume_ema5"] = ta._ta_lib.EMA(volume_list, 5)
        self.dataframe["volume_ema10"] = ta._ta_lib.EMA(volume_list, 10)
        self.dataframe["volume_ema20"] = ta._ta_lib.EMA(volume_list, 20)
        self.dataframe["volume_ema60"] = ta._ta_lib.EMA(volume_list, 60)
        self.dataframe["volume_ema120"] = ta._ta_lib.EMA(volume_list, 120)

        self.dataframe["volume_wma5"] = ta._ta_lib.WMA(volume_list, 5)
        self.dataframe["volume_wma10"] = ta._ta_lib.WMA(volume_list, 10)
        self.dataframe["volume_wma20"] = ta._ta_lib.WMA(volume_list, 20)
        self.dataframe["volume_wma60"] = ta._ta_lib.WMA(volume_list, 60)
        self.dataframe["volume_wma120"] = ta._ta_lib.WMA(volume_list, 120)

        return self.dataframe