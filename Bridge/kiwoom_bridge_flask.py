# flask 서버
import sys
import os

import dateutil.relativedelta
from flask import Flask,request,Response
from multiprocessing import Process
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import json
from functools import wraps
import mpld3

# koapy
from koapy import KiwoomOpenApiPlusEntrypoint, KiwoomOpenApiPlusTrInfo
from pandas import Timestamp
import matplotlib.pyplot as plt
import pandas as pd
from exchange_calendars import get_calendar

# DB
from DataBase.SqliteDB import StockDB
from DataBase.StockDataTaLib import StockData

# Custom
from config.kiwoomType import RealType
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

########### init ###########
app = Flask(__name__)
server = Process()
stock_db = StockDB()

# 1. 엔트리포인트 객체 생성
entrypoint = KiwoomOpenApiPlusEntrypoint()

# 2. 로그인
logging.info('Logging in...')
entrypoint.EnsureConnected()
logging.info('Logged in.')

# 3. kospi/kosdaq 종목리스트 저장
# 종목 리스트 확인 (기본 함수 호출 예시)
logging.info('Getting stock codes and names...')
codes = entrypoint.GetKospiCodeList()
names = [entrypoint.GetMasterCodeName(code) for code in codes]
codes_by_names_dict_kospi = dict(zip(names, codes))
names_by_codes_dict_kospi = dict(zip(codes, names))
codes = entrypoint.GetKosdaqCodeList()
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
    startdate = ''
    if len(parameter) > 0 and 'startdate' in parameter.keys():
        startdate = parameter['startdate']

    html = "<div style=\"position: relative;\"><h1 align=\"center\">"+get_name_by_code(code)+" 종목차트</h1>"

    #date, open, high, low, close, volume
    tname = stock_db.getTableName(code)
    if validate(startdate):
        result = stock_db.load(tname, startdate)
    else:
        result = stock_db.load(tname)

    if result is None:
        return ('', 204)

    #df = result.iloc[::-1]
    #sd = StockData(code, df).calcIndicators()
    #sd = sd.iloc[::-1]

    dates = pd.to_datetime(result['date'], format='%Y%m%d')
    closes = pd.to_numeric(result['close'])
    f = plt.figure()
    plt.plot(dates, closes)
    html += mpld3.fig_to_html(f, figid='Stock_Chart')
    html += '</br></br>'
    #html += sd.to_html()
    html += result.to_html()
    return html

@app.route('/daily_detail_stock_data/<code>')
def get_daily_detail_stock_data(code):
    parameter = request.args.to_dict()
    startdate = ''
    if len(parameter) > 0 and 'startdate' in parameter.keys():
        startdate = parameter['startdate']

    html = "<div style=\"position: relative;\"><h1 align=\"center\">"+get_name_by_code(code)+" 종목 일봉 상세차트</h1>"

    # date, open, high, low, close, volume
    tname = stock_db.getTableName(code)
    if validate(startdate):
        result = stock_db.load_detail(tname, startdate)
    else:
        result = stock_db.load_detail(tname)

    if result is None:
        return ('', 204)

    html += result.to_html()
    return html

