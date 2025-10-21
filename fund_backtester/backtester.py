# -*- coding: utf-8 -*-
"""
回测引擎模块 (已重构以支持DCA)
"""
import pandas as pd

def run_backtest(data: pd.DataFrame, initial_capital: float = 100000.0, commission_rate: float = 0.001, is_dca: bool = False, trade_amount: float = None):
    """
    执行回测。

    Args:
        data (pd.DataFrame): 包含 'close' 和 'signal' 列的数据.
        initial_capital (float): 初始资金.
        commission_rate (float): 交易手续费率.
        is_dca (bool): 是否为DCA策略。如果是, 'signal'列代表投资金额.
        trade_amount (float, optional): 每次交易的固定金额. 如果为 None, 则为全仓交易. Defaults to None.

    Returns:
        pd.DataFrame: 包含每日持仓和资产组合价值的 DataFrame.
        dict: 包含最终性能指标的字典.
        pd.DataFrame: 包含所有实际执行交易的详细日志.
    """
    trade_mode = "DCA" if is_dca else ("固定金额" if trade_amount else "全仓")
    print(f"开始执行回测模拟... (交易模式: {trade_mode})")
    
    trade_log_list = []
    portfolio = pd.DataFrame(index=data.index)
    portfolio['shares'] = 0.0  # 持有的基金份额
    portfolio['cash'] = initial_capital
    portfolio['holdings'] = 0.0  # 持有的基金份额价值
    portfolio['total'] = initial_capital
    
    for i in range(len(data)):
        current_price = data['close'].iloc[i]
        signal = data['signal'].iloc[i]
        
        # 继承前一天的持仓
        if i > 0:
            portfolio.loc[data.index[i], 'shares'] = portfolio['shares'].iloc[i-1]
            portfolio.loc[data.index[i], 'cash'] = portfolio['cash'].iloc[i-1]

        # --- 交易逻辑 ---
        # 卖出信号 (-1.0) 逻辑统一：对所有非DCA策略，卖出信号意味着清仓
        if not is_dca and signal == -1.0 and portfolio['shares'].iloc[i] > 0:
            shares_to_sell = portfolio['shares'].iloc[i]
            value_sold = shares_to_sell * current_price
            commission = value_sold * commission_rate
            cash_received = value_sold - commission
            portfolio.loc[data.index[i], 'cash'] += cash_received
            portfolio.loc[data.index[i], 'shares'] = 0
            print(f"{data.index[i].to_pydatetime().date()}: [{trade_mode}] 卖出信号. 价格: {current_price:.2f}, 清仓份额: {shares_to_sell:.2f}")
            log_entry = {
                'date': data.index[i], 'action': '卖出', 'price': current_price, 
                'shares': shares_to_sell, 'amount': cash_received
            }
            # Add extra info for threshold strategy
            if 'price_change_pct' in data.columns:
                log_entry['reference_nav'] = data['reference_nav'].iloc[i]
                log_entry['reference_date'] = data['reference_date'].iloc[i]
                log_entry['price_change_pct'] = data['price_change_pct'].iloc[i]
                log_entry['buy_threshold_pct'] = data['buy_threshold_pct'].iloc[i]
                log_entry['sell_threshold_pct'] = data['sell_threshold_pct'].iloc[i]
            trade_log_list.append(log_entry)

        # 买入信号逻辑
        elif is_dca: # DCA 模式 (定期定额买入)
            if signal > 0 and portfolio['cash'].iloc[i] >= signal:
                cash_to_use = signal
                commission = cash_to_use * commission_rate
                shares_to_buy = (cash_to_use - commission) / current_price
                portfolio.loc[data.index[i], 'shares'] += shares_to_buy
                portfolio.loc[data.index[i], 'cash'] -= cash_to_use
                print(f"{data.index[i].to_pydatetime().date()}: [DCA] 定投信号. 价格: {current_price:.2f}, 投资金额: {cash_to_use:.2f}")
                log_entry = {
                    'date': data.index[i], 'action': '买入', 'price': current_price,
                    'shares': shares_to_buy, 'amount': cash_to_use
                }
                if 'price_change_pct' in data.columns:
                    log_entry['reference_nav'] = data['reference_nav'].iloc[i]
                    log_entry['reference_date'] = data['reference_date'].iloc[i]
                    log_entry['price_change_pct'] = data['price_change_pct'].iloc[i]
                    log_entry['buy_threshold_pct'] = data['buy_threshold_pct'].iloc[i]
                    log_entry['sell_threshold_pct'] = data['sell_threshold_pct'].iloc[i]
                trade_log_list.append(log_entry)
        
        elif trade_amount: # 固定金额交易模式 (非DCA)
            if signal == 1.0 and portfolio['cash'].iloc[i] >= trade_amount:
                cash_to_use = trade_amount
                commission = cash_to_use * commission_rate
                shares_to_buy = (cash_to_use - commission) / current_price
                portfolio.loc[data.index[i], 'shares'] += shares_to_buy
                portfolio.loc[data.index[i], 'cash'] -= cash_to_use
                print(f"{data.index[i].to_pydatetime().date()}: [固定金额] 买入信号. 价格: {current_price:.2f}, 投资金额: {cash_to_use:.2f}")
                log_entry = {
                    'date': data.index[i], 'action': '买入', 'price': current_price,
                    'shares': shares_to_buy, 'amount': cash_to_use
                }
                if 'price_change_pct' in data.columns:
                    log_entry['reference_nav'] = data['reference_nav'].iloc[i]
                    log_entry['reference_date'] = data['reference_date'].iloc[i]
                    log_entry['price_change_pct'] = data['price_change_pct'].iloc[i]
                    log_entry['buy_threshold_pct'] = data['buy_threshold_pct'].iloc[i]
                    log_entry['sell_threshold_pct'] = data['sell_threshold_pct'].iloc[i]
                trade_log_list.append(log_entry)

        elif not trade_amount and not is_dca: # 全仓交易模式 (非DCA)
            if signal == 1.0 and portfolio['cash'].iloc[i] > 0:
                cash_to_use = portfolio['cash'].iloc[i]
                commission = cash_to_use * commission_rate
                shares_to_buy = (cash_to_use - commission) / current_price
                # 在全仓模式下，买入即替换现有份额
                portfolio.loc[data.index[i], 'shares'] = shares_to_buy
                portfolio.loc[data.index[i], 'cash'] = 0
                print(f"{data.index[i].to_pydatetime().date()}: [全仓] 买入信号. 价格: {current_price:.2f}, 动用资金: {cash_to_use:.2f}")
                
                # 修正：为全仓买入模式添加完整的日志记录逻辑
                log_entry = {
                    'date': data.index[i], 'action': '买入', 'price': current_price,
                    'shares': shares_to_buy, 'amount': cash_to_use
                }
                if 'price_change_pct' in data.columns:
                    log_entry['reference_nav'] = data['reference_nav'].iloc[i]
                    log_entry['reference_date'] = data['reference_date'].iloc[i]
                    log_entry['price_change_pct'] = data['price_change_pct'].iloc[i]
                    log_entry['buy_threshold_pct'] = data['buy_threshold_pct'].iloc[i]
                    log_entry['sell_threshold_pct'] = data['sell_threshold_pct'].iloc[i]
                
                trade_log_list.append(log_entry)

        # --- 每日更新资产 ---
        portfolio.loc[data.index[i], 'holdings'] = portfolio['shares'].iloc[i] * current_price
        portfolio.loc[data.index[i], 'total'] = portfolio['holdings'].iloc[i] + portfolio['cash'].iloc[i]

    # --- 最终结算 ---
    # 对于DCA策略，在回测最后一天卖出所有持仓以计算最终收益
    if is_dca and portfolio['shares'].iloc[-1] > 0:
        final_price = data['close'].iloc[-1]
        shares_to_sell = portfolio['shares'].iloc[-1]
        value_sold = shares_to_sell * final_price
        commission = value_sold * commission_rate
        final_cash = portfolio['cash'].iloc[-1] + value_sold - commission
        portfolio.loc[data.index[-1], 'cash'] = final_cash
        portfolio.loc[data.index[-1], 'holdings'] = 0
        portfolio.loc[data.index[-1], 'total'] = final_cash
        print(f"{data.index[-1].to_pydatetime().date()}: [DCA] 期末清仓. 价格: {final_price:.2f}")

    final_total = portfolio['total'].iloc[-1]
    total_return = (final_total / initial_capital) - 1
    benchmark_return = (data['close'].iloc[-1] / data['close'].iloc[0]) - 1

    performance = {
        'initial_capital': initial_capital,
        'final_portfolio_value': final_total,
        'total_return': total_return,
        'benchmark_return': benchmark_return,
    }
    
    trade_log = pd.DataFrame(trade_log_list)
    if not trade_log.empty:
        # 确保 date 列是 datetime 类型，不再将其设置为索引
        trade_log['date'] = pd.to_datetime(trade_log['date'])

    print("回测模拟执行完毕。")
    return portfolio, performance, trade_log