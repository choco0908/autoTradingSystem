from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from config.errorCode import *
import os

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        print("[+] Kiwoom init called")

        #init values
        self.account_num = ''
        self.use_money = 0
        self.user_money_ratio = 0.5
        self.account_stock_detail = {}

        ##### eventloop 모음
        self.login_event_loop = None
        self.detail_account_event_loop = None
        self.detail_account_stocks_event_loop = None
        ###################

        if not os.path.exists('credentials.txt'):
            print('credentials is not exists')
            return

        self.get_ocx_instance()
        self.event_slots()
        self.signal_login_commConnect()

        self.get_acoount()
        self.detail_account()
        self.detail_account_stocks_event_loop = QEventLoop()
        self.detail_account_stocks()

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
        with open('credentials.txt','r') as f:
            self.setInputValue("계좌번호", self.account_num)
            self.setInputValue("비밀번호", f.readline())
            self.setInputValue("비밀번호입력매체구분", f.readline())
            self.setInputValue("조회구분", "2")
            self.commRqData("예수금상세현황","opw00001","0","1000")
            f.close()
            self.detail_account_event_loop = QEventLoop()
            self.detail_account_event_loop.exec_()

    def detail_account_stocks(self, sPrevNext="0"):
        print('계좌평가잔고내역 확인')
        with open('credentials.txt','r') as f:
            self.setInputValue("계좌번호", self.account_num)
            self.setInputValue("비밀번호", f.readline())
            self.setInputValue("비밀번호입력매체구분", f.readline())
            self.setInputValue("조회구분", "2")
            self.commRqData("계좌평가잔고내역", "opw00018", sPrevNext , "1000")
            f.close()
            self.detail_account_stocks_event_loop.exec_()

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
            deposit = self.getCommData(sTrCode, sRQName, 0, "예수금")
            print("예수금 %s" % int(deposit))

            self.use_money = int(deposit) * self.user_money_ratio
            self.use_money = self.use_money / 4
            
            candeposit = self.getCommData(sTrCode, sRQName, 0, "출금가능금액")
            print("출금가능금액 %s" % int(candeposit))

            self.detail_account_event_loop.exit()
        elif sRQName == "계좌평가잔고내역":
            total_portfolio_stocks = self.getCommData(sTrCode, sRQName, 0, "총매입금액")
            print("총매입금액 %s" % int(total_portfolio_stocks))

            win_portfolio_rate = self.getCommData(sTrCode, sRQName, 0,"총수익률(%)")
            print("총수익률 %s%%" % float(win_portfolio_rate))

            rows = self.getRepeatCnt(sTrCode, sRQName)
            cnt = 0

            if rows == 0:
                print("계좌에 조회할 종목이 없습니다.")

            for idx in range(rows):
                code = self.getCommData(sTrCode, sRQName, idx, "종목번호")
                code = code.strip()[1:] #영어 제외 종목코드만
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

                if code in self.account_stock_detail:
                    pass
                else:
                    self.account_stock_detail.update({code:{}})

                self.account_stock_detail[code].update({"종목명":code_name})
                self.account_stock_detail[code].update({"보유수량":stock_quantity})
                self.account_stock_detail[code].update({"매입가":buy_price})
                self.account_stock_detail[code].update({"수익률(%)":win_ratio})
                self.account_stock_detail[code].update({"현재가":current_price})
                self.account_stock_detail[code].update({"매입금액":total_buy_price})
                self.account_stock_detail[code].update({"매매가능수량":possible_quantity})
                print(self.account_stock_detail[code])
                cnt += 1

            if sPrevNext == "2":
                self.detail_account_stocks(sPrevNext="2")
            else:
                self.detail_account_stocks_event_loop.exit()


    def setInputValue(self, name, value):
        self.dynamicCall("SetInputValue(QString, QString)", name, value)

    def commRqData(self, sRQName, sTrCode, sPrevNext, sScrNo):
        self.dynamicCall("CommRqData(QString, QString, int, QString", sRQName, sTrCode, sPrevNext, sScrNo)

    def getCommData(self, sTrCode, sRQName, idx, name):
        return self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, idx, name)

    def getRepeatCnt(self, sTrCode, sRQName):
        return self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)




