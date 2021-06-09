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
            self.dynamicCall("SetInputValue(String, String)","계좌번호", self.account_num)
            self.dynamicCall("SetInputValue(String, String)","비밀번호", f.readline())
            self.dynamicCall("SetInputValue(String, String)","비밀번호입력매체구분", f.readline())
            self.dynamicCall("SetInputValue(String, String)","조회구분", "2")
            self.dynamicCall("CommRqData(String, String, int, String)","예수금상세현황","opw00001","0","1000")
            f.close()
            self.detail_account_event_loop = QEventLoop()
            self.detail_account_event_loop.exec_()

    def detail_account_stocks(self, sPrevNext="0"):
        print('계좌평가잔고내역 확인')
        with open('credentials.txt','r') as f:
            self.dynamicCall("SetInputValue(String, String)","계좌번호", self.account_num)
            self.dynamicCall("SetInputValue(String, String)","비밀번호", f.readline())
            self.dynamicCall("SetInputValue(String, String)","비밀번호입력매체구분", f.readline())
            self.dynamicCall("SetInputValue(String, String)","조회구분", "2")
            self.dynamicCall("CommRqData(String, String, int, String)", "계좌평가잔고내역", "opw00018", sPrevNext , "1000")
            f.close()
            self.detail_account_stocks_event_loop = QEventLoop()
            self.detail_account_stocks_event_loop.exec_()

    def tr_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        '''
        tr요청 받는 slot
        :param sScrNo: 스크린번호
        :param sRQName: 요청명
        :param sTrCode: tr코드
        :param sRecordName: 사용 X 
        :param sPrevNext: 다음 페이지 여부
        :return: 
        '''

        if sRQName == "예수금상세현황":
            deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "예수금")
            print("예수금 %s" % int(deposit))
            
            candeposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "출금가능금액")
            print("출금가능금액 %s" % int(candeposit))

            self.detail_account_event_loop.exit()
        elif sRQName == "계좌평가잔고내역":
            total_portfolio_stocks = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "총매입금액")
            print("총매입금액 %s" % int(total_portfolio_stocks))

            win_portfolio_rate = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0,"총수익률(%)")
            print("총수익률 %s%%" % float(win_portfolio_rate))

            self.detail_account_stocks_event_loop.exit()






