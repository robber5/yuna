from packages import pymysql
import WindPy
import re
import datetime
from functools import partial

__title__ = 'yuna'
__version__ = '0.0.3'
__author__ = 'lvzhi'
__copyright__ = 'Copyright 2017 lvzhi'

'''连接数据库相关常量'''
HOST = 'localhost'
PORT = 3306
USER = 'root'
PASS_WD = 'lvzhi'
DB = 'yuna'


class TechnicalIndicator:

    def __init__(self, data):
        self.data = data
        self.ans = []

    def _handle(self):
        pass


class Ema(TechnicalIndicator):
    """指数移动平均线"""

    def __init__(self, data, days, weight_factor=0.7):
        TechnicalIndicator.__init__(self, data)
        self.days = days
        self.weight_factor = 2 / (days + 1)
        """
        if len(self.data) < self.days:
            raise ValueError("数据长度不应小于天数")
        """
        self._handle()

    def _handle(self):
        """
            data = [3, 4, 5]
            len(data) #3
            Ema(data, 1) => len(.ans) #3 => 3-1+1=3

        ans_length = len(self.data) - self.days + 1
        for one in range(ans_length):
            var = 0
            for day in range(self.days):
                if day == 0:
                    var = self.data[day + one]
                else:
                    var = self.weight_factor * self.data[day + one] + (1 - self.weight_factor) * var
            self.ans.append(var)
        """
        ans_length = len(self.data)
        for one in range(ans_length):
            if one == 0:
                self.ans.append(self.data[one])
            else:
                self.ans.append(self.weight_factor * self.data[one] + (1 - self.weight_factor) * self.ans[-1])

    def __sub__(self, other):
        """
        ans = []
        if len(other.ans) > len(self.ans):
            other.ans = other.ans[-(len(self.ans)):]
            ans_length = len(self.ans)
        else:
            self.ans = self.ans[-(len(other.ans)):]
            ans_length = len(other.ans)
        for one in range(ans_length):
            ans.append(self.ans[one] - other.ans[one])
        obj = Ema(ans, 1)
        return obj
        """
        ans, ans_length = [], len(self.ans)
        for one in range(ans_length):
            ans.append(self.ans[one] - other.ans[one])
        obj = Ema(ans, 1)
        return obj

    def __mul__(self, other):
        obj = Ema(list(map(lambda x: x * other, self.ans)), 1)
        return obj


class Macd(TechnicalIndicator):
    """指数平滑移动平均线"""
    def __init__(self, data, short=12, long=26, m=9):
        TechnicalIndicator.__init__(self, data)
        self.short = short
        self.long = long
        self.m = m
        """
        if len(self.data) < (self.long + self.m - 2):
            raise ValueError("数据长度不应小于天数")
        """
        self._handle()

    def _handle(self):
        diff = Ema(self.data, self.short) - Ema(self.data, self.long)
        self.ans.append(diff.ans)
        dea = Ema(diff.ans, self.m)
        self.ans.append(dea.ans)
        macd = (diff - dea) * 2
        self.ans.append(macd.ans)


def _update(conn, stocks, date=1):
    """周六日无法更新"""
    if datetime.date.today().weekday() in (5, 6):
        return 'None'
    if isinstance(stocks, str):
        stock_list = [stocks + '.sh' if stocks[0] == '6' else stocks + '.sz']
    else:
        stock_list = [stock + '.sh' if stock[0] == '6' else stock + '.sz' for stock in stocks]
    (year, mon, mday, *scrap) = (datetime.date.today() - datetime.timedelta(days=date)).timetuple()
    query_date = '{}-{}-{}'.format(year, mon, mday)
    WindPy.w.start()
    cur = conn.cursor()
    for stock_name in stock_list:
        a = WindPy.w.wsd(stock_name, 'close', query_date)
        time_list, data_list, code_list = a.Times, a.Data, a.Codes
        '''减1去除当天的不稳定数据（上午是昨天，下午是当天，数据源更新问题造成数据后续更新产生bug）'''
        time_list.append(len(a.Times)-1)
        data_list.append(len(a.Data))
        code_list.append(len(a.Codes))

        """
        b = a.Times[0].timetuple()
        c = a.Data[0][0]
        d = a.Codes[0]
        """

        for code in range(code_list[-1]):
            try:
                cur.execute('create table `{}` (time date not null, price float not null)'.format(code_list[code][:-3]))
            except pymysql.err.InternalError:
                pass
            for time in range(time_list[-1]):
                if not cur.execute('select * from `{}` where time = {}{}{}'.format(
                        code_list[code][:-3], time_list[time].timetuple()[0],
                        _date_update(time_list[time].timetuple()[1]),
                        _date_update(time_list[time].timetuple()[2]))):
                    cur.execute('insert into `{}` values ({}{}{}, {})'.format(
                        code_list[code][:-3], time_list[time].timetuple()[0],
                        _date_update(time_list[time].timetuple()[1]),
                        _date_update(time_list[time].timetuple()[2]),
                        data_list[code][time]))
                else:
                    pass
    conn.commit()
    cur.close()
    return 'OK'


def _delete(conn):
    cur = conn.cursor()
    cur.execute("select concat('drop table `', table_name, '`;') from information_schema.tables where table_schema = "
                "'{}'".format(DB))
    var = cur.fetchall()
    length = len(var)
    for i in range(length):
        cur.execute("{}".format(var[i][0]))
    conn.commit()
    cur.close()


def _query(conn, stock, indicator=0):
    cur = conn.cursor()
    cur.execute("select price from `{}` order by time".format(stock))
    var = cur.fetchall()
    data = []
    for i in range(len(var)):
        data.append(var[i][0])
    a = indicator(data).ans
    print(a)
    conn.commit()
    cur.close()


def _date_update(original_date):
    """把类似2这样的单个数字转化为02，而双数字则保持不变"""
    return re.sub(r'(\b[1-9]\b)', r'0\1', str(original_date))


if __name__ == '__main__':
    conn = pymysql.connect(host=HOST, port=PORT, user=USER, passwd=PASS_WD, db=DB,
                           charset='utf8')
    update = partial(_update, conn)
    delete = partial(_delete, conn)
    query = partial(_query, conn)
    """conn.close()"""
