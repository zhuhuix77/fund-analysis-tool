"""
基金回测分析程序演示
"""

from fund_backtest import FundDataDownloader, FundBacktester, FundAnalyzer
import matplotlib.pyplot as plt

def demo_fund_analysis():
    """演示基金分析功能"""
    print("🚀 基金回测分析程序演示")
    print("=" * 50)
    
    # 演示基金代码列表
    demo_funds = {
        "000001": "华夏成长混合",
        "110022": "易方达消费行业",
        "161725": "招商中证白酒指数",
        "320007": "诺安成长混合"
    }
    
    print("可选择的演示基金:")
    for code, name in demo_funds.items():
        print(f"  {code}: {name}")
    
    # 让用户选择基金或使用默认
    fund_code = input("\n请输入基金代码 (直接回车使用 000001): ").strip()
    if not fund_code:
        fund_code = "000001"
    
    fund_name = demo_funds.get(fund_code, "未知基金")
    print(f"\n📊 正在分析基金: {fund_code} ({fund_name})")
    
    try:
        # 1. 数据下载
        print("\n1️⃣ 正在下载基金数据...")
        downloader = FundDataDownloader()
        
        # 获取基金信息
        fund_info = downloader.get_fund_info(fund_code)
        if fund_info:
            print(f"   基金名称: {fund_info.get('name', fund_name)}")
            print(f"   当前净值: {fund_info.get('gsz', 'N/A')}")
        
        # 获取历史数据 (最近1年)
        fund_data = downloader.get_fund_history(fund_code, "2023-01-01", "2024-01-01")
        
        if fund_data.empty:
            print("❌ 无法获取基金数据")
            return
        
        print(f"   ✅ 成功获取 {len(fund_data)} 天的历史数据")
        print(f"   📅 数据期间: {fund_data['date'].iloc[0].strftime('%Y-%m-%d')} 至 {fund_data['date'].iloc[-1].strftime('%Y-%m-%d')}")
        
        # 2. 回测分析
        print("\n2️⃣ 正在进行回测分析...")
        backtester = FundBacktester(fund_data)
        metrics = backtester.calculate_metrics()
        
        print("   ✅ 回测分析完成")
        
        # 3. 投资策略模拟
        print("\n3️⃣ 正在模拟投资策略...")
        initial_investment = 10000  # 1万元初始投资
        
        # 一次性投资
        lump_sum_data = backtester.simulate_investment(initial_investment, 'lump_sum')
        lump_sum_final = lump_sum_data['portfolio_value'].iloc[-1]
        lump_sum_return = (lump_sum_final / initial_investment - 1) * 100
        
        # 定投策略
        dca_data = backtester.simulate_investment(initial_investment, 'dca')
        dca_final = dca_data['portfolio_value'].iloc[-1]
        dca_return = (dca_final / initial_investment - 1) * 100
        
        print(f"   💰 一次性投资收益: {lump_sum_return:.2f}% (最终价值: {lump_sum_final:.2f}元)")
        print(f"   📈 定投策略收益: {dca_return:.2f}% (最终价值: {dca_final:.2f}元)")
        
        # 4. 生成分析报告
        print("\n4️⃣ 生成分析报告...")
        analyzer = FundAnalyzer(fund_code, fund_data, metrics)
        analyzer.print_analysis_report()
        
        # 5. 图形化分析
        print("\n5️⃣ 正在生成图表...")
        print("   📊 综合分析图表...")
        analyzer.plot_comprehensive_analysis()
        
        print("   📈 投资策略对比图表...")
        analyzer.plot_investment_comparison(lump_sum_data)
        
        # 6. 额外的风险分析
        print("\n6️⃣ 风险分析...")
        returns = fund_data['nav'].pct_change().dropna()
        
        # VaR分析
        var_95 = returns.quantile(0.05) * 100
        var_99 = returns.quantile(0.01) * 100
        
        # 连续亏损分析
        negative_returns = returns < 0
        max_consecutive_losses = 0
        current_losses = 0
        
        for is_loss in negative_returns:
            if is_loss:
                current_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_losses = 0
        
        print(f"   📉 VaR (95%置信度): {var_95:.2f}%")
        print(f"   📉 VaR (99%置信度): {var_99:.2f}%")
        print(f"   ⚠️  最长连续亏损天数: {max_consecutive_losses} 天")
        
        print("\n✅ 分析完成！")
        print("\n💡 温馨提示:")
        print("   - 以上分析结果仅供参考，不构成投资建议")
        print("   - 投资有风险，入市需谨慎")
        print("   - 历史表现不代表未来收益")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        print("💡 这可能是由于网络连接问题或数据源暂时不可用")

def demo_multiple_funds():
    """演示多基金对比"""
    print("\n🔄 多基金对比分析演示")
    print("=" * 50)
    
    # 预设的基金组合
    fund_portfolio = {
        "000001": "华夏成长混合",
        "110022": "易方达消费行业", 
        "161725": "招商中证白酒指数"
    }
    
    print("正在对比以下基金:")
    for code, name in fund_portfolio.items():
        print(f"  📊 {code}: {name}")
    
    downloader = FundDataDownloader()
    results = {}
    
    for fund_code, fund_name in fund_portfolio.items():
        try:
            print(f"\n正在分析 {fund_name} ({fund_code})...")
            fund_data = downloader.get_fund_history(fund_code, "2023-01-01", "2024-01-01")
            
            if not fund_data.empty:
                backtester = FundBacktester(fund_data)
                metrics = backtester.calculate_metrics()
                results[fund_name] = metrics
                print(f"  ✅ {fund_name} 分析完成")
            else:
                print(f"  ❌ {fund_name} 数据获取失败")
                
        except Exception as e:
            print(f"  ❌ {fund_name} 分析出错: {e}")
    
    if results:
        print("\n📊 基金对比结果:")
        print("=" * 80)
        
        # 创建对比表格
        import pandas as pd
        comparison_df = pd.DataFrame(results).T
        print(comparison_df.round(2).to_string())
        
        # 找出最佳表现
        if len(results) > 1:
            print("\n🏆 最佳表现:")
            best_return = comparison_df['年化收益率(%)'].idxmax()
            best_sharpe = comparison_df['夏普比率'].idxmax()
            lowest_risk = comparison_df['年化波动率(%)'].idxmin()
            
            print(f"  📈 最高年化收益率: {best_return}")
            print(f"  ⚖️  最佳夏普比率: {best_sharpe}")
            print(f"  🛡️  最低波动率: {lowest_risk}")

if __name__ == "__main__":
    print("🎯 基金回测分析程序 - 完整演示")
    print("=" * 60)
    
    # 主演示
    demo_fund_analysis()
    
    # 询问是否进行多基金对比
    if input("\n是否进行多基金对比分析？(y/n): ").lower().startswith('y'):
        demo_multiple_funds()
    
    print("\n🎉 演示结束，感谢使用！")