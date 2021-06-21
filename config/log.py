import logging
from datetime import datetime
import os

class Logging():
    def __init__(self, log_path='log'):
        self.log_path = log_path
        if not os.path.exists(log_path):
            os.mkdir(log_path)

        fh = logging.FileHandler(filename=os.path.join(self.log_path, '{:%Y-%m-%d}.log'.format(datetime.now())),
                                 encoding="utf-8")
        format = '[%(asctime)s] I %(filename)s | %(name)s-%(funcName)s-%(lineno)04d I %(levelname)-8s > %(message)s'
        fh.setLevel(logging.DEBUG)
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        logging.basicConfig(format=format, handlers=[fh,sh], level=logging.DEBUG)
