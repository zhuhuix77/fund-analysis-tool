# -*- coding: utf-8 -*-
"""
回测系统主入口
"""
import config
import data_manager
import strategy
import backtester # 导入回测引擎

def run_backtest():
    """
    主回测流程
    """
    print("开始执行回测任务...")
    
    # 1. 从配置中获取目标基金列表
    funds_to_backtest = config.TARGET_FUNDS
    
    # 2. 遍历每支基金，获取其历史数据
    for fund_code in funds_to_backtest:
        print(f"\n---------- 处理基金: {fund_code} ----------")
        fund_history = data_manager.get_fund_history(
            fund_code=fund_code,
            start_date=config.BACKTEST_START_DATE,
            end_date=config.BACKTEST_END_DATE
        )
        
        if fund_history.empty:
            print(f"未能获取基金 {fund_code} 的数据，跳过。")
            continue
            
        print(f"成功获取基金 {fund_code} 的历史数据。")
        
        # 3. 应用策略生成交易信号
        print("\n应用均线交叉策略...")
        strategy_data = strategy.ma_crossover_strategy(fund_history)
        
        # 4. 执行回测
        portfolio, performance = backtester.run_backtest(strategy_data)
        
        # 5. 打印最终回测结果
        print("\n---------- 回测结果 ----------")
        print(f"初始资金: {performance['initial_capital']:,.2f} 元")
        print(f"最终资产: {performance['final_portfolio_value']:,.2f} 元")
        print(f"策略总收益率: {performance['total_return']:.2%}")
        print(f"基准总收益率 (买入并持有): {performance['benchmark_return']:.2%}")
        print("------------------------------")
        
    print("\n所有回测任务执行完毕。")

if __name__ == "__main__":
    run_backtest()