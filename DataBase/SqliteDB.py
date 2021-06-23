import sqlite3
from sqlite3 import Error
import pandas as pd

#COLUMNS_CHART_DATA = ['date', 'open', 'high', 'low', 'close', 'volume']
class StockDB:
    def __init__(self):
        self.conn = self.createConnection('DataBase/DB/stocks.db')

    def createBasicInfoTable(self):
        with self.conn as c:
            try:
                cur = c.cursor()
                create_sql = "CREATE TABLE stock_basic_info (code TEXT PRIMARY KEY, name TEXT, maketcap INTEGER, per REAL, eps REAL, roe REAL, pbr REAL, multiple REAL);"
                cur.execute(create_sql)
                return True
            except:
                print("basic_info table creating fail")

    def saveBasicInfoTable(self, dataframe):
        with self.conn as c:
            try:
                cur = c.cursor()
                sql = "INSERT OR REPLACE INTO stock_basic_info ('code', 'name', 'maketcap', 'per', 'eps', 'roe', 'pbr', 'multiple') VALUES(?, ?, ?, ?, ?, ?, ?, ?)"
                cur.executemany(sql, dataframe.values)
                c.commit()
            except:
                return None

    def loadBasicInfoTable(self):
        with self.conn as c:
            try:
                sql = "SELECT code, name, maketcap, per, eps, roe, pbr, multiple FROM stock_basic_info"
                df = pd.read_sql(sql, c, index_col=None)
                return df
            except:
                return None

    def createTable(self, tname):
        with self.conn as c:
            try:
                cur = c.cursor()
                create_sql = "CREATE TABLE %s (date DATETIME PRIMARY KEY, open INT, high INT, low INT, close INT, volume INT);" % tname
                cur.execute(create_sql)
                return True
            except:
                print("[%s] table creating fail" % tname)

    def save(self, tname, dataframe):
        print('[+] call save %s' % tname)
        with self.conn as c:
            try:
                cur = c.cursor()
                sql = "INSERT OR REPLACE INTO \'%s\' ('date', 'open', 'high', 'low', 'close', 'volume') VALUES(?, ?, ?, ?, ?, ?)" % tname
                cur.executemany(sql, dataframe.values)
                c.commit()
            except:
                return None

    def load(self, tname, startdate=None):
        print('[+] call load %s' % tname)
        with self.conn as c:
            try:
                if startdate is not None:
                    sql = "SELECT date, open, high, low, close, volume FROM \'%s\' WHERE date >= \'%s\' ORDER BY date DESC" % (tname, startdate)
                else:
                    sql = "SELECT date, open, high, low, close, volume FROM \'%s\' ORDER BY date DESC" % tname
                df = pd.read_sql(sql, c, index_col=None)
                return df
            except:
                return None

    def createConnection(self, file):
        conn = None
        try:
            conn = sqlite3.connect(file,check_same_thread=False)
            return conn
        except Error as e:
            print(e)
        return conn


    def getTableName(self, code):
        name = "StockData_" + code
        return name

    def checkTableName(self, tname):
        with self.conn as c:
            cur = c.cursor()
            sql = "SELECT count(*) FROM sqlite_master WHERE Name = \'%s\'" % tname
            cur.execute(sql)
            rows = cur.fetchall()
            for row in rows:
                if str(row[0]) == "1":
                    return True
            return False

