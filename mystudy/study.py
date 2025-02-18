import backtrader as bt
import datetime
import akshare as ak
import backtrader.analyzers as btanalyzers


class MyStrategy(bt.Strategy):
    """
    主策略程序
    """

    params = (("maperiod", 5),)

    def __init__(self):
        """
        初始化函数
        """
        self.data_close = self.datas[0].close  # 指定价格序列
        self.order = None  # 初始化交易指令
        self.buy_price = None
        self.buy_comm = None

        # 添加移动均线指标
        self.rsi12 = bt.indicators.RSI(self.data_close, period=12)
        self.rsi6 = bt.indicators.RSI(self.data_close, period=6)

    def next(self):
        """
        执行逻辑
        """
        if self.order:  # 检查是否有未完成订单
            return

        if not self.position:  # 没有持仓
            # 判断 RSI6 上穿 RSI12
            if self.rsi6[0] > self.rsi12[0] and self.rsi6[-1] <= self.rsi12[-1]:
                self.buy_price = self.data_close[0]
                self.stop_loss_price = self.buy_price * 0.98  # 设置止损价格
                self.order = self.buy()  # 执行买入
                print(
                    f"Buy at price: {self.data_close[0]}, stop loss: {self.stop_loss_price}"
                )
        else:
            # 卖出条件 1: RSI12 > 70
            if self.rsi12[0] > 70:
                self.order = self.sell()  # 执行卖出
                print(f"Sell at price: {self.data_close[0]} (RSI12 >70)")
            # 卖出条件 2: 触发止损
            elif self.data_close[0] <= self.stop_loss_price:
                self.order = self.sell()  # 执行卖出
                print(f"Sell at price: {self.data_close[0]} (stop loss hit)")

        if self.order:
            self.order = None  # 更新订单状态


def getakdata():

    # 利用 AKShare 获取股票的后复权数据，这里只获取前 6 列
    stock_hfq_df = ak.stock_zh_a_hist(symbol="600028", adjust="hfq").iloc[:, :6]
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
    cerebro = bt.Cerebro()  # 初始化回测系统
    start_date = datetime.datetime(2024, 2, 18)  # 回测开始时间
    end_date = datetime.datetime(2025, 2, 18)  # 回测结束时间

    # 假设 stock_hfq_df 是正确的 DataFrame
    import pandas as pd

    stock_hfq_df = getakdata()  # 获取样本数据

    data = bt.feeds.PandasData(
        dataname=stock_hfq_df, fromdate=start_date, todate=end_date
    )
    cerebro.adddata(data)  # 将数据传入回测系统
    cerebro.addstrategy(MyStrategy)  # 将交易策略加载到回测系统中
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name="pyfolio")  # 添加分析器

    start_cash = 100000  # 设置初始资金
    cerebro.broker.setcash(start_cash)  # 设置初始资金
    cerebro.broker.setcommission(commission=0.002)  # 设置手续费

    print("初始账户价值: %.2f" % cerebro.broker.getvalue())
    result = cerebro.run()  # 运行回测系统
    print("最终账户价值: %.2f" % cerebro.broker.getvalue())

    cerebro.addanalyzer(btanalyzers.SharpeRatio_A, _name="sharp")
    cerebro.addanalyzer(btanalyzers.AnnualReturn, _name="annualreturn")
    cerebro.addanalyzer(btanalyzers.Returns, _name="return")
    cerebro.addanalyzer(btanalyzers.SQN, _name="SQN")

    cerebro.run()

    cerebro.plot()
