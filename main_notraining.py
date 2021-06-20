import logging
import os

import settings
import data_manager
from policy_learner import PolicyLearner

if __name__ == '__main__':
    stock_code = '005930'  # 삼성전자
    model_ver = '20210526202014'

    # 로그 기록
    log_dir = os.path.join(settings.BASE_DIR, 'logs/%s' % stock_code)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    timestr = settings.get_time_str()
    file_handler = logging.FileHandler(filename=os.path.join(log_dir, "%s_%s.log" % (stock_code, timestr)), encoding='utf-8')
    stream_handler = logging.StreamHandler()
    file_handler.setLevel(logging.DEBUG)
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(format="%(message)s", handlers=[file_handler, stream_handler], level=logging.DEBUG)

    # 전처리된 데이터 저장
    prechartdir = os.path.join(settings.BASE_DIR, 'preprocessed_chart_data/%s' % stock_code)
    if not os.path.isdir(prechartdir):
        os.makedirs(prechartdir)
    prechart_path = os.path.join(prechartdir, 'preprocessed_{}.csv'.format(stock_code))

    # 주식 데이터 준비
    chart_data = data_manager.load_chart_data(os.path.join(settings.BASE_DIR, 'chart_data/{}.csv'.format(stock_code)))
    prep_data = data_manager.preprocess(chart_data)
    training_data = data_manager.build_training_data(prep_data,prechart_path)

    # 기간 필터링
    training_data = training_data[(training_data['date'] >= '2017-01-01') & (training_data['date'] <= '2017-12-31')]
    training_data = training_data.dropna()

    # 차트 데이터 분리
    feature_chart_data = ['date', 'open', 'high', 'low', 'close', 'volume']
    chart_data = training_data[feature_chart_data]

    # 학습 데이터 분리
    feature_chart_data = ['open_lastclose_ratio', 'high_close_ratio', 'low_close_ratio', 'close_lastclose_ratio', 'volume_lastvolume_ratio',
                          'close_ma5_ratio', 'volume_ma5_ratio', 'close_ma10_ratio', 'volume_ma10_ratio', 'close_ma20_ratio',
                          'volume_ma20_ratio', 'close_ma60_ratio', 'volume_ma60_ratio', 'close_ma120_ratio', 'volume_ma120_ratio']
    training_data = training_data[feature_chart_data]

    '''
    # 강화학습 시작
    policy_learner = PolicyLearner(stock_code=stock_code, chart_data=chart_data, training_data=training_data, min_trading_unit=1, max_trading_unit=1, delayed_reward_threshold=.05, lr=.0001)
    policy_learner.fit(balance=10000000, num_epoches=1000, discount_factor=0, start_epsilon=.5)

    # 정책 신경망을 파일로 저장
    model_dir = os.path.join(settings.BASE_DIR, 'models/%s' % stock_code)
    if not os.path.isdir(model_dir):
        os.makedirs(model_dir)
    model_path = os.path.join(model_dir, 'model_%s.h5' % timestr)
    policy_learner.policy_network.save_model(model_path)
    '''
    # 비학습 투자 시뮬레이션 시작
    policy_learner = PolicyLearner(stock_code=stock_code, chart_data=chart_data, training_data=training_data, min_trading_unit=1, max_trading_unit=3)
    policy_learner.trade(balance=10000000,model_path=os.path.join(settings.BASE_DIR, 'models/{}/model_{}.h5'.format(stock_code, model_ver)))