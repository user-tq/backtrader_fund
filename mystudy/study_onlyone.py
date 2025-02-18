import datetime
import akshare as ak
import pandas as pd
import backtrader as bt
import backtrader.analyzers as btanalyzers

class BBandStrategy(bt.Strategy):
    """
    如果跌破布林下线则买入，跌破中线买入一半，从中线上涨到上线则卖出二分之一，从下线上涨到布林中线卖出二分之一。
    """

    params = (
        ("period", 20),
        ("printlog", True),
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        self.dataprice = self.datas[0].close
        self.order = None
        self.mid = bt.indicators.BollingerBands(
            self.datas[0], period=self.params.period
        ).mid
        self.bot = bt.indicators.BollingerBands(
            self.datas[0], period=self.params.period
        ).bot
        self.top = bt.indicators.BollingerBands(
            self.datas[0], period=self.params.period
        ).top
        self.buy_value = []

    def next(self):

        position_size = self.broker.getposition(data=self.datas[0]).size
        
        self.log(f"{position_size}, {self.dataprice[0]}, {self.bot[0]}")

        if self.dataprice[0] <= self.bot[0] and position_size <= 0:
            self.order_target_percent(data=self.datas[0], target=0.3)
            self.buy_value.append(self.dataprice[0])

        if self.dataprice[0] <= self.bot[0] and position_size > 0:
            if self.dataprice[0] < self.buy_value[-1]:
                self.order_target_percent(data=self.datas[0], target=0.7)
                self.buy_value.append(self.dataprice[0])

        if self.dataprice[0] >= self.mid[0] and position_size > 0:
            self.order_target_percent(data=self.datas[0], target=position_size // 2)
            self.buy_value.append(self.dataprice[0])

        if self.dataprice[0] >= self.top[0] and position_size > 0:
            self.order_target_percent(data=self.datas[0], target=0)
            self.buy_value.clear()

        if self.dataprice[0] <= self.mid[0] and position_size <= 0:
            self.order_target_percent(data=self.datas[0], target=0.3)
            self.buy_value.append(self.dataprice[0])

    def stop(self):
        return_all = self.broker.getvalue() / 200000.0
        print(
            "{0}, {1}%, {2}%".format(
                self.params.period,
                round((return_all - 1.0) * 100, 2),
                round((pow(return_all, 1.0 / 8) - 1.0) * 100, 2),
            )
        )

def getakdata():

    # 利用 AKShare 获取股票的后复权数据，这里只获取前 6 列
    stock_hfq_df = ak.fund_etf_hist_em( symbol="510300",period="daily", adjust="")
    print(stock_hfq_df)

    #stock_hfq_df = ak.stock_zh_a_hist(symbol="600028", adjust="hfq").iloc[:, :6]
    # 处理字段命名，以符合 Backtrader 的要求
    stock_hfq_df.columns = [
        "date",
        "open",
        "close",
        "high",
        "low",
        "volume",
    ]
    # 把 date 作为日期索引，以符合 Backtrader 的要求
    stock_hfq_df.index = pd.to_datetime(stock_hfq_df["date"])

    # 确保日期列被解析为 datetime 类型
    # stock_hfq_df['datetime'] = pd.to_datetime(stock_hfq_df['datetime'])

    # 将数值列转换为浮点数或整数
    stock_hfq_df["open"] = pd.to_numeric(stock_hfq_df["open"], errors="coerce")
    stock_hfq_df["high"] = pd.to_numeric(stock_hfq_df["high"], errors="coerce")
    stock_hfq_df["low"] = pd.to_numeric(stock_hfq_df["low"], errors="coerce")
    stock_hfq_df["close"] = pd.to_numeric(stock_hfq_df["close"], errors="coerce")
    stock_hfq_df["volume"] = pd.to_numeric(stock_hfq_df["volume"], errors="coerce")
    return stock_hfq_df


if __name__ == "__main__":

    cash = 200000.00
    periods = range(1, 60)

    run_start_date = datetime.datetime(2020, 1, 6)
    end_date = datetime.datetime.now()
    stock_hfq_df=getakdata()
    data = bt.feeds.PandasData(
        dataname=stock_hfq_df, fromdate=run_start_date, todate=end_date
    )
    cerebro = bt.Cerebro()
    # cerebro.optstrategy(BBandStrategy, period=periods, printlog=False)
    cerebro.addstrategy(BBandStrategy, period=20)

    cerebro.adddata(data)

    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=0.00015)

    cerebro.addanalyzer(btanalyzers.SharpeRatio_A, _name="sharp")
    cerebro.addanalyzer(btanalyzers.AnnualReturn, _name="annualreturn")
    cerebro.addanalyzer(btanalyzers.Returns, _name="return")
    cerebro.addanalyzer(btanalyzers.SQN, _name="SQN")

    cerebro.run()
    #b = Bokeh()
    cerebro.plot()
