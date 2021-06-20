import pandas as pd

from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *

from config.errorCode import *
from config.kiwoomType import *

from DataBase.SqliteDB import StockDB
from DataBase.StockDataTaLib import StockData

from datetime import date, timedelta
from enum import Enum
import os

class ScreenNumber(Enum):
    ACCOUNT = 0         # 1000:계좌현황
    CHART_DATA = 1      # 2000:차트데이터
    STOCK_SCRNO = 2     # 3000:종목별 스크린번호
    ACTION_SCRNO = 3    # 4000:매매용 스크린번호
    REAL = 4            # 5000:실시간 조회


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self.today = date.today()
        print("[+] Kiwoom init called at %s" % self.today)

        #init values
        self.account_num = ''
        self.passwd = ''
        self.pwtype = ''
        self.use_money = 0
        self.user_money_ratio = 0.5
        self.account_stocks_detail = {} # 계좌 잔고 현황
        self.non_trading_stocks_detail = {} # 미체결 데이터
        self.portfolio_stocks_detail = {} # 처리해야할 종목 데이터
        self.buy_sell_stocks_detail = {} # 사야할 종목 데이터
        self.daily_stock_data = {} # 일봉 데이터
        self.limits = {}  # 일봉 저장 데이터 갯수 제한
        self.yesterday = (self.today - timedelta(1)).strftime("%Y%m%d")
        self.realType = RealType()
        self.stock_db = StockDB()

        ##### eventloop 모음
        self.login_event_loop = None
        self.detail_account_event_loop = QEventLoop()
        self.get_stock_data_event_loop = QEventLoop()
        self.real_data_event_loop = QEventLoop()
        ###################

        ##### 스크린 번호
        self.e = ScreenNumber
        # 1000:계좌현황 2000:차트데이터 3000:종목별 스크린번호 4000:매매용 스크린번호 5000:실시간 조회
        self.screen_info = ["1000", "2000", "3000", "4000", "5000"]

        # 계좌 정보
        if not os.path.exists('credentials.txt'):
            print('credentials is not exists')
            return
        else:
            with open('credentials.txt', 'r') as f:
                self.passwd = f.readline()
                self.pwtype = f.readline()
                f.close()

        # Buy / Sell 종목
        if not os.path.exists('DataBase/DB/buy_sell_action.txt'):
            print('buy_sell_action.txt is not exists')
            return
        else:
            with open('DataBase/DB/buy_sell_action.txt', 'r', encoding='UTF-8') as f:
                while True:
                    stock = f.readline().strip()
                    if not stock: break
                    stock = tuple(stock.split(';'))
                    self.buy_sell_stocks_detail.update({stock[0]: {"종목명": stock[1], "액션": stock[2], "수량": stock[3]}})
                f.close()

        self.get_ocx_instance()
        self.event_slots()
        self.real_event_slots()
        self.signal_login_commConnect()

        # 계좌번호 조회
        self.get_acoount()
        # 예수금 조회
        self.detail_account()
        # 계좌평가잔고내역 조회
        self.detail_account_stocks()
        # 미체결 요청
        self.non_trading_stocks()
        # 종목별 스크린번호 부여
        self.set_screen_number()
        # 종목 분석
        # self.analysis_stock()
        # 장운영시간 확인
        self.get_stock_market_status()

        # 실시간 주식 거래시 등록
        '''
        for code in self.portfolio_stocks_detail.keys():
            screen_no = self.portfolio_stocks_detail[code]['스크린번호']
            fid = self.realType.REALTYPE['주식체결']['체결시간']
            self.setRealReg(screen_no, code, fid, "1")
        '''

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.tr_slot)

    def login_slot(self, errorCode):
        print(errors(errorCode))
        self.login_event_loop.exit()

    def real_event_slots(self):
        self.OnReceiveRealData.connect(self.realdata_slot)

    def signal_login_commConnect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def get_acoount(self):
        account_list = self.dynamicCall("GetLoginInfo(String)","ACCNO")
        self.account_num = account_list.split(';')[0]
        user_name = self.dynamicCall("GetLoginInfo(String)","USER_NAME")
        server_gubun = self.dynamicCall("GetLoginInfo(String)","GetServerGubun")
        print('%s is login , 계좌번호 %s \nserver %s connected' % (user_name,self.account_num,server_gubun))

    def detail_account(self):
        self.setInputValue("계좌번호", self.account_num)
        self.setInputValue("비밀번호", self.passwd)
        self.setInputValue("비밀번호입력매체구분", self.pwtype)
        self.setInputValue("조회구분", "2")
        self.commRqData("예수금상세현황","opw00001","0",self.screen_info[self.e.ACCOUNT.value])
        self.detail_account_event_loop.exec_()

    def detail_account_stocks(self, sPrevNext="0"):
        print('계좌평가잔고내역 확인')
        self.setInputValue("계좌번호", self.account_num)
        self.setInputValue("비밀번호", self.passwd)
        self.setInputValue("비밀번호입력매체구분", self.pwtype)
        self.setInputValue("조회구분", "2")
        self.commRqData("계좌평가잔고내역", "opw00018", sPrevNext , self.screen_info[self.e.ACCOUNT.value])
        self.detail_account_event_loop.exec_()

    def non_trading_stocks(self, sPrevNext="0"):
        self.setInputValue("계좌번호", self.account_num)
        self.setInputValue("체결구분", "1")
        self.setInputValue("매매구분", "0")
        self.commRqData("실시간미체결요청", "opt10075", sPrevNext, self.screen_info[self.e.ACCOUNT.value])
        self.detail_account_event_loop.exec_()

    def get_stock_market_status(self):
        self.setRealReg(self.screen_info[self.e.REAL.value], '', self.realType.REALTYPE['장시작시간']['장운영구분'], "0")

    def get_code_list_by_market(self, market_code):
        code_list = self.getCodeListByMarket(market_code)
        code_list = code_list.split(";")[:-1]
        return code_list

    def analysis_stock(self):
        code_list_kospi = self.get_code_list_by_market("0")
        code_list_kosdaq = self.get_code_list_by_market("10")
        list_kospi = []
        list_kosdaq = []

        if not os.path.exists('stock_list.txt'):
            print('stock_list.txt is not exists')
            return
        else:
            with open('stock_list.txt', 'r', encoding='UTF-8') as f:
                while True:
                    stock = f.readline().strip()
                    if not stock: break
                    stock = tuple(stock.split(';'))
                    if stock[0] in code_list_kospi:
                        list_kospi.append(stock)
                    elif stock[0] in code_list_kosdaq:
                        list_kosdaq.append(stock)
                f.close()
            if len(list_kospi) == 0 and len(list_kosdaq) == 0:
                print('stock_list.txt is empty')

        print("코스피 종목 %s개 / 코스닥 종목 %s개 분석 시작" % (len(list_kospi), len(list_kosdaq)))
        for idx, tp in enumerate(list_kospi):
            self.disconnectRealData(self.screen_info[self.e.CHART_DATA.value])
            code = tp[0]
            name = tp[1]
            print("%s / %s : KOSPI Stock Code : %s Name : %s is updating..." % (idx+1, len(list_kospi), code, name))
            tname = self.stock_db.getTableName(code)
            if self.stock_db.checkTableName(tname) == False:
                if self.stock_db.createTable(tname) == False:
                    continue

            if code not in self.limits.keys():
                self.limits.update({code : 0})
            self.get_kiwoom_stock_data(code, self.yesterday)
            df = pd.DataFrame.from_dict(self.daily_stock_data[code], orient='index')
            df = df.iloc[::-1]
            print(f"index: {df.index}")
            sd = StockData(code, df).calcIndicators()
            sd = sd.iloc[::-1]
            print(sd)
            self.stock_db.save(tname, df)

            if idx == 1: #DB에 잘 들어가는지 테스트용
                df = self.stock_db.load(tname)
                if df is None:
                    continue

        for idx, tp in enumerate(list_kosdaq):
            self.disconnectRealData(self.screen_info[self.e.CHART_DATA.value])
            code = tp[0]
            name = tp[1]
            print("%s / %s : KOSDAQ Stock Code : %s Name : %s is updating..." % (idx+1, len(list_kosdaq), code, name))
            tname = self.stock_db.getTableName(code)
            if self.stock_db.checkTableName(tname) == False:
                if self.stock_db.createTable(tname) == False:
                    continue

            self.get_kiwoom_stock_data(code, self.yesterday)
            df = pd.DataFrame.from_dict(self.daily_stock_data[code], orient='index')
            print(f"index: {df.index}")
            self.stock_db.save(tname, df)

    def get_kiwoom_stock_data(self, code=None, date=None, sPrevNext="0"):
        QTest.qWait(3600)
        self.setInputValue("종목코드", code)
        self.setInputValue("수정주가구분", "1")
        if date != None:
            self.setInputValue("기준일자",date)

        self.commRqData("주식일봉차트조회", "opt10081", sPrevNext, self.screen_info[self.e.CHART_DATA.value])
        self.get_stock_data_event_loop.exec_()

    def set_screen_number(self):
        code_list = []

        #계좌평가잔고내역 종목들
        for code in self.account_stocks_detail.keys():
            if code not in code_list:
                code_list.append(code)
        #미체결 종목
        for order_no in self.non_trading_stocks_detail.keys():
            code = self.non_trading_stocks_detail[order_no]['종목코드']
            if code not in code_list:
                code_list.append(code)
        #사야할 종목
        print(self.buy_sell_stocks_detail)
        for code in self.buy_sell_stocks_detail.keys():
            if code not in code_list:
                code_list.append(code)

        #스크린번호 할당
        cnt = 0
        for code in code_list:
            stock_screen = int(self.screen_info[self.e.STOCK_SCRNO.value])
            action_screen = int(self.screen_info[self.e.ACTION_SCRNO.value])

            if code not in self.portfolio_stocks_detail.keys():
                self.portfolio_stocks_detail.update({code:{}})
            self.portfolio_stocks_detail[code].update({"스크린번호": stock_screen})
            self.portfolio_stocks_detail[code].update({"주문용스크린번호": action_screen})

            cnt += 1
            if (cnt % 50) == 0:
                stock_screen += 1
                action_screen += 1
                self.screen_info[self.e.STOCK_SCRNO.value] = str(stock_screen)
                self.screen_info[self.e.ACTION_SCRNO.value] = str(action_screen)

    def tr_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        '''
        tr요청 받는 slot
        :param sScrNo: 스크린번호
        :param sRQName: 요청명
        :param sTrCode: tr코드
        :param sRecordName: 사용 X 
        :param sPrevNext: 다음 페이지 여부  없음(0 or "") 있음 (2)
        :return: 
        '''

        if sRQName == "예수금상세현황":
            self.retDetail_account(sTrCode, sRQName)
        elif sRQName == "계좌평가잔고내역":
            self.retDetail_account_stocks(sTrCode, sRQName, sPrevNext)
        elif sRQName == "실시간미체결요청":
            self.retNon_trading_stocks(sTrCode, sRQName)
        elif sRQName == "주식일봉차트조회":
            self.retGet_kiwoom_stock_data(sTrCode, sRQName, sPrevNext)

    def retDetail_account(self, sTrCode, sRQName):
        deposit = self.getCommData(sTrCode, sRQName, 0, "예수금")
        self.use_money = int(deposit) * self.user_money_ratio
        self.use_money = self.use_money / 4
        candeposit = self.getCommData(sTrCode, sRQName, 0, "출금가능금액")
        print("예수금 : %s 출금가능금액 : %s" % (int(deposit), int(candeposit)))
        self.detail_account_event_loop.exit()

    def retDetail_account_stocks(self, sTrCode, sRQName, sPrevNext):
        total_portfolio_stocks = self.getCommData(sTrCode, sRQName, 0, "총매입금액")
        win_portfolio_rate = self.getCommData(sTrCode, sRQName, 0, "총수익률(%)")
        print("총매입금액 : %s 총수익률 : %s%%" % (int(total_portfolio_stocks), float(win_portfolio_rate)))

        rows = self.getRepeatCnt(sTrCode, sRQName)
        cnt = 0

        if rows == 0:
            print("계좌에 조회할 종목이 없습니다.")

        for idx in range(rows):
            code = self.getCommData(sTrCode, sRQName, idx, "종목번호").strip()[1:]  # 영어 제외 종목코드만
            code_name = self.getCommData(sTrCode, sRQName, idx, "종목명").strip()
            stock_quantity = int(self.getCommData(sTrCode, sRQName, idx, "보유수량").strip())
            buy_price = int(self.getCommData(sTrCode, sRQName, idx, "매입가").strip())
            win_ratio = float(self.getCommData(sTrCode, sRQName, idx, "수익률(%)").strip())
            current_price = int(self.getCommData(sTrCode, sRQName, idx, "현재가").strip())
            total_buy_price = int(self.getCommData(sTrCode, sRQName, idx, "매입금액").strip())
            possible_quantity = int(self.getCommData(sTrCode, sRQName, idx, "매매가능수량").strip())

            if code in self.account_stocks_detail:
                pass
            else:
                self.account_stocks_detail.update({code: {}})
            account_stock_detail = self.account_stocks_detail[code]
            account_stock_detail.update({"종목명": code_name, "보유수량": stock_quantity, "매입가": buy_price, "수익률(%)": win_ratio, "현재가": current_price, "매입금액": total_buy_price, "매매가능수량": possible_quantity})
            print(account_stock_detail)
            cnt += 1

        if sPrevNext == "2":
            self.detail_account_stocks(sPrevNext="2")
        else:
            self.detail_account_event_loop.exit()

    def retNon_trading_stocks(self, sTrCode, sRQName):
        rows = self.getRepeatCnt(sTrCode, sRQName)
        cnt = 0

        if rows == 0:
            print("미체결된 종목이 없습니다.")

        for idx in range(rows):
            code = self.getCommData(sTrCode, sRQName, idx, "종목번호").strip()
            code_name = self.getCommData(sTrCode, sRQName, idx, "종목명").strip()
            order_no = int(self.getCommData(sTrCode, sRQName, idx, "주문번호").strip())
            order_status = int(self.getCommData(sTrCode, sRQName, idx, "주문상태").strip()) # 접수,확인,체결
            order_quantity = int(self.getCommData(sTrCode, sRQName, idx, "주문수량").strip())
            order_price = int(self.getCommData(sTrCode, sRQName, idx, "주문가격").strip())
            order_gubun = self.getCommData(sTrCode, sRQName, idx, "주문구분").strip().lstrip('+').lstrip('-') # -매도, +매수, -
            non_trading_quantity = int(self.getCommData(sTrCode, sRQName, idx, "미체결수량").strip())
            trading_quantity = int(self.getCommData(sTrCode, sRQName, idx, "체결량").strip())

            if order_no in self.non_trading_stocks_detail:
                pass
            else:
                self.non_trading_stocks_detail[order_no] = {}
            non_trading_stock_detail = self.non_trading_stocks_detail[order_no]
            non_trading_stock_detail.update({"종목코드": code, "종목명": code_name, "주문번호": order_no, "주문상태": order_status, "주문수량": order_quantity, "주문가격": order_price,
                                             "주문구분": order_gubun, "미체결수량": non_trading_quantity, "체결량": trading_quantity})
            print("미체결 종목 : %s" % non_trading_stock_detail)
        self.detail_account_event_loop.exit()

    def retGet_kiwoom_stock_data(self, sTrCode, sRQName, sPrevNext):
        code = self.getCommData(sTrCode, sRQName, 0, "종목코드")
        code = code.strip()
        cnt = self.getRepeatCnt(sTrCode, sRQName)
        limit = self.limits[code] + 1
        self.limits.update({code:limit})

        for idx in range(cnt):
            close_price = int(self.getCommData(sTrCode, sRQName, idx, "현재가").strip())
            value = int(self.getCommData(sTrCode, sRQName, idx, "거래량").strip())
            date = self.getCommData(sTrCode, sRQName, idx, "일자").strip()
            open_price = int(self.getCommData(sTrCode, sRQName, idx, "시가").strip())
            high_price = int(self.getCommData(sTrCode, sRQName, idx, "고가").strip())
            low_price = int(self.getCommData(sTrCode, sRQName, idx, "저가").strip())

            if code in self.daily_stock_data:
                pass
            else:
                self.daily_stock_data.update({code: {}})
            if date in self.daily_stock_data[code]:
                pass
            else:
                self.daily_stock_data[code].update({date: {}})
            data = self.daily_stock_data[code][date]
            data.update({"date": date, "open": open_price, "high": high_price, "low": low_price, "close": close_price, "volume": value})

        if sPrevNext == "2" and limit < 3:  # 1800개 이상 받지 않음
            self.get_kiwoom_stock_data(code=code, sPrevNext=sPrevNext)
        else:
            self.get_stock_data_event_loop.exit()

    def realdata_slot(self, sCode, sRealType, sRealData):
        if sRealType == "장시작시간":
            self.retGet_stock_market_status(sCode, sRealType)
        elif sRealType == "주식체결":
            self.retRealData_transferred(sCode, sRealType)

    def retGet_stock_market_status(self, sCode, sRealType):
        fid = self.realType.REALTYPE[sRealType]['장운영구분']
        value = self.getCommRealData(sCode, fid)

        if value == '0':
            print("장 시작 전")
        elif value == '2':
            print("장 종료, 동시호가 시간")
        elif value == '3':
            print("장 시작")
        elif value == '4':
            print("3시 30분 장 종료")

    def retRealData_transferred(self, sCode, sRealType):
        time = self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['체결시간']) # HHMMSS
        cur_price = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['현재가']))) # +(-) 2500
        before_ratio = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['전일대비']))) # +(-) 50
        diff_ratio = float(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['등락율'])) # +(-) 1.9
        first_sell = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['최우선(매도호가)']))) # +(-) 2500
        first_buy = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['최우선(매수호가)'])))  # +(-) 2500
        tick_volume = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['거래량']))) # +(-) 10000
        all_volume = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['누적거래량'])))  # +(-) 10000
        high_price = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['고가'])))  # +(-) 2500
        open_price = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['시가'])))  # +(-) 2500
        low_price = abs(int(self.getCommRealData(sCode, self.realType.REALTYPE[sRealType]['저가'])))  # +(-) 2500

        if sCode not in self.portfolio_stocks_detail:
            self.portfolio_stocks_detail.update({sCode: {}})

        self.portfolio_stocks_detail[sCode].update({"체결시간": time, "현재가": cur_price, "전일대비": before_ratio, "등락율": diff_ratio, "최우선(매도호가)": first_sell,
                                                    "최우선(매수호가)": first_buy, "거래량": tick_volume, "누적거래량": all_volume, "고가": high_price,
                                                    "시가": open_price, "저가": low_price})

        # 실시간 조건에 따라 매도 / 매수
        # print(self.portfolio_stocks_detail[sCode])
        
        non_trading_list = list(self.non_trading_stocks_detail)
        for order_no in non_trading_list:
            code = self.non_trading_stocks_detail[order_no]["종목코드"]
            trading_price = self.non_trading_stocks_detail[order_no]["주문가격"]
            non_trading_count = self.non_trading_stocks_detail[order_no]["미체결수량"]
            trading_status = self.non_trading_stocks_detail[order_no]["매도수구분"]

            if trading_status == "매수" and non_trading_count > 0 and first_sell > trading_price:
                print("%s %s" % ("매수취소 한다", code))
            elif non_trading_count == 0:
                del self.non_trading_stocks_detail[order_no]


    def setInputValue(self, name, value):
        self.dynamicCall("SetInputValue(QString, QString)", name, value)

    def commRqData(self, sRQName, sTrCode, sPrevNext, sScrNo):
        self.dynamicCall("CommRqData(QString, QString, int, QString", sRQName, sTrCode, sPrevNext, sScrNo)

    def getCommData(self, sTrCode, sRQName, idx, name):
        return self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, idx, name)

    def getRepeatCnt(self, sTrCode, sRQName):
        return self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)

    def getCodeListByMarket(self, market_code):
        return self.dynamicCall("GetCodeListByMarket(QString)", market_code)

    def disconnectRealData(self, sScrNo):
        self.dynamicCall("DisconnectRealData(QString)", sScrNo)

    def setRealReg(self, sScrNo, sCodeList, sFidList, sOptType):
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", sScrNo, sCodeList, sFidList, sOptType)

    def getCommRealData(self, sCode, fid):
        return self.dynamicCall("GetCommRealData(QString, int)", sCode,fid)




