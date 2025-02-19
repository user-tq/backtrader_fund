import backtrader as bt
import datetime
import akshare as ak
import pandas as pd
import backtrader.analyzers as btanalyzers




class CMWilliamsVixFix(bt.Indicator):
    lines = ('vixfix',)  # 定义一个布尔值的输出线
    params = (
        ('pd', 22),      # LookBack Period Standard Deviation High
        ('bbl', 20),     # Bollinger Band Length
        ('mult', 2.0),   # Bollinger Band Standard Deviation Up
        ('lb', 50),      # Look Back Period Percentile High
        ('ph', 0.85),    # Highest Percentile
        ('pl', 1.01),    # Lowest Percentile
    )

    def __init__(self):
        # 计算 WVF
        highest_close = bt.indicators.Highest(self.data.close, period=self.p.pd)
        self.wvf = ((highest_close - self.data.low) / highest_close) * 100

        # 计算布林带上轨
        mid_line = bt.indicators.SMA(self.wvf, period=self.p.bbl)
        std_dev = self.p.mult * bt.indicators.StdDev(self.wvf, period=self.p.bbl)
        self.upper_band = mid_line + std_dev

        # 计算范围高
        self.range_high = bt.indicators.Highest(self.wvf, period=self.p.lb) * self.p.ph

    def next(self):
        # 在 next() 方法中动态计算布尔值
        self.lines.vixfix[0] = self.wvf[0] >= self.upper_band[0] or self.wvf[0] >= self.range_high[0]



class RSIGoldenCross(bt.Indicator):
    lines = ('golden_cross',)  # 定义一个线用于绘制金叉信号

    def __init__(self):
        # 定义两个RSI指标
        self.rsi_short = bt.indicators.RSI(self.data.close, period=6)
        self.rsi_long = bt.indicators.RSI(self.data.close, period=12)
        
        # 检测金叉
        self.lines.golden_cross = bt.ind.CrossUp(self.rsi_short, self.rsi_long)

