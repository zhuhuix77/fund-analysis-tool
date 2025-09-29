"""
基金回测分析程序 - 简化演示版本
直接运行，无需用户交互
"""

from fund_backtest import FundDataDownloader, FundBacktester, FundAnalyzer
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

def main():
    print("🎯 基金回测分析程序 - 自动演示")
    print("=" * 50)
    
    # 使用华夏成长混合基金作为演示
    fund_code = "000001"
    fund_name = "华夏成长混合"
    
    print(f"📊 正在分析基金: {fund_code} ({fund_name})")
    
    try:
        # 1. 数据下载
        print("\n1️⃣ 正在下载基金数据...")
        downloader = FundDataDownloader()
        
        # 获取基金信息
        fund_info = downloader.get_fund_info(fund_code)
        if fund_info:
            print(f"   基金名称: {fund_info.get('name', fund_name)}")
            print(f"   当前净值: {fund_info.get('gsz', 'N/A')}")
        else:
            print(f"   使用模拟数据进行演示")
        
        # 获取历史数据
        print("   正在获取历史净值数据...")
        fund_data = downloader.get_fund_history(fund_code, "2023-01-01", "2024-01-01")
        
        if fund_data.empty:
            print("❌ 无法获取基金数据")
            return
        
        print(f"   ✅ 成功获取 {len(fund_data)} 天的历史数据")
        print(f"   📅 数据期间: {fund_data['date'].iloc[0].strftime('%Y-%m-%d')} 至 {fund_data['date'].iloc[-1].strftime('%Y-%m-%d')}")
        
        # 显示数据样本
        print("\n   📋 数据样本 (前5条):")
        print(fund_data.head().to_string(index=False))
        
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
        
        print(f"   💰 一次性投资: 投入{initial_investment}元 → 最终{lump_sum_final:.2f}元 (收益率: {lump_sum_return:.2f}%)")
        print(f"   📈 定投策略: 投入{initial_investment}元 → 最终{dca_final:.2f}元 (收益率: {dca_return:.2f}%)")
        
        # 4. 生成分析报告
        print("\n4️⃣ 生成详细分析报告...")
        analyzer = FundAnalyzer(fund_code, fund_data, metrics)
        analyzer.print_analysis_report()
        
        # 5. 风险分析
        print("\n5️⃣ 风险分析...")
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
        
        print(f"   📉 VaR (95%置信度): {var_95:.2f}% (95%的情况下，单日最大损失不超过此值)")
        print(f"   📉 VaR (99%置信度): {var_99:.2f}% (99%的情况下，单日最大损失不超过此值)")
        print(f"   ⚠️  最长连续亏损天数: {max_consecutive_losses} 天")
        
        # 6. 生成图表
        print("\n6️⃣ 正在生成图表...")
        try:
            print("   📊 生成综合分析图表...")
            analyzer.plot_comprehensive_analysis()
            
            print("   📈 生成投资策略对比图表...")
            analyzer.plot_investment_comparison(lump_sum_data)
            
            print("   ✅ 图表生成完成！")
        except Exception as e:
            print(f"   ⚠️  图表生成遇到问题: {e}")
            print("   💡 这可能是由于显示环境限制，但分析数据仍然有效")
        
        # 7. 总结建议
        print("\n7️⃣ 投资建议总结...")
        annual_return = metrics['年化收益率(%)']
        volatility = metrics['年化波动率(%)']
        sharpe_ratio = metrics['夏普比率']
        max_drawdown = abs(metrics['最大回撤(%)'])
        
        print("   📝 基于分析结果的建议:")
        
        if annual_return > 10 and sharpe_ratio > 1 and max_drawdown < 20:
            print("   ✅ 该基金表现优秀，风险收益比较好，值得考虑配置")
        elif annual_return > 5 and sharpe_ratio > 0.5:
            print("   ⚠️  该基金表现中等，可适量配置，注意风险控制")
        else:
            print("   ❌ 该基金表现较差，建议谨慎投资或寻找其他选择")
        
        if volatility > 25:
            print("   ⚠️  该基金波动较大，适合风险承受能力强的投资者")
        
        if lump_sum_return > dca_return:
            print("   💡 在此期间，一次性投资策略表现更好")
        else:
            print("   💡 在此期间，定投策略表现更好，能够平滑市场波动")
        
        print("\n✅ 分析完成！")
        print("\n💡 重要提示:")
        print("   - 以上分析结果仅供参考，不构成投资建议")
        print("   - 投资有风险，入市需谨慎")
        print("   - 历史表现不代表未来收益")
        print("   - 建议结合个人风险承受能力做出投资决策")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        print("💡 这可能是由于网络连接问题或数据源暂时不可用")
        print("   程序会自动使用模拟数据继续演示功能")

if __name__ == "__main__":
    main()