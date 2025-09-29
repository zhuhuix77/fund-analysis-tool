"""
基金回测分析程序使用示例
演示如何使用各个模块进行基金分析
"""

from fund_backtest import FundDataDownloader, FundBacktester, FundAnalyzer
from datetime import datetime, timedelta
import pandas as pd

def example_single_fund_analysis():
    """单个基金分析示例"""
    print("=== 单个基金分析示例 ===")
    
    # 设置分析参数
    fund_code = "000001"  # 华夏成长混合
    start_date = "2023-01-01"
    end_date = "2024-01-01"
    
    print(f"分析基金: {fund_code}")
    print(f"分析期间: {start_date} 到 {end_date}")
    
    # 1. 下载数据
    downloader = FundDataDownloader()
    fund_info = downloader.get_fund_info(fund_code)
    fund_data = downloader.get_fund_history(fund_code, start_date, end_date)
    
    if fund_info:
        print(f"基金名称: {fund_info.get('name', '未知')}")
    
    # 2. 回测分析
    backtester = FundBacktester(fund_data)
    metrics = backtester.calculate_metrics()
    
    # 3. 投资模拟
    lump_sum_data = backtester.simulate_investment(10000, 'lump_sum')
    dca_data = backtester.simulate_investment(10000, 'dca')
    
    # 4. 结果展示
    analyzer = FundAnalyzer(fund_code, fund_data, metrics)
    analyzer.print_analysis_report()
    
    # 比较两种投资策略
    print("\n投资策略对比:")
    print("-" * 30)
    lump_sum_return = (lump_sum_data['portfolio_value'].iloc[-1] / 10000 - 1) * 100
    dca_return = (dca_data['portfolio_value'].iloc[-1] / 10000 - 1) * 100
    
    print(f"一次性投资收益率: {lump_sum_return:.2f}%")
    print(f"定投策略收益率: {dca_return:.2f}%")
    
    return fund_data, metrics

def example_multiple_funds_comparison():
    """多基金对比分析示例"""
    print("\n=== 多基金对比分析示例 ===")
    
    # 要对比的基金列表
    fund_codes = ["000001", "110022", "161725"]
    fund_names = ["华夏成长", "易方达消费", "招商中证白酒"]
    
    results = {}
    
    downloader = FundDataDownloader()
    
    for i, fund_code in enumerate(fund_codes):
        print(f"\n分析基金 {i+1}: {fund_code} ({fund_names[i]})")
        
        # 获取数据
        fund_data = downloader.get_fund_history(fund_code, "2023-01-01", "2024-01-01")
        
        if not fund_data.empty:
            # 回测分析
            backtester = FundBacktester(fund_data)
            metrics = backtester.calculate_metrics()
            
            results[fund_names[i]] = metrics
    
    # 对比结果
    if results:
        print("\n基金对比结果:")
        print("=" * 80)
        
        # 创建对比表格
        comparison_df = pd.DataFrame(results).T
        print(comparison_df.to_string())
        
        # 找出最佳基金
        best_return = comparison_df['年化收益率(%)'].idxmax()
        best_sharpe = comparison_df['夏普比率'].idxmax()
        lowest_risk = comparison_df['年化波动率(%)'].idxmin()
        
        print(f"\n最佳收益: {best_return}")
        print(f"最佳夏普比率: {best_sharpe}")
        print(f"最低风险: {lowest_risk}")

def example_custom_analysis():
    """自定义分析示例"""
    print("\n=== 自定义分析示例 ===")
    
    # 自定义分析函数
    def calculate_custom_metrics(fund_data):
        """计算自定义指标"""
        returns = fund_data['nav'].pct_change().dropna()
        
        # VaR (Value at Risk) - 95%置信度
        var_95 = returns.quantile(0.05) * 100
        
        # 连续上涨/下跌天数
        returns_sign = (returns > 0).astype(int)
        consecutive_wins = 0
        consecutive_losses = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for ret in returns_sign:
            if ret == 1:
                current_win_streak += 1
                current_loss_streak = 0
                consecutive_wins = max(consecutive_wins, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                consecutive_losses = max(consecutive_losses, current_loss_streak)
        
        return {
            'VaR_95%': round(var_95, 2),
            '最长连涨天数': consecutive_wins,
            '最长连跌天数': consecutive_losses,
            '平均日收益率(%)': round(returns.mean() * 100, 4),
            '收益率偏度': round(returns.skew(), 2),
            '收益率峰度': round(returns.kurtosis(), 2)
        }
    
    # 分析示例基金
    fund_code = "000001"
    downloader = FundDataDownloader()
    fund_data = downloader.get_fund_history(fund_code, "2023-01-01")
    
    if not fund_data.empty:
        custom_metrics = calculate_custom_metrics(fund_data)
        
        print("自定义分析指标:")
        print("-" * 30)
        for key, value in custom_metrics.items():
            print(f"{key}: {value}")

def example_risk_analysis():
    """风险分析示例"""
    print("\n=== 风险分析示例 ===")
    
    fund_code = "000001"
    downloader = FundDataDownloader()
    fund_data = downloader.get_fund_history(fund_code, "2022-01-01")
    
    if not fund_data.empty:
        returns = fund_data['nav'].pct_change().dropna()
        
        # 不同置信度的VaR
        var_90 = returns.quantile(0.10) * 100
        var_95 = returns.quantile(0.05) * 100
        var_99 = returns.quantile(0.01) * 100
        
        # 条件VaR (CVaR)
        cvar_95 = returns[returns <= returns.quantile(0.05)].mean() * 100
        
        # 下行风险
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * (252**0.5) * 100
        
        print("风险分析结果:")
        print("-" * 30)
        print(f"VaR (90%): {var_90:.2f}%")
        print(f"VaR (95%): {var_95:.2f}%")
        print(f"VaR (99%): {var_99:.2f}%")
        print(f"CVaR (95%): {cvar_95:.2f}%")
        print(f"下行偏差: {downside_deviation:.2f}%")
        print(f"负收益天数占比: {(len(downside_returns)/len(returns)*100):.1f}%")

if __name__ == "__main__":
    print("基金回测分析程序 - 使用示例")
    print("=" * 50)
    
    # 运行各种示例
    try:
        # 1. 单个基金分析
        example_single_fund_analysis()
        
        # 2. 多基金对比
        example_multiple_funds_comparison()
        
        # 3. 自定义分析
        example_custom_analysis()
        
        # 4. 风险分析
        example_risk_analysis()
        
        print("\n所有示例运行完成！")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
        print("请确保已安装所需依赖包")