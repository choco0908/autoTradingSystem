from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *
from config.errorCode import *
import os

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        print("[+] Kiwoom init called")

        #init values
        self.account_num = ''
        self.passwd = ''
        self.pwtype = ''
        self.use_money = 0
        self.user_money_ratio = 0.5
        self.account_stocks_detail = {}
        self.non_trading_stocks_detail = {}

        ##### eventloop 모음
        self.login_event_loop = None
        self.detail_account_event_loop = QEventLoop()
        self.get_stock_data_event_loop = QEventLoop()
        ###################

        ##### 스크린 번호
        self.screen_info = ["1000","2000"]

        if not os.path.exists('credentials.txt'):
            print('credentials is not exists')
            return
        else:
            with open('credentials.txt', 'r') as f:
                self.passwd = f.readline()
                self.pwtype = f.readline()
                f.close()

        self.get_ocx_instance()
        self.event_slots()
        self.signal_login_commConnect()

        # 계좌번호 조회
        self.get_acoount()
        # 예수금 조회
        self.detail_account()
        # 계좌평가잔고내역 조회
        self.detail_account_stocks()
        # 미체결 요청
        self.non_trading_stocks()
        #종목 분석
        self.analysis_stock()

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.tr_slot)

    def login_slot(self, errorCode):
        if errorCode == 0:
            print("connected")
        else:
            print("disconnected")
        print(errors(errorCode))

        self.login_event_loop.exit()

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
        print('예수금 확인')
        self.setInputValue("계좌번호", self.account_num)
        self.setInputValue("비밀번호", self.passwd)
        self.setInputValue("비밀번호입력매체구분", self.pwtype)
        self.setInputValue("조회구분", "2")
        self.commRqData("예수금상세현황","opw00001","0",self.screen_info[0])

        self.detail_account_event_loop.exec_()

    def detail_account_stocks(self, sPrevNext="0"):
        print('계좌평가잔고내역 확인')
        self.setInputValue("계좌번호", self.account_num)
        self.setInputValue("비밀번호", self.passwd)
        self.setInputValue("비밀번호입력매체구분", self.pwtype)
        self.setInputValue("조회구분", "2")
        self.commRqData("계좌평가잔고내역", "opw00018", sPrevNext , self.screen_info[0])

        self.detail_account_event_loop.exec_()

    def non_trading_stocks(self, sPrevNext="0"):
        self.setInputValue("계좌번호", self.account_num)
        self.setInputValue("체결구분", "1")
        self.setInputValue("매매구분", "0")
        self.commRqData("실시간미체결요청", "opt10075", sPrevNext, self.screen_info[0])

        self.detail_account_event_loop.exec_()

    def get_code_list_by_market(self, market_code):
        '''
        종목 코드들 반환
        :param market_code: 
        :return: 
        '''
        code_list = self.getCodeListByMarket(market_code)
        code_list = code_list.split(";")[:-1]

        return code_list

    def analysis_stock(self):
        '''
        종목 분석
        :return:
        '''
        code_list_kospi = self.get_code_list_by_market("0")
        code_list_kosdaq = self.get_code_list_by_market("10")
        print("코스피 종목 갯수 %s" % len(code_list_kospi))
        print(code_list_kospi)
        print("코스닥 종목 갯수 %s" % len(code_list_kosdaq))
        print(code_list_kosdaq)
        list_kospi = []
        list_kosdaq = []

        if not os.path.exists('stock_list'):
            print('stock_list is not exists')
            return
        else:
            with open('stock_list', 'r') as f:
                while True:
                    stock = f.readline().strip()
                    if not stock: break
                    if stock in code_list_kospi:
                        list_kospi.append(stock)
                    elif stock in code_list_kosdaq:
                        list_kosdaq.append(stock)
                f.close()
            if len(list_kospi) == 0 and len(list_kosdaq) == 0:
                print('stock_list is empty')

        print("코스피 종목 %s개 / 코스닥 종목 %s개 분석 시작" % (len(list_kospi), len(list_kosdaq)))
        for idx, code in enumerate(list_kospi):
            self.disconnectRealData(self.screen_info[1])
            print("%s / %s : KOSPI Stock Code : %s is updating..." % (idx+1, len(list_kospi), code))
            self.get_kiwoom_stock_data(code)

        for idx, code in enumerate(list_kosdaq):
            self.disconnectRealData(self.screen_info[1])
            print("%s / %s : KOSDAQ Stock Code : %s is updating..." % (idx+1, len(list_kosdaq), code))
            self.get_kiwoom_stock_data(code)


    def get_kiwoom_stock_data(self, code=None, date=None, sPrevNext="0"):
        '''
        차트 일봉 조회
        :param code:
        :param date:
        :param sPrevNext:
        :return:
        '''
        QTest.qWait(3600)
        self.setInputValue("종목코드", code)
        self.setInputValue("수정주가구분", "1")

        if date != None:
            self.setInputValue("기준일자",date)

        self.commRqData("주식일봉차트조회", "opt10081", sPrevNext, self.screen_info[1])

        self.get_stock_data_event_loop.exec_()


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
        print("예수금 %s" % int(deposit))

        self.use_money = int(deposit) * self.user_money_ratio
        self.use_money = self.use_money / 4

        candeposit = self.getCommData(sTrCode, sRQName, 0, "출금가능금액")
        print("출금가능금액 %s" % int(candeposit))

        self.detail_account_event_loop.exit()

    def retDetail_account_stocks(self, sTrCode, sRQName, sPrevNext):
        total_portfolio_stocks = self.getCommData(sTrCode, sRQName, 0, "총매입금액")
        print("총매입금액 %s" % int(total_portfolio_stocks))

        win_portfolio_rate = self.getCommData(sTrCode, sRQName, 0, "총수익률(%)")
        print("총수익률 %s%%" % float(win_portfolio_rate))

        rows = self.getRepeatCnt(sTrCode, sRQName)
        cnt = 0

        if rows == 0:
            print("계좌에 조회할 종목이 없습니다.")

        for idx in range(rows):
            code = self.getCommData(sTrCode, sRQName, idx, "종목번호")
            code = code.strip()[1:]  # 영어 제외 종목코드만
            code_name = self.getCommData(sTrCode, sRQName, idx, "종목명")
            code_name = code_name.strip()
            stock_quantity = self.getCommData(sTrCode, sRQName, idx, "보유수량")
            stock_quantity = int(stock_quantity.strip())
            buy_price = self.getCommData(sTrCode, sRQName, idx, "매입가")
            buy_price = int(buy_price.strip())
            win_ratio = self.getCommData(sTrCode, sRQName, idx, "수익률(%)")
            win_ratio = float(win_ratio.strip())
            current_price = self.getCommData(sTrCode, sRQName, idx, "현재가")
            current_price = int(current_price.strip())
            total_buy_price = self.getCommData(sTrCode, sRQName, idx, "매입금액")
            total_buy_price = int(total_buy_price.strip())
            possible_quantity = self.getCommData(sTrCode, sRQName, idx, "매매가능수량")
            possible_quantity = int(possible_quantity.strip())

            if code in self.account_stocks_detail:
                pass
            else:
                self.account_stocks_detail.update({code: {}})

            account_stock_detail = self.account_stocks_detail[code]

            account_stock_detail.update({"종목명": code_name})
            account_stock_detail.update({"보유수량": stock_quantity})
            account_stock_detail.update({"매입가": buy_price})
            account_stock_detail.update({"수익률(%)": win_ratio})
            account_stock_detail.update({"현재가": current_price})
            account_stock_detail.update({"매입금액": total_buy_price})
            account_stock_detail.update({"매매가능수량": possible_quantity})
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
            code = self.getCommData(sTrCode, sRQName, idx, "종목번호")
            code = code.strip()
            code_name = self.getCommData(sTrCode, sRQName, idx, "종목명")
            code_name = code_name.strip()
            order_no = self.getCommData(sTrCode, sRQName, idx, "주문번호")
            order_no = int(order_no.strip())
            order_status = self.getCommData(sTrCode, sRQName, idx, "주문상태") # 접수,확인,체결
            order_status = int(order_status.strip())
            order_quantity = self.getCommData(sTrCode, sRQName, idx, "주문수량")
            order_quantity = int(order_quantity.strip())
            order_price = self.getCommData(sTrCode, sRQName, idx, "주문가격")
            order_price = int(order_price.strip())
            order_gubun = self.getCommData(sTrCode, sRQName, idx, "주문구분") # -매도, +매수, -
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')
            non_trading_quantity = self.getCommData(sTrCode, sRQName, idx, "미체결수량")
            non_trading_quantity = int(non_trading_quantity.strip())
            trading_quantity = self.getCommData(sTrCode, sRQName, idx, "체결량")
            trading_quantity = int(trading_quantity.strip())
            
            if order_no in self.non_trading_stocks_detail:
                pass
            else:
                self.non_trading_stocks_detail[order_no] = {}

            non_trading_stock_detail = self.non_trading_stocks_detail[order_no]

            non_trading_stock_detail.update({"종목코드": code})
            non_trading_stock_detail.update({"종목명": code_name})
            non_trading_stock_detail.update({"주문번호": order_no})
            non_trading_stock_detail.update({"주문상태": order_status})
            non_trading_stock_detail.update({"주문수량": order_quantity})
            non_trading_stock_detail.update({"주문가격": order_price})
            non_trading_stock_detail.update({"주문구분": order_gubun})
            non_trading_stock_detail.update({"미체결수량": non_trading_quantity})
            non_trading_stock_detail.update({"체결량": trading_quantity})

            print("미체결 종목 : %s" % non_trading_stock_detail)

        self.detail_account_event_loop.exit()

    def retGet_kiwoom_stock_data(self, sTrCode, sRQName, sPrevNext):
        code = self.getCommData(sTrCode, sRQName, 0, "종목코드")
        code = code.strip()
        rows = self.getRepeatCnt(sTrCode, sRQName)
        print("%s 일봉데이터 %s개 요청" % (code, rows))

        if sPrevNext == "2":
            self.get_kiwoom_stock_data(code=code, sPrevNext=sPrevNext)
        else:
            self.get_stock_data_event_loop.exit()

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




