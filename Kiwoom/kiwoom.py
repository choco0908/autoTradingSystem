from PyQt5.QAxContainer import *
from PyQt5.QtCore import *

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        print("[+] Kiwoom init called")

        ##### eventloop 모음
        self.login_event_loop = None
        ###################
        self.get_ocx_instance()
        self.event_slots()
        self.signal_login_commConnect()

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)

    def login_slot(self, errorCode):
        if errorCode == 0:
            print("connected")
        else:
            print("disconnected")

        self.login_event_loop.exit()

    def signal_login_commConnect(self):
        self.dynamicCall("CommConnect()")

        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()