class MyStrategy(bt.Strategy):
    """
    主策略程序 (修正版)
    """
    lines = ('vixfix',)
    params = (
        ('pd', 12),  # 日k用22，30分用12
        ('bbl', 20),  # Bollinger Band Length
        ('mult', 2.0),  # Bollinger Band Standard Deviation Up
        ('lb', 50),  # Look Back Period Percentile High
        ('ph', 0.85),  # Highest Percentile
        ('pl', 1.01),  # Lowest Percentile
        ('hp', False),  # Show High Range
        ('sd', False),  # Show Standard Deviation Line
        ("stop_loss", 0.02),  # 新增止损比例参数 params.stop_loss
        ("stop_win", 0.05)
    )

    def __init__(self):
        self.data_close = self.datas[0].close
        self.data_low = self.datas[0].low
        self.data_high = self.datas[0].high
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.stop_loss_price = None  # 止损价格
        self.stop_win_price = None  # 止盈价格
        
        self.mid = bt.indicators.BollingerBands(
            self.datas[0], period=20
        ).mid
        self.bot = bt.indicators.BollingerBands(
            self.datas[0], period=20
        ).bot
        self.top = bt.indicators.BollingerBands(
            self.datas[0], period=20
        ).top

        # 使用参数化RSI周期
        self.rsi_cross = RSIGoldenCross()
        self.vix_indicator = CMWilliamsVixFix()

    def next(self):

        # 有未完成订单直接返回
        
        if self.order:
            return
        current_time = self.datas[0].datetime.time(0)

        # 判断是否是下午1点之后
        if current_time >=datetime.time(13, 0, 0):
            self.log("当前时间是下午1点之后")
        else:
            return
        # 没有持仓时的买入逻辑
        if self.position.size == 0:
            # RSI6上穿RSI12（严格判断）
            if self.rsi_cross.lines.golden_cross[0]  and \
                (self.vix_indicator.lines.vixfix[-1] or self.vix_indicator.lines.vixfix[-2] or self.vix_indicator.lines.vixfix[-3] or self.vix_indicator.lines.vixfix[-4])\
                and (self.data_low[0] <= self.bot[0] or self.data_low[-1] <= self.bot[-1] or self.data_low[-2] <= self.bot[-2] or self.data_low[-3] <= self.bot[-3] or self.data_low[-4] <= self.bot[-4])\
                and (self.data_low[0] > min( self.data_low[-1], self.data_low[-2], self.data_low[-3], self.data_low[-4])) \
                and not (self.data_low[-1] < self.data_low[-2] < self.data_low[-3]):#\
                #and self.
                self.order = self.buy()  # 使用计算出的size进行买入

                self.stop_loss_price = self.data_close[0] * (1 - self.params.stop_loss)
                self.stop_win_price =self.data_close[0] * (1 + self.params.stop_win)
        # 持仓时的卖出逻辑
        else:
            # # 止盈条件：boll超过上轨
            if self.data_high[0] >= self.top[0]:
                self.order = self.close()
            elif self.data_close[-1] >= self.mid[-1] and self.data_close[0] < self.mid[0] :
                self.order = self.close()
            #止盈条件，最高价
            # elif self.data_high[0]>= self.stop_win_price:
            #     self.order = self.close()
            # 止损条件：使用当日最低价判断
            elif self.data_low[0] <= self.stop_loss_price:
                self.order = self.close()
   

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单提交或接受时，不做操作
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"买入, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
            elif order.issell():
                self.log(f"卖出, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
            self.order = None  # 订单完成，重置订单状态

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")
            self.order = None  # 订单失败，重置订单状态
    def log(self, txt):
        """ 统一的日志记录方法 """
        dt = self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')


def getakdata():

    # 利用 AKShare 获取股票的后复权数据，这里只获取前 6 列
    #stock_hfq_df = ak.stock_zh_a_hist(symbol="600028", adjust="hfq")
    stock_hfq_df = ak.fund_etf_hist_em(symbol=510330, period="daily",adjust='hfq')
    # 处理字段命名，以符合 Backtrader 的要求
    print(stock_hfq_df)
    column_mapping = {
        "日期": "date",
        "股票代码": "symbol",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "换手率": "turnover"
    }

    # 重命名列
    stock_hfq_df.rename(columns=column_mapping, inplace=True)
    columns_to_keep = ["date", "open", "close", "high", "low", "volume"]
    stock_hfq_df = stock_hfq_df.loc[:, columns_to_keep]
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



def get30k():

    stock_hfq_df = ak.stock_zh_a_minute(symbol='sz001227', period='30', adjust="qfq")
    #print(stock_hfq_df)
    column_mapping = {
        "day": "date",
        "股票代码": "symbol",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "换手率": "turnover"
    }

    # 重命名列
    stock_hfq_df.rename(columns=column_mapping, inplace=True)
    columns_to_keep = ["date", "open", "close", "high", "low", "volume"]
    stock_hfq_df.index = pd.to_datetime(stock_hfq_df["date"])
    stock_hfq_df = stock_hfq_df.loc[:, columns_to_keep]
    # 确保日期列被解析为 datetime 类型
    # stock_hfq_df['datetime'] = pd.to_datetime(stock_hfq_df['datetime'])

    # 将数值列转换为浮点数或整数
    stock_hfq_df["open"] = pd.to_numeric(stock_hfq_df["open"], errors="coerce")
    stock_hfq_df["high"] = pd.to_numeric(stock_hfq_df["high"], errors="coerce")
    stock_hfq_df["low"] = pd.to_numeric(stock_hfq_df["low"], errors="coerce")
    stock_hfq_df["close"] = pd.to_numeric(stock_hfq_df["close"], errors="coerce")
    stock_hfq_df["volume"] = pd.to_numeric(stock_hfq_df["volume"], errors="coerce")
    print(stock_hfq_df)
    return stock_hfq_df
if __name__ == "__main__":
    cerebro = bt.Cerebro()  # 初始化回测系统
    start_date = datetime.datetime(2024, 2, 18)  # 回测开始时间
    end_date = datetime.datetime(2025, 2, 18)  # 回测结束时间

    # 假设 stock_hfq_df 是正确的 DataFrame


    stock_hfq_df = get30k()  # 获取样本数据

    data = bt.feeds.PandasData(
        dataname=stock_hfq_df, fromdate=start_date, todate=end_date
    )
    cerebro.adddata(data)  # 将数据传入回测系统
    cerebro.addstrategy(MyStrategy)  # 将交易策略加载到回测系统中
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name="pyfolio")  # 添加分析器

    start_cash = 1000000  # 设置初始资金
    cerebro.broker.setcash(start_cash)  # 设置初始资金
    cerebro.broker.setcommission(commission=0.0009)  # 设置手续费

    cerebro.addsizer(bt.sizers.PercentSizer, percents=90) 


    cerebro.addanalyzer(btanalyzers.SharpeRatio_A, _name="sharp")
    cerebro.addanalyzer(btanalyzers.AnnualReturn, _name="annualreturn")
    cerebro.addanalyzer(btanalyzers.Returns, _name="return")
    cerebro.addanalyzer(btanalyzers.SQN, _name="SQN")
    print("初始账户价值: %.2f" % cerebro.broker.getvalue())

    cerebro.run()
    print("最终账户价值: %.2f" % cerebro.broker.getvalue())
    

    cerebro.plot(style='candle', bar=True)

#     import matplotlib.dates as mdates
# # 如果需要自定义时间格式，可以使用以下代码
#     import matplotlib.pyplot as plt

#     # 获取当前的 figure 和 axis
#     fig, ax = plt.subplots()

#     # 设置时间格式
#     ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

#     # 显示图形
#     plt.show()