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

# Custom
from datetime import datetime
import logging

# Telegram
import telepot

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
print('Logging in...')
entrypoint.EnsureConnected()
logging.info('Logged in.')
base_account = entrypoint.GetAccountList()[0]

# 3. kospi/kosdaq 종목리스트 저장
# 종목 리스트 확인 (기본 함수 호출 예시)
print('Getting stock codes and names...')
codes = entrypoint.GetKospiCodeList()
names = [entrypoint.GetMasterCodeName(code) for code in codes]
codes_by_names_dict_kospi = dict(zip(names, codes))
names_by_codes_dict_kospi = dict(zip(codes, names))
codes = entrypoint.GetKosdaqCodeList()
names = [entrypoint.GetMasterCodeName(code) for code in codes]
codes_by_names_dict_kosdaq = dict(zip(names, codes))
names_by_codes_dict_kosdaq = dict(zip(codes, names))
logging.info('End stock codes and names...')


# 6.주문처리
krx_calendar = get_calendar('XKRX')

# 7.telegram 등록
def getToken():
    f = open("telebot.txt")
    token = f.readline().strip()
    userid = f.readline().strip()
    f.close()
    return (token , userid)
(token, chat_id) = getToken()
bot = telepot.Bot(token)

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
    print('Checking connection status...')
    status = entrypoint.GetConnectState()
    print('Connection status: %s', status)
    return 'Kiwoom Bridge Made By Dotz'

@app.route('/disconnect', methods=['GET'])
def disconnect():
    # 리소스 해제
    entrypoint.close()
    shutdown_server()
    print('Server shutting down...')

@app.route('/myaccount', methods=['GET'])
def myaccount():
    sAccNo = base_account
    account = stock_db.load_account_table().to_html()
    tname = 'account_detail_{}'.format(sAccNo)
    account_detail = stock_db.load_account_detail_table(tname)
    result = account + '</br></br>'
    result += account_detail.to_html()
    
    return result

@app.route('/stock_list/<kind>')
@as_json
def get_stock_list(kind):
    if kind == 'kospi':
        return names_by_codes_dict_kospi
    elif kind == 'kosdaq':
        return names_by_codes_dict_kosdaq

@app.route('/basic_info/<code>')
@as_json
def get_basic_info(code): # 업데이트 예정
    print('Getting basic info of %s', code)
    info = entrypoint.GetStockBasicInfoAsDict(code)
    print('Got basic info data (using GetStockBasicInfoAsDict):')
    return info