@app.route('/save_daily_stock_data/<code>')
def save_daily_stock_data(code):
    logging.debug("Stock Code : %s Name : %s is updating..." % (code, get_name_by_code(code)))
    tname = stock_db.getTableName(code)
    if stock_db.checkTableName(tname) == False:
        if stock_db.createTable(tname) == False:
            logging.debug(code+' table create failed')

    date = stock_db.load_first(tname)
    if len(date) == 0:
        date = None
    else:
        date = date['date'][0]
    lastdate = getmaximumdate(date)
    print('lastdate = '+lastdate)
    result1 = entrypoint.GetDailyStockDataAsDataFrame(code, end_date=lastdate, include_end=True, adjusted_price=True)
    result2 = detail_stock_data(code, end_date=lastdate, include_end=True)

    #출력값 dataframe DB 변환할 수 있도록 수정
    result1 = result1[['일자', '시가', '고가', '저가', '현재가', '거래량']].dropna()
    result1.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    result1 = result1.astype({'date': 'str', 'open': 'int', 'high': 'int', 'low': 'int', 'close': 'int', 'volume': 'int'})

    result2 = result2[['날짜', '등락률', '외인비중', '외인순매수', '기관순매수', '개인순매수']].dropna()
    result2.columns = ['date', 'dayratio', 'frnratio', 'frnvolume', 'insvolume', 'manvolume']

    result2['frnvolume'] = result2['frnvolume'].apply(lambda _: _[1:])
    result2['insvolume'] = result2['insvolume'].apply(lambda _: _[1:])
    result2['manvolume'] = result2['manvolume'].apply(lambda _: _[1:])
    result2 = result2.astype({'date': 'str', 'dayratio': 'float', 'frnratio': 'float', 'frnvolume': 'int', 'insvolume': 'int', 'manvolume': 'int'})

    # 날짜 , 시가, 고가, 저가, 종가, 거래량, 등락률, 외인비중, 외인순매수, 기관순매수, 개인순매수
    # date, open, high, low, close, volume, dayratio, frnratio, frnvolume, insvolume, manvolume
    result = pd.merge(result1, result2, how='inner', on='date')
    del_idx = result[result['volume'] == 0].index
    result = result.drop(del_idx)

    stock_db.save(tname, result)
    return ('', 204)

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

def detail_stock_data(code,start_date=None, end_date=None, include_end=False, scrno=None):
    logging.info('Checking TR info of opt10086')
    tr_info = KiwoomOpenApiPlusTrInfo.get_trinfo_by_code('opt10086')

    print('Inputs of opt10086:\n'+str(tr_info.inputs))
    print('Single outputs of opt10086:\n'+str(tr_info.single_outputs))
    print('Multi outputs of opt10086:\n'+str(tr_info.multi_outputs))

    rqname = "일별주가요청"
    trcode = "opt10086"
    inputs = {'종목코드': code, '조회일자': '', '표시구분': '0'}

    date_format = "%Y%m%d"
    date_column_name = "날짜"

    if validate(start_date):
        if start_date is not None:
            inputs.update({'조회일자': start_date})

    if validate(end_date):
        stop_condition = {"name": date_column_name, "value": end_date, "include_equal": True,}
        if include_end:
            stop_condition["include_equal"] = True
    else:
        stop_condition = None

    columns = []
    records = []
    for response in entrypoint.TransactionCall(rqname, trcode, scrno, inputs, stop_condition=stop_condition):
        if not columns:
            columns = list(response.multi_data.names)
            if date_column_name in columns:
                date_column_index = columns.index(date_column_name)
        for values in response.multi_data.values:
            records.append(values.values)

        nrows = len(response.multi_data.values)
        if nrows > 0:
            from_date = response.multi_data.values[0].values[date_column_index]
            to_date = response.multi_data.values[-1].values[date_column_index]
            from_date = datetime.strptime(from_date, date_format)
            to_date = datetime.strptime(to_date, date_format)
            logging.info("Received %d records from %s to %s for code %s", nrows, from_date, to_date, code,)

    df = pd.DataFrame.from_records(records, columns=columns)
    return df

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def validate(date_text):
    if date_text is None:
        return False
    try:
        if date_text != datetime.strptime(date_text, "%Y%m%d").strftime('%Y%m%d'):
            raise ValueError
        return True
    except ValueError:
        return False

def getmaximumdate(date_text): # data 최대 10년치만 저장
    max_date = datetime.today() + dateutil.relativedelta.relativedelta(days=-3650)
    max_date = max_date.strftime('%Y%m%d')
    if validate(date_text):
        date_text = datetime.strptime(date_text, "%Y%m%d").strftime('%Y%m%d')
        if date_text > max_date:
            return date_text
        else:
            return max_date
    else:
        return max_date

if __name__ == '__main__':
    server = Process(target=app.run(debug=True))
    server.start()

