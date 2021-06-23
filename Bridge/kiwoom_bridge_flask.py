import sys
import os

import matplotlib.pyplot as plt
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from flask import Flask,request,Response
from koapy import KiwoomOpenApiPlusEntrypoint
from pandas import Timestamp
from config.kiwoomType import RealType
from multiprocessing import Process
from exchange_calendars import get_calendar
import json
from functools import wraps
import mpld3

# 로깅 설정
from datetime import datetime
import logging

if not os.path.exists('log'):
    os.mkdir('log')

fh = logging.FileHandler(filename=os.path.join('log', '{:%Y-%m-%d}.log'.format(datetime.now())),
                         encoding="utf-8")
format = '[%(asctime)s] I %(filename)s | %(name)s-%(funcName)s-%(lineno)04d I %(levelname)-8s > %(message)s'
fh.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
logging.basicConfig(format=format, handlers=[fh, sh], level=logging.DEBUG)

app = Flask(__name__)
server = Process()
# 1. 엔트리포인트 객체 생성
entrypoint = KiwoomOpenApiPlusEntrypoint()

# 2. 로그인
logging.info('Logging in...')
entrypoint.EnsureConnected()
logging.info('Logged in.')

# 3. kospi/kosdaq 종목리스트 저장
# 종목 리스트 확인 (기본 함수 호출 예시)
logging.info('Getting stock codes and names...')
codes = entrypoint.GetCodeListByMarketAsList('0')
names = [entrypoint.GetMasterCodeName(code) for code in codes]
codes_by_names_dict_kospi = dict(zip(names, codes))
names_by_codes_dict_kospi = dict(zip(codes, names))
codes = entrypoint.GetCodeListByMarketAsList('10')
names = [entrypoint.GetMasterCodeName(code) for code in codes]
codes_by_names_dict_kosdaq = dict(zip(names, codes))
names_by_codes_dict_kosdaq = dict(zip(codes, names))

# 6.주문처리
krx_calendar = get_calendar('XKRX')

def as_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        res = f(*args, **kwargs)
        res = json.dumps(res, ensure_ascii=False, indent=4).encode('utf8')
        return Response(res, content_type='application/json; charset=utf-8')
    return decorated_function

@app.route('/')
def home():
    # 접속 상태 확인 (기본 함수 호출 예시)
    logging.info('Checking connection status...')
    status = entrypoint.GetConnectState()
    logging.info('Connection status: %s', status)
    return 'Kiwoom Bridge Made By Dotz'

@app.route('/disconnect', methods=['GET'])
def disconnect():
    # 리소스 해제
    entrypoint.close()
    shutdown_server()
    logging.info('Server shutting down...')

@app.route('/stock_list/<kind>')
@as_json
def get_stock_list(kind):
    if kind == 'kospi':
        return names_by_codes_dict_kospi
    elif kind == 'kosdaq':
        return names_by_codes_dict_kosdaq

@app.route('/basic_info/<code>')
@as_json
def get_basic_info(code):
    logging.info('Getting basic info of Samsung...')
    info = entrypoint.GetStockBasicInfoAsDict(code)
    logging.info('Got basic info data (using GetStockBasicInfoAsDict):')
    return info

@app.route('/daily_stock_data/<code>')
def get_daily_stock_data(code):
    parameter = request.args.to_dict()
    if len(parameter) > 0 and 'adj' in parameter.keys():
        adj_bool = (parameter['adj'] == 'true')
        result = entrypoint.GetDailyStockDataAsDataFrame(code, adjusted_price=adj_bool)
    else:
        result = entrypoint.GetDailyStockDataAsDataFrame(code)
    html = "<h1 align=\"center\">"+get_name_by_code(code)+"</h1></br></br>"
    #date, open, high, low, close, volume
    result = result[['일자', '시가', '고가', '저가', '현재가', '거래량']].dropna()
    dates = pd.to_datetime(result['일자'], format='%Y%m%d')
    closes = pd.to_numeric(result['현재가'])
    f = plt.figure()
    plt.plot(dates, closes)
    html += mpld3.fig_to_html(f, figid='Stock_Chart')
    html += '</br></br>'
    html += result.to_html()
    return html

@app.route('/order/<code>/<count>/<action>')
def order(code, count, action):
    '''
    :param sRQName: 사용자 구분명, 구분가능한 임의의 문자열
    :param sScreenNo: 스크린번호
    :param sAccNo: 계좌번호 10자리
    :param nOrderType: 주문유형 1:신규매수, 2:신규매도 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정
    :param sCode: 종목코드 (6자리)
    :param nQty: 매매수량
    :param nPrice: 매매가격 시장가:0
    :param sHogaGb: 거래구분(혹은 호가구분) 03:시장가
    :param sOrgOrderNo: 원주문번호. 신규주문에는 공백 입력, 정정/취소시 입력
    :return:
    '''
    # 주문처리 파라미터 설정
    sRQName = code + ' 주식 '+action
    sScreenNo = '1000'  # 화면번호, 0000 을 제외한 4자리 숫자 임의로 지정
    sAccNo = entrypoint.GetAccountList()[0]  # 계좌번호 10자리, GetFirstAvailableAccount() : 계좌번호 목록에서 첫번째로 발견한 계좌번호
    nOrderType = 1 if action == 'buy' else 2
    sCode = code
    nQty = count
    nPrice = 0
    sHogaGb = '03'
    sOrgOrderNo = ''

    # 현재는 기본적으로 주문수량이 모두 소진되기 전까지 이벤트를 듣도록 되어있음 (단순 호출 예시)
    if is_currently_in_session():
        logging.info('Sending order to buy %s, quantity of %s stock, at market price...', code, count)
        for event in entrypoint.OrderCall(sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice,
                                          sHogaGb, sOrgOrderNo):
            logging.info(event)
        return "종목 %s %s개 %s주문" % (code, count, action)
    else:
        logging.info('Cannot send an order while market is not open, skipping...')
        return 'Cannot send an order while market is not open, skipping...'

def is_currently_in_session():
    now = Timestamp.now(tz=krx_calendar.tz)
    previous_open = krx_calendar.previous_open(now).astimezone(krx_calendar.tz)
    next_close = krx_calendar.next_close(previous_open).astimezone(krx_calendar.tz)
    return previous_open <= now <= next_close

def get_code_by_name(name):
    if name in codes_by_names_dict_kospi.keys():
        return codes_by_names_dict_kospi[name]
    elif name in codes_by_names_dict_kosdaq.keys():
        return codes_by_names_dict_kosdaq[name]

def get_name_by_code(code):
    if code in names_by_codes_dict_kospi.keys():
        return names_by_codes_dict_kospi[code]
    elif code in names_by_codes_dict_kosdaq.keys():
        return names_by_codes_dict_kosdaq[code]

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

if __name__ == '__main__':
    server = Process(target=app.run(debug=True))
    server.start()

