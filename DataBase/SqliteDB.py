import sqlite3
from sqlite3 import Error
import pandas as pd

#COLUMNS_CHART_DATA = ['date', 'open', 'high', 'low', 'close', 'volume', 'dayratio', 'frnratio', 'frnvolume', 'insvolume', 'manvolume', 'autovolume']
class StockDB:
    def __init__(self):
        self.conn = self.createConnection('DataBase/DB/stocks.db')

    def create_account_table(self):
        c = self.conn
        try:
            cur = c.cursor()
            create_sql = "CREATE TABLE account_info (accountno TEXT PRIMARY KEY, balance INTEGER, cash INTEGER, totalbalance INTEGER, pvbalance INTEGER, totalwinratio REAL);" # accoutno: 계좌번호, balance: 예수금, cash: 출금가능금액
            cur.execute(create_sql)
            return True
        except:
            print("account_info table creating fail")

    def save_account_table(self, dataframe):
        c = self.conn
        try:
            cur = c.cursor()
            sql = "INSERT OR REPLACE INTO account_info ('accountno', 'balance', 'cash', 'totalbalance', 'pvbalance', 'totalwinratio') VALUES(?, ?, ?, ?, ?, ?)"
            cur.executemany(sql, dataframe.values)
            c.commit()
        except:
            return None

    def load_account_table(self):
        c = self.conn
        try:
            sql = "SELECT accountno, balance, 'totalbalance', 'pvbalance', 'totalwinratio' FROM account_info"
            df = pd.read_sql(sql, c, index_col=None)
            return df
        except:
            return None

    def createBasicInfoTable(self):
        c = self.conn
        try:
            cur = c.cursor()
            create_sql = "CREATE TABLE stock_basicinfo (code TEXT PRIMARY KEY, name TEXT, maketcap INTEGER, per REAL, eps REAL, roe REAL, pbr REAL, multiple REAL);"
            cur.execute(create_sql)
            return True
        except:
            print("stock_basicinfo table creating fail")

    def saveBasicInfoTable(self, dataframe):
        c = self.conn
        try:
            cur = c.cursor()
            sql = "INSERT OR REPLACE INTO stock_basicinfo ('code', 'name', 'maketcap', 'per', 'eps', 'roe', 'pbr', 'multiple') VALUES(?, ?, ?, ?, ?, ?, ?, ?)"
            cur.executemany(sql, dataframe.values)
            c.commit()
        except:
            return None

    def loadBasicInfoTable(self):
        c = self.conn
        try:
            sql = "SELECT code, name, maketcap, per, eps, roe, pbr, multiple FROM stock_basicinfo"
            df = pd.read_sql(sql, c, index_col=None)
            return df
        except:
            return None

    def create_account_detail_table(self, tname):
        c = self.conn
        try:
            cur = c.cursor()
            create_sql = "CREATE TABLE \'%s\' (code TEXT PRIMARY KEY, name TEXT, count INTEGER, tradecount INTEGER, winratio REAL, havratio REAL);" % tname
            cur.execute(create_sql)
            return True
        except:
            print("[%s] table creating fail" % tname)

    def save_account_detail_table(self, tname, dataframe):
        print('[+] call save %s' % tname)
        c = self.conn
        try:
            cur = c.cursor()
            sql = "INSERT OR REPLACE INTO \'%s\' ('code', 'name', 'count', 'tradecount', 'winratio', 'havratio') VALUES(?, ?, ?, ?, ?, ?)" % tname
            cur.executemany(sql, dataframe.values)
            c.commit()
        except:
            return None

    def load_account_detail_table(self, tname):
        c = self.conn
        try:
            sql = "SELECT code, name, tradecount, havratio FROM \'%s\'" % tname
            df = pd.read_sql(sql, c, index_col=None)
            return df
        except:
            return None

    def create_table(self, tname):
        c = self.conn
        try:
            cur = c.cursor()
            create_sql = "CREATE TABLE \'%s\' (date DATETIME PRIMARY KEY, open INT, high INT, low INT, close INT, volume INT);" % tname
            cur.execute(create_sql)
            return True
        except:
            print("[%s] table creating fail" % tname)

    def create_table_detail(self, tname):
        c = self.conn
        try:
            cur = c.cursor()
            create_sql = "CREATE TABLE \'%s\' (date DATETIME PRIMARY KEY, open INT, high INT, low INT, close INT, volume INT, dayratio REAL, frnratio REAL, frnvolume INT, insvolume INT, manvolume INT, autovolume INT);" % tname
            cur.execute(create_sql)
            return True
        except:
            print("[%s] detail table creating fail" % tname)

    def save(self, tname, dataframe):
        print('[+] call save %s' % tname)
        c = self.conn
        try:
            cur = c.cursor()
            sql = "INSERT OR REPLACE INTO \'%s\' ('date', 'open', 'high', 'low', 'close', 'volume') VALUES(?, ?, ?, ?, ?, ?)" % tname
            cur.executemany(sql, dataframe.values)
            c.commit()
        except:
            return None

    def save_detail(self, tname, dataframe):
        print('[+] call save detail %s' % tname)
        c = self.conn
        try:
            cur = c.cursor()
            sql = "INSERT OR REPLACE INTO \'%s\' ('date', 'open', 'high', 'low', 'close', 'volume', 'dayratio', 'frnratio', 'frnvolume', 'insvolume', 'manvolume', 'autovolume') VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" % tname
            cur.executemany(sql, dataframe.values)
            c.commit()
        except:
            return None

    def load(self, tname, startdate=None):
        print('[+] call load %s' % tname)
        c = self.conn
        try:
            if startdate is not None:
                sql = "SELECT date, open, high, low, close, volume FROM \'%s\' WHERE date >= \'%s\' ORDER BY date DESC" % (tname, startdate)
            else:
                sql = "SELECT date, open, high, low, close, volume FROM \'%s\' ORDER BY date DESC" % tname
            df = pd.read_sql(sql, c, index_col=None)
            return df
        except:
            return None

    def load_detail(self, tname, startdate=None):
        print('[+] call load detail %s' % tname)
        c = self.conn
        try:
            if startdate is not None:
                sql = "SELECT date, open, high, low, close, volume, dayratio, frnratio, frnvolume, insvolume, manvolume, autovolume FROM \'%s\' WHERE date >= \'%s\' ORDER BY date DESC" % (tname, startdate)
            else:
                sql = "SELECT date, open, high, low, close, volume, dayratio, frnratio, frnvolume, insvolume, manvolume, autovolume FROM \'%s\' ORDER BY date DESC" % tname
            df = pd.read_sql(sql, c, index_col=None)
            return df
        except:
            return None

    def load_first(self, tname):
        print('[+] call load first %s' % tname)
        c = self.conn
        try:
            sql = "SELECT * FROM \'%s\' ORDER BY date DESC, ROWID LIMIT 1" % tname
            df = pd.read_sql(sql, c, index_col=None)
            return df
        except:
            return None

    def load_nrows(self, tname, nrow):
        print('[+] call load nrows %s' % tname)
        c = self.conn
        try:
            sql = "SELECT * FROM %s ORDER BY date DESC, ROWID LIMIT %s" % (tname, nrow)
            df = pd.read_sql(sql, c, index_col=None)
            return df
        except:
            return None

    def createConnection(self, file):
        conn = None
        try:
            conn = sqlite3.connect(file, check_same_thread=False)
            return conn
        except Error as e:
            print(e)
        return conn


    def getTableName(self, code):
        name = "StockData_" + code
        return name

    def checkTableName(self, tname):
        c = self.conn
        cur = c.cursor()
        sql = "SELECT count(*) FROM sqlite_master WHERE Name = \'%s\'" % tname
        cur.execute(sql)
        rows = cur.fetchall()
        for row in rows:
            if str(row[0]) == "1":
                return True
        return False

