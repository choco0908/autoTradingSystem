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

Use Anaconda (Python distribution platform)

1. Trader
 - python 3.6
 - trader is using tensorflow, numpy, pandas, scipy, talib
 - pip install TA_Lib-0.4.19-cp36-cp36m-win_amd64.whl tensorflow-gpu=1.15.2 pandas scipy requests matplotlib mplfinance keras==2.2.4 h5py==2.10.0

2. Bridge Server
 - python 3.7 32bit
 - koapy (https://koapy.readthedocs.io/en/latest/index.html)
 - kiwoom OpenApi+ (https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)
 - Flask
 - pip install python-dateutil flask mpld3 koapy

# Ideas

1. kiwoom OpenApi+ is available only in 32bit environment
2. Seperate Kiwoom trader and Actor(Reinforcement learning Agent)
3. Need Simple Api Server to connect between open api and deep learning

# Details

1. Trader
 - Trader is learning stocks data to predict when is time to buy,sell or hold.
 - Trader decide action using A2C Reinforcement Models and LSTM Neural Network.
 - Trader is getting reward under conditions which are 60% win/loss
 - Stocks data contain OHLC Daily chart data, Kospi Daily char data, MACD histogram, RSI

2. Bridge Server
 - To get and update stocks data, use Python Flask for Api Server
 - To use kiwoom OpenApi+, import koapy library
 - The Bridge Server is log in kiwoom server and get stocks data from kiwoom with koapy

3. Database
 - Use sqlite3 to store data
 - The Trader is getting chart/kospi data and learning from DataBase/DB/stocks.db
 - The Bridge Server is storing chart/kospi data to DataBase/DB/stocks.db from kiwoom server

# Installation

1. Install Anaconda
2. Make python3.7 32bit and python3.6 in venv (using conda create)
3. Install each python packages with requirements
4. Install CUDA Toolkit (https://developer.nvidia.com/cuda-toolkit-archive) for GPU

# Testing

1. To learning
    - activate py36
    - python Analysis\tf_gpu.py --stock_code {$} --rl_method {$} --net {$} --num_steps {$} --output_name {$} --learning --num_epoches {$} --lr {$} --start_epsilon {$} --discount_factor {$} --ver {$} --delayed_reward_threshold {$} --start_date {$} --end_date {$} --value_network_name {$} --policy_network_name {$}
    
2. To Trading
    - activate py37_32
    - python Bridge\kiwoom_bridge_flask.py
      
    - activate py36
    - python Analysis\tf_gpu.py --stock_code {$} --reuse_models --rl_method {$} --net {$} --ver {$} 