@app.route('/index_stock_data/<name>')
def get_index_stock_data(name):
    # date, open, high, low, close, volume
    tname = stock_db.getTableName(name)
    result = stock_db.load(tname)

    if result is None:
        return ('', 204)

    html = "<div style=\"position: relative;\"><h1 align=\"center\">"+name+"지수 차트</h1>"
    result = result.astype({'date': 'str', 'open': 'int', 'high': 'int', 'low': 'int', 'close': 'int', 'volume': 'int'})
    result['open'] = result['open'].apply(lambda _: _ / 100 if _ > 0 else _)
    result['high'] = result['high'].apply(lambda _: _ / 100 if _ > 0 else _)
    result['low'] = result['low'].apply(lambda _: _ / 100 if _ > 0 else _)
    result['close'] = result['close'].apply(lambda _: _ / 100 if _ > 0 else _)

    dates = pd.to_datetime(result['date'], format='%Y%m%d')
    closes = pd.to_numeric(result['close'])
    f = plt.figure()
    plt.plot(dates, closes)
    html += mpld3.fig_to_html(f, figid='Index_Chart')
    html += '</br></br>'
    html += result.to_html()
    return html

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
        result = stock_db.load_detail(tname, startdate)
    else:
        result = stock_db.load_detail(tname)

    if result is None:
        return ('', 204)

    dates = pd.to_datetime(result['date'], format='%Y%m%d')
    closes = pd.to_numeric(result['close'])
    f = plt.figure()
    plt.plot(dates, closes)
    html += mpld3.fig_to_html(f, figid='Stock_Chart')
    html += '</br></br>'
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
    :param sHogaGb: 거래구분(혹은 호가구분) '지정가': '00', '시장가': '03', '조건부지정가': '05', '최유리지정가': '06', '최우선지정가': '07',
            '지정가IOC': '10', '시장가IOC': '13', '최유리IOC': '16', '지정가FOK': '20', '시장가FOK': '23', '최유리FOK': '26',
            '장전시간외종가': '61', '시간외단일가매매': '62', '장후시간외종가': '81'
    :param sOrgOrderNo: 원주문번호. 신규주문에는 공백 입력, 정정/취소시 입력
    :return:
    [정규장 외 주문]
    장전 동시호가 주문
    08:30 ~ 09:00.	거래구분 00:지정가/03:시장가 (일반주문처럼)
    ※ 08:20 ~ 08:30 시간의 주문은 키움에서 대기하여 08:30 에 순서대로 거래소로 전송합니다.
    장전시간외 종가
    08:30 ~ 08:40. 	거래구분 61:장전시간외종가.  가격 0입력
    ※ 전일 종가로 거래. 미체결시 자동취소되지 않음
    장마감 동시호가 주문
    15:20 ~ 15:30.	거래구분 00:지정가/03:시장가 (일반주문처럼)
    장후 시간외 종가
    15:40 ~ 16:00.	거래구분 81:장후시간외종가.  가격 0입력
    ※ 당일 종가로 거래
    시간외 단일가
    16:00 ~ 18:00.	거래구분 62:시간외단일가.  가격 입력
    ※ 10분 단위로 체결, 당일 종가대비 +-10% 가격으로 거래
    '''
    # 주문처리 파라미터 설정
    sRQName = code + ' 주식 '+action
    sScreenNo = '1000'  # 화면번호, 0000 을 제외한 4자리 숫자 임의로 지정
    sAccNo = entrypoint.GetAccountList()[0]  # 계좌번호 10자리, GetFirstAvailableAccount() : 계좌번호 목록에서 첫번째로 발견한 계좌번호
    nOrderType = 1 if action == 'buy' else 2 if action == 'sell' else 3
    sCode = code
    nQty = count
    nPrice = 0
    sHogaGb = '03'
    sOrgOrderNo = ''

    # 현재는 기본적으로 주문수량이 모두 소진되기 전까지 이벤트를 듣도록 되어있음 (단순 호출 예시)
    if is_currently_in_session():
        if action == 'hold':
            logging.info('Holding action')
            bot.sendMessage(chat_id=chat_id, text="%s %s" % (get_name_by_code(code), action))
            return "종목 %s %s" % (code, action)

        logging.info('Sending order to %s %s, quantity of %s stock, at market price...', action, code, count)
        for event in entrypoint.OrderCall(sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice,
                                          sHogaGb, sOrgOrderNo):
            print(event)

        bot.sendMessage(chat_id=chat_id, text="%s %s개 %s" % (get_name_by_code(code), count, action))
        update_account()
        update_trading_record(code, get_name_by_code(code), count, action)
        return "종목 %s %s개 %s주문" % (code, count, action)
    else:
        logging.info('Cannot send an order while market is not open, skipping...')
        return 'Cannot send an order while market is not open, skipping...'

@app.route('/update_database')
def update_database():
    print('Updating Database.......')
    stock_list = []
    index_dict = {"kospi": "001", "big": "002", "medium": "003", "small": "004", "kosdaq": "101", "kospi200": "201",
                      "kostar": "302", "krx100": "701"}
    with open('stock_list.txt', 'r', encoding='utf-8') as f:
        while True:
            line = f.readline()
            if not line: break
            code = line.split(';')[0]
            stock_list.append(code)
        f.close()

    # DB 한번에 업데이트
    #save_account_info() 각 종목 매매 후 업데이트로 변경
    save_index_stock_data('kospi')
    logging.info(stock_list)
    for code in stock_list:
        save_daily_stock_data(code)

    print('Finishing Update Database.......')
    return ('', 204)

@app.route('/update_account')
def update_account():
    print('Updating Account.......')
    save_account_info()
    print('Finishing Update Account.......')
    return ('', 204)

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

def save_account_info():
    print("Account is updating...")
    actname = 'account_info'
    if stock_db.checkTableName(actname) == False:
        if stock_db.create_account_table() == False:
            logging.debug('Account table create failed')

    df = pd.DataFrame(columns=['예수금', '출금가능금액', '총매입금액', '총평가금액', '총수익률(%)', '추정예탁자산'])

    sAccNo_list = entrypoint.GetAccountList()
    print('Getting DepositInfo Data')
    for sAccNo in sAccNo_list:
        deposit = entrypoint.GetDepositInfo(account_no=sAccNo)
        print('Got DepositInfo Data (using GetDepositInfo)')
        print('Getting Account Detail Data')

        tname = 'account_detail_{}'.format(sAccNo)
        if stock_db.checkTableName(tname) == True:
            stock_db.delete_account_detail_table(tname)
        else:
            if stock_db.create_account_detail_table(tname) == True:
                logging.debug('account_detail_{} table create failed'.format(sAccNo))

        (totalbalance, balancedetail) = entrypoint.GetAccountEvaluationBalanceAsSeriesAndDataFrame(account_no=sAccNo)
        totalbalance = totalbalance[['총매입금액', '총평가금액', '총수익률(%)', '추정예탁자산']]
        if len(balancedetail) == 0 :
            balancedetail = pd.DataFrame([["TEST","TEST",0,0,0.0,0.0,0]],columns=['종목번호', '종목명', '보유수량', '매매가능수량', '수익률(%)', '보유비중(%)', '매입금액'])
        else :
            balancedetail = balancedetail[
                ['종목번호', '종목명', '보유수량', '매매가능수량', '수익률(%)', '보유비중(%)', '매입금액']]
        record = pd.DataFrame([{'예수금': deposit['예수금'], '출금가능금액': deposit['출금가능금액'], '총매입금액': totalbalance['총매입금액'],
                                '총평가금액': totalbalance['총평가금액'], '총수익률(%)': totalbalance['총수익률(%)'], '추정예탁자산': totalbalance['추정예탁자산']}],
                              columns=['예수금', '출금가능금액', '총매입금액', '총평가금액', '총수익률(%)', '추정예탁자산'])
        df = df.append(record, ignore_index=True)
        print('Got Account Detail Data (using GetAccountEvaluationBalanceAsSeriesAndDataFrame)')
        balancedetail.columns = ['code', 'name', 'count', 'tradecount', 'winratio', 'havratio', 'totalbuyprice']
        balancedetail = balancedetail.astype({'code': 'str', 'name': 'str', 'count': 'int', 'tradecount': 'int', 'winratio': 'float', 'havratio': 'float', 'totalbuyprice': 'int'})
        balancedetail['code'] = balancedetail['code'].apply(lambda _: _[1:]) # 종목코드 A 제거
        stock_db.save_account_detail_table(tname, balancedetail)

    df['계좌번호'] = pd.Series(sAccNo_list)
    df.columns = ['balance', 'cash', 'totalbalance', 'pvbalance', 'totalwinratio', 'pvtotalbalance', 'accountno']
    # '계좌번호', '예수금', '출금가능금액', '총매입금액', '총평가금액', '총수익률(%)', '추정예탁자산'
    df = df[['accountno', 'balance', 'cash', 'totalbalance', 'pvbalance', 'totalwinratio', 'pvtotalbalance']]
    stock_db.save_account_table(df)

def save_index_stock_data(name, scrno=None):
    #업종코드 = 001:종합(KOSPI), 002:대형주, 003:중형주, 004:소형주 101:종합(KOSDAQ), 201:KOSPI200, 302:KOSTAR, 701: KRX100 나머지 ※ 업종코드 참고
    print('Checking TR info of opt20006')
    tr_info = KiwoomOpenApiPlusTrInfo.get_trinfo_by_code('opt20006')

    print('Inputs of opt20006:\n'+str(tr_info.inputs))
    print('Single outputs of opt20006:\n'+str(tr_info.single_outputs))
    print('Multi outputs of opt20006:\n'+str(tr_info.multi_outputs))

    rqname = "업종일봉조회요청"
    trcode = "opt20006"

    index_dict = {"kospi": "001", "big": "002", "medium": "003", "small": "004", "kosdaq": "101", "kospi200": "201",
            "kostar": "302", "krx100": "701"}

    if name in index_dict.keys():
        code = index_dict[name]
        print("Index Name : %s is updating..." % name)
        tname = stock_db.getTableName(name)
        if stock_db.checkTableName(tname) == False:
            if stock_db.create_table(tname) == False:
                logging.debug(code + ' table create failed')

        date = stock_db.load_first(tname)
        if len(date) == 0:
            date = None
        else:
            date = str(date['date'][0])

        # date = str(datetime.today().strftime('%Y%m%d')) 테스트용
        lastdate = getmaximumdate(date)
        print('lastdate = ' + lastdate)
        inputs = {'업종코드': code, '기준일자': ''}
        date_format = "%Y%m%d"
        date_column_name = "일자"

        if validate(lastdate):
            stop_condition = {"name": date_column_name, "value": lastdate, "include_equal": True}
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
                print("Received %d records from %s to %s for code %s", nrows, from_date, to_date, code,)
            
        df = pd.DataFrame.from_records(records, columns=columns)
        # date, open, high, low, close, volume
        df = df[['일자', '시가', '고가', '저가', '현재가', '거래량']].dropna()
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = df.astype({'date': 'str', 'open': 'int', 'high': 'int', 'low': 'int', 'close': 'int', 'volume': 'int'})
        del_idx = df[df['volume'] == 0].index
        df = df.drop(del_idx)
        stock_db.save(tname, df)

def save_daily_stock_data(code):
    print("Stock Code : %s Name : %s is updating..." % (code, get_name_by_code(code)))
    tname = stock_db.getTableName(code)
    if stock_db.checkTableName(tname) == False:
        if stock_db.create_table_detail(tname) == False:
            logging.debug(code+' table create failed')

    date = stock_db.load_first(tname)
    if len(date) == 0:
        date = None
    else:
        date = str(date['date'][0])

    #date = str(datetime.today().strftime('%Y%m%d')) 테스트용
    lastdate = getmaximumdate(date)
    print('lastdate = '+lastdate)
    result1 = entrypoint.GetDailyStockDataAsDataFrame(code, end_date=lastdate, include_end=True, adjusted_price=True)
    result2 = detail_stock_data(code, end_date=lastdate, include_end=True)

    #출력값 dataframe DB 변환할 수 있도록 수정
    result1 = result1[['일자', '시가', '고가', '저가', '현재가', '거래량']].dropna()
    result1.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    result1 = result1.astype({'date': 'str', 'open': 'int', 'high': 'int', 'low': 'int', 'close': 'int', 'volume': 'int'})

    result2 = result2[['날짜', '등락률', '외인비중', '외인순매수', '기관순매수', '개인순매수', '프로그램']].dropna()
    result2.columns = ['date', 'dayratio', 'frnratio', 'frnvolume', 'insvolume', 'manvolume', 'autovolume']

    result2['frnvolume'] = result2['frnvolume'].apply(lambda _: _[1:] if len(_) > 1 else _)
    result2['insvolume'] = result2['insvolume'].apply(lambda _: _[1:] if len(_) > 1 else _)
    result2['manvolume'] = result2['manvolume'].apply(lambda _: _[1:] if len(_) > 1 else _)
    result2['autovolume'] = result2['autovolume'].apply(lambda _: _[1:] if len(_) > 1 else _)
    result2 = result2.astype({'date': 'str', 'dayratio': 'float', 'frnratio': 'float', 'frnvolume': 'int', 'insvolume': 'int', 'manvolume': 'int', 'autovolume': 'int'})

    # 날짜 , 시가, 고가, 저가, 종가, 거래량, 등락률, 외인비중, 외인순매수, 기관순매수, 개인순매수, 프로그램순매수
    # date, open, high, low, close, volume, dayratio, frnratio, frnvolume, insvolume, manvolume, autovolume
    result = pd.merge(result1, result2, how='inner', on='date')
    del_idx = result[result['volume'] == 0].index
    result = result.drop(del_idx)

    stock_db.save_detail(tname, result)

def detail_stock_data(code,start_date=None, end_date=None, include_end=False, scrno=None):
    print('Checking TR info of opt10086')
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
            print("Received %d records from %s to %s for code %s", nrows, from_date, to_date, code,)

    df = pd.DataFrame.from_records(records, columns=columns)
    return df

def update_trading_record(code, name, count, action):
    print("Stock Code : %s Name : %s %s개 %s recorded" % (code, name, count, action))
    tname = 'trading_record'
    if stock_db.checkTableName(tname) == False:
        if stock_db.create_trading_record_table() == False:
            logging.debug(tname + ' table create failed')

    if action == 'sell':
        count = -int(count)
    stock_db.save_trading_record_table(datetime.today().strftime('%Y%m%d'), code, name, count)

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
    server = Process(target=app.run())
    server.start()

