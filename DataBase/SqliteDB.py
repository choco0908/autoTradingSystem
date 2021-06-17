import sqlite3
from sqlite3 import Error
import pandas as pd

#COLUMNS_CHART_DATA = ['date', 'open', 'high', 'low', 'close', 'volume']
class StockDB:
    def __init__(self):
        self.conn = self.createConnection('DataBase/DB/stocks.db')

    def createTable(self, tname):
        with self.conn as c:
            try:
                cur = c.cursor()
                create_sql = "CREATE TABLE %s (date DATETIME PRIMARY KEY, open INT, high INT, low INT, close INT, volume INT);" % tname
                cur.execute(create_sql)
                return True
            except:
                print("[%s] creating fail" % tname)

    def save(self, tname, dataframe):
        with self.conn as c:
            try:
                cur = c.cursor()
                sql = "INSERT OR REPLACE INTO \'%s\' ('date', 'open', 'high', 'low', 'close', 'volume') VALUES(?, ?, ?, ?, ?, ?)" % tname
                cur.executemany(sql, dataframe.values)
                c.commit()
            except:
                return None

    def load(self, tname):
        with self.conn as c:
            try:
                sql = "SELECT date, open, high, low, close, volume FROM \'%s\' ORDER BY date ASC" % tname
                df = pd.read_sql(sql, c, index_col=None)
                return df
            except:
                return None

    def createConnection(self, file):
        conn = None
        try:
            conn = sqlite3.connect(file)
            print(sqlite3.version)
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
