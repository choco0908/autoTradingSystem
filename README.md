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
