from Kiwoom.kiwoom import Kiwoom
import sys
from PyQt5.QtWidgets import *

class UI_Class():
    def __init__(self):
        print("[+] UI init called")

        self.app = QApplication(sys.argv)

        self.kiwwom = Kiwoom()

        self.app.exec_()