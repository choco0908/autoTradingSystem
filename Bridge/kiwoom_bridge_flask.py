from flask import Flask
from koapy import KiwoomOpenApiPlusEntrypoint
from pandas import Timestamp
from exchange_calendars import get_calendar

# 로깅 설정
import os
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

# 1. 엔트리포인트 객체 생성
entrypoint = KiwoomOpenApiPlusEntrypoint()

# 2. 로그인
logging.info('Logging in...')
entrypoint.EnsureConnected()
logging.info('Logged in.')

# 6.주문처리
krx_calendar = get_calendar('XKRX')

@app.route('/')
def home():
    # 접속 상태 확인 (기본 함수 호출 예시)
    logging.info('Checking connection status...')
    status = entrypoint.GetConnectState()
    logging.info('Connection status: %s', status)
    return 'Kiwoom Bridge Made By Dotz'

@app.route('/stock_list')
def connect():
    # 종목 리스트 확인 (기본 함수 호출 예시)
    logging.info('Getting stock codes and names...')
    codes = entrypoint.GetCodeListByMarketAsList('0')
    kospi_names = [entrypoint.GetMasterCodeName(code) for code in codes]
    codes = entrypoint.GetCodeListByMarketAsList('10')
    kosaq_names = [entrypoint.GetMasterCodeName(code) for code in codes]
    return '종목 출력\n'+str(kospi_names+kosaq_names)

@app.route('/order/<code>/<count>/<action>')
def order(code, count, action):
    # 주문처리 파라미터 설정
    first_account_no = entrypoint.GetFirstAvailableAccount()
    request_name = code + ' 주식 '+action  # 사용자 구분명, 구분가능한 임의의 문자열
    screen_no = '1000'  # 화면번호, 0000 을 제외한 4자리 숫자 임의로 지정
    account_no = first_account_no  # 계좌번호 10자리, 여기서는 계좌번호 목록에서 첫번째로 발견한 계좌번호로 매수처리
    order_type = 1  # 주문유형, 1 : 신규매수
    code = code  # 종목코드, 앞의 삼성전자 종목코드
    quantity = count  # 주문수량, 1주 매수
    price = 0  # 주문가격, 시장가 매수는 가격설정 의미없음
    quote_type = '03'  # 거래구분, 03 : 시장가
    original_order_no = ''  # 원주문번호, 주문 정정/취소 등에서 사용

    # 현재는 기본적으로 주문수량이 모두 소진되기 전까지 이벤트를 듣도록 되어있음 (단순 호출 예시)
    if is_currently_in_session():
        logging.info('Sending order to buy %s, quantity of %s stock, at market price...', code, count)
        for event in entrypoint.OrderCall(request_name, screen_no, account_no, order_type, code, quantity, price,
                                          quote_type, original_order_no):
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

if __name__ == '__main__':
    app.run(debug=True)

