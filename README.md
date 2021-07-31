# AutoTradingSystem
 키움증권 자동매매프로그램

# Basic

1. Trader
 - tf_gpu.py : main file for Reinforcement learning
 - agent.py : decide action to trade and validate
 - policy_learner.py : define Reinforcement Models
 - policy_network.py : define Neural Network Models
 - visualizer.py : visualize chart data to graph

2. Bridge Server For Win32
 - kiwwom_bridge_flask.py : bridge server connecting between Trader to Kiwoom OpenApi+

3. DataBase
 - store and share database with sqlite3

# Requirements and Environment

1. Trader
 - python 3.6
 - trader is using tensorflow, numpy, pandas, scipy, talib

2. Bridge Server
 - python 3.7 32bit
 - koapy (https://koapy.readthedocs.io/en/latest/index.html)
 - kiwoom OpenApi+ (https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)

# Details

