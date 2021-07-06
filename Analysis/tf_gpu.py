import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from DataBase.SqliteDB import StockDB # account 정보 조회
import logging
import argparse
import json

import settings
import utils
import data_manager

import requests

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stock_code', nargs='+') # 종목 코드
    parser.add_argument('--ver', choices=['v1', 'v2'], default='v2') # 사용할 데이터 버전
    parser.add_argument('--rl_method', choices=['dqn', 'pg', 'ac', 'a2c', 'a3c', 'monkey']) # 강화학습 방식
    parser.add_argument('--net', choices=['dnn', 'lstm', 'cnn', 'monkey'], default='dnn') # 가치/정책 신경망에서 사용할 신경망 유형
    parser.add_argument('--num_steps', type=int, default=1) # lstm/cnn 에서 사용할 step 수
    parser.add_argument('--lr', type=float, default=0.01) # 학습 속도
    parser.add_argument('--discount_factor', type=float, default=0.9) # 이전 행동에 대한 할인율
    parser.add_argument('--start_epsilon', type=float, default=0) # 시작 탐험률
    parser.add_argument('--balance', type=int, default=10000000) # 초기 자본금
    parser.add_argument('--num_epoches', type=int, default=100) # 수행할 에포크 수
    parser.add_argument('--delayed_reward_threshold', type=float, default=0.05) # 지연 보상의 임곗값
    parser.add_argument('--backend', choices=['tensorflow', 'plaidml'], default='tensorflow') # keras 백엔드
    parser.add_argument('--output_name', default=utils.get_time_str())
    parser.add_argument('--value_network_name')
    parser.add_argument('--policy_network_name')
    parser.add_argument('--reuse_models', action='store_true') # 신경망 재사용 유무
    parser.add_argument('--learning', action='store_true') # 강화학습 유무
    parser.add_argument('--start_date', default='20170101')
    parser.add_argument('--end_date', default='20171231')
    parser.add_argument('--base_num_stocks', type=int, default=0)
    parser.add_argument('--update', action='store_true')
    args = parser.parse_args()

    # args 업데이트 가능하도록 초기화
    stock_code_param = args.stock_code
    ver = args.ver
    rl_method = args.rl_method
    net = args.net
    num_steps = args.num_steps
    lr = args.lr
    discount_factor = args.discount_factor
    start_epsilon = args.start_epsilon
    balance = args.balance
    num_epoches = args.num_epoches
    delayed_reward_threshold = args.delayed_reward_threshold
    backend = args.backend
    output_name = args.output_name
    value_network_name = args.value_network_name
    policy_network_name = args.policy_network_name
    reuse_models = args.reuse_models
    learning = args.learning
    start_date = args.start_date
    end_date = args.end_date
    base_num_stocks = args.base_num_stocks

    stock_dict = {}

    if args.update and reuse_models:
        response = requests.get('http://127.0.0.1:5000/update_database')
        print('update_database '+str(response.status_code))

    # Keras Backend 설정
    if backend == 'tensorflow':
        os.environ['KERAS_BACKEND'] = 'tensorflow'
    elif backend == 'plaidml':
        os.environ['KERAS_BACKEND'] = 'plaidml.keras.backend'

    if reuse_models:
        response = requests.get('http://127.0.0.1:5000/update_account')
        print('update_account ' + str(response.status_code))
        stock_db = StockDB()
        account = stock_db.load_account_table().iloc[0].to_dict()
        base_balance = int(account['balance']) + int(account['totalbalance'])
        tname = 'account_detail_' + account['accountno']
        stock_df_list = stock_db.load_account_detail_table(tname).to_dict('records')
        initial_balance = int(base_balance / len(stock_df_list))
        for code in stock_code_param: # 신규 종목 매매
            stock_dict.update({code: {'count': 0, 'value_net': '{}_{}_value_{}'.format(rl_method, net, code),
                                      'policy_net': '{}_{}_policy_{}'.format(rl_method, net, code), 'rl_method': rl_method, 'net': net,
                                      'output': '{}_{}'.format(datetime.datetime.today().strftime('%Y%m%d'), code), 'winratio': 0.0,
                                      'havratio': 0.0, 'balance': initial_balance}})
        for stock in stock_df_list: # 기존 종목 매매
            code = stock['code']
            balance = initial_balance - stock['totalbuyprice'] if initial_balance > stock['totalbuyprice'] else 0
            stock_dict.update({code: {'count': stock['tradecount'], 'value_net': '{}_{}_value_{}'.format(rl_method, net, code),
                                      'policy_net': '{}_{}_policy_{}'.format(rl_method, net, code), 'rl_method': rl_method, 'net': net,
                                      'output': '{}_{}'.format(datetime.datetime.today().strftime('%Y%m%d'), code), 'winratio': stock['winratio'], 'havratio': stock['havratio'], 'balance': balance}})
        if len(stock_code_param) == 0:
            stock_code_param = stock_dict.keys()

        for code in stock_code_param:
            # 출력 경로 설정
            output_name = stock_dict[code]['output']
            output_path = os.path.join(settings.BASE_DIR, 'output/{}_{}_{}'.format(output_name, stock_dict[code]['rl_method'], stock_dict[code]['net']))
            if not os.path.isdir(output_path):
                os.makedirs(output_path)

            # 파라미터 기록
            with open(os.path.join(output_path, 'params.json'), 'w') as f:
                f.write(json.dumps(vars(args)))

            # 로그 기록 설정
            file_handler = logging.FileHandler(filename=os.path.join(output_path, "{}.log".format(output_name)),
                                                   encoding='utf-8')
            stream_handler = logging.StreamHandler(sys.stdout)
            file_handler.setLevel(logging.DEBUG)
            stream_handler.setLevel(logging.INFO)
            logging.basicConfig(format="%(message)s", handlers=[file_handler, stream_handler], level=logging.DEBUG)

            # 로그, Keras Backend 설정을 먼저하고 RLTrader 모듈들을 이후에 임포트해야 함
            from policy_learner import ReinforcementLearner, DQNLearner, PolicyGradientLearner, ActorCriticLearner, A2CLearner, A3CLearner

            common_params = {}
            list_stock_code = []
            list_chart_data = []
            list_training_data = []
            list_min_trading_unit = []
            list_max_trading_unit = []

            for stock_code in stock_code_param:
                base_num_stocks = int(stock_dict[stock_code]['count'])
                rl_method = stock_dict[stock_code]['rl_method']
                net = stock_dict[stock_code]['net']
                win_stock_ratio = stock_dict[stock_code]['winratio']
                have_stock_ratio = stock_dict[stock_code]['havratio']
                balance = stock_dict[stock_code]['balance']
                num_steps = 5
                start_epsilon = 0
                # num_steps 수만큼 데이터 불러옴
                tname = 'StockData_{}'.format(stock_code)
                df = stock_db.load_nrows(tname, num_steps)
                df = df[['date']]
                df = df.astype({'date': 'str'})
                start_date = df.iloc[num_steps-1]['date']
                end_date = df.iloc[0]['date']
                num_epoches = 1
                # 모델 경로 준비
                value_network_path = os.path.join(settings.BASE_DIR, 'models/{}.h5'.format(stock_dict[code]['value_net']))
                print(value_network_path)
                policy_network_path = os.path.join(settings.BASE_DIR, 'models/{}.h5'.format(stock_dict[code]['policy_net']))
                print(policy_network_path)

                # 차트 데이터, 학습 데이터 준비
                chart_data, training_data = data_manager.load_data(stock_code, start_date, end_date, ver=ver)

                # 최소/최대 투자 단위 설정
                min_trading_unit = max(int(100000 / chart_data.iloc[-1]['close']), 1)
                max_trading_unit = max(int(1000000 / chart_data.iloc[-1]['close']), 1)

                # 공통 파라미터 설정
                common_params = {'rl_method': rl_method, 'delayed_reward_threshold': delayed_reward_threshold,
                                 'net': net, 'num_steps': num_steps, 'lr': lr, 'output_path': output_path,
                                 'reuse_models': reuse_models, 'win_stock_ratio': float(win_stock_ratio), 'have_stock_ratio': float(have_stock_ratio)}

                # 강화학습 시작
                learner = None
                if rl_method != 'a3c':
                    common_params.update(
                        {'stock_code': stock_code, 'chart_data': chart_data, 'training_data': training_data,
                         'min_trading_unit': min_trading_unit, 'max_trading_unit': max_trading_unit})
                    if rl_method == 'dqn':
                        learner = DQNLearner(**{**common_params, 'value_network_path': value_network_path})
                    elif rl_method == 'pg':
                        learner = PolicyGradientLearner(**{**common_params, 'policy_network_path': policy_network_path})
                    elif rl_method == 'ac':
                        learner = ActorCriticLearner(**{**common_params, 'value_network_path': value_network_path,
                                                        'policy_network_path': policy_network_path})
                    elif rl_method == 'a2c':
                        learner = A2CLearner(**{**common_params, 'value_network_path': value_network_path,
                                                'policy_network_path': policy_network_path})
                    if learner is not None:
                        learner.run(balance=balance, num_epoches=num_epoches, discount_factor=discount_factor,
                                    start_epsilon=start_epsilon, learning=learning)
                        learner.save_models()
                else:
                    list_stock_code.append(stock_code)
                    list_chart_data.append(chart_data)
                    list_training_data.append(training_data)
                    list_min_trading_unit.append(min_trading_unit)
                    list_max_trading_unit.append(max_trading_unit)

            if rl_method == 'a3c':
                learner = A3CLearner(
                    **{**common_params, 'list_stock_code': list_stock_code, 'list_chart_data': list_chart_data,
                       'list_training_data': list_training_data,
                       'list_min_trading_unit': list_min_trading_unit,
                       'list_max_trading_unit': list_max_trading_unit,
                       'value_network_path': value_network_path, 'policy_network_path': policy_network_path})

                learner.run(balance=balance, num_epoches=num_epoches, discount_factor=discount_factor,
                            start_epsilon=start_epsilon, learning=learning)
                learner.save_models()

    else:
        # 출력 경로 설정
        output_path = os.path.join(settings.BASE_DIR, 'output/{}_{}_{}'.format(output_name, rl_method, net))
        if not os.path.isdir(output_path):
            os.makedirs(output_path)

        # 파라미터 기록
        with open(os.path.join(output_path, 'params.json'), 'w') as f:
            f.write(json.dumps(vars(args)))

        # 로그 기록 설정
        file_handler = logging.FileHandler(filename=os.path.join(output_path, "{}.log".format(output_name)),
                                           encoding='utf-8')
        stream_handler = logging.StreamHandler(sys.stdout)
        file_handler.setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.INFO)
        logging.basicConfig(format="%(message)s", handlers=[file_handler, stream_handler], level=logging.DEBUG)

        # 로그, Keras Backend 설정을 먼저하고 RLTrader 모듈들을 이후에 임포트해야 함
        from policy_learner import ReinforcementLearner, DQNLearner, PolicyGradientLearner, ActorCriticLearner, A2CLearner, \
            A3CLearner

        # 모델 경로 준비
        value_network_path = ''
        policy_network_path = ''
        if value_network_name is not None:
            value_network_path = os.path.join(settings.BASE_DIR, 'models/{}.h5'.format(value_network_name))
        else:
            value_network_path = os.path.join(output_path, '{}_{}_value_{}.h5'.format(rl_method, net, output_name))
        if policy_network_name is not None:
            policy_network_path = os.path.join(settings.BASE_DIR, 'models/{}.h5'.format(policy_network_name))
        else:
            policy_network_path = os.path.join(output_path, '{}_{}_policy_{}.h5'.format(rl_method, net, output_name))

        common_params = {}
        list_stock_code = []
        list_chart_data = []
        list_training_data = []
        list_min_trading_unit = []
        list_max_trading_unit = []

        for stock_code in stock_code_param:
            # 차트 데이터, 학습 데이터 준비
            chart_data, training_data = data_manager.load_data(stock_code, start_date, end_date, ver=ver)

            # 최소/최대 투자 단위 설정
            min_trading_unit = max(int(100000 / chart_data.iloc[-1]['close']), 1)
            max_trading_unit = max(int(1000000 / chart_data.iloc[-1]['close']), 1)

            # 공통 파라미터 설정
            common_params = {'rl_method': rl_method, 'delayed_reward_threshold': delayed_reward_threshold,
                             'net': net, 'num_steps': num_steps, 'lr': lr, 'output_path': output_path,
                             'reuse_models': reuse_models}

            # 강화학습 시작
            learner = None
            if rl_method != 'a3c':
                common_params.update({'stock_code': stock_code, 'chart_data': chart_data, 'training_data': training_data,
                                      'min_trading_unit': min_trading_unit, 'max_trading_unit': max_trading_unit})
                if rl_method == 'dqn':
                    learner = DQNLearner(**{**common_params, 'value_network_path': value_network_path})
                elif rl_method == 'pg':
                    learner = PolicyGradientLearner(**{**common_params, 'policy_network_path': policy_network_path})
                elif rl_method == 'ac':
                    learner = ActorCriticLearner(**{**common_params, 'value_network_path': value_network_path,
                                                    'policy_network_path': policy_network_path})
                elif rl_method == 'a2c':
                    learner = A2CLearner(**{**common_params, 'value_network_path': value_network_path,
                                            'policy_network_path': policy_network_path})
                elif rl_method == 'monkey':
                    net = rl_method
                    num_epoches = 1
                    discount_factor = None
                    start_epsilon = 1
                    learning = False
                    learner = ReinforcementLearner(**common_params)
                if learner is not None:
                    learner.run(balance=balance, num_epoches=num_epoches, discount_factor=discount_factor,
                                start_epsilon=start_epsilon, learning=learning)
                    learner.save_models()
            else:
                list_stock_code.append(stock_code)
                list_chart_data.append(chart_data)
                list_training_data.append(training_data)
                list_min_trading_unit.append(min_trading_unit)
                list_max_trading_unit.append(max_trading_unit)

        if rl_method == 'a3c':
            learner = A3CLearner(**{**common_params, 'list_stock_code': list_stock_code, 'list_chart_data': list_chart_data,
                                    'list_training_data': list_training_data,
                                    'list_min_trading_unit': list_min_trading_unit,
                                    'list_max_trading_unit': list_max_trading_unit,
                                    'value_network_path': value_network_path, 'policy_network_path': policy_network_path})

            learner.run(balance=balance, num_epoches=num_epoches, discount_factor=discount_factor,
                        start_epsilon=start_epsilon, learning=learning)
            learner.save_models()