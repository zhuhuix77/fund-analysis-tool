"""
基金回测分析程序 - 阈值策略演示
展示买入阈值、卖出阈值和回顾期功能
"""

from fund_backtest import FundDataDownloader, FundBacktester, FundAnalyzer
import matplotlib.pyplot as plt
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def demo_threshold_strategy():
    """演示阈值策略"""
    print("🎯 基金阈值策略回测演示")
    print("=" * 60)
    
    # 使用华夏成长混合基金作为演示
    fund_code = "000001"
    fund_name = "华夏成长混合"
    
    print(f"📊 分析基金: {fund_code} ({fund_name})")
    
    try:
        # 1. 下载数据
        print("\n1️⃣ 正在下载基金数据...")
        downloader = FundDataDownloader()
        
        # 获取基金信息
        fund_info = downloader.get_fund_info(fund_code)
        if fund_info:
            print(f"   基金名称: {fund_info.get('name', fund_name)}")
            print(f"   当前净值: {fund_info.get('gsz', 'N/A')}")
        
        # 获取历史数据（2年数据以便更好展示阈值策略）
        fund_data = downloader.get_fund_history(fund_code, "2022-01-01", "2024-01-01")
        
        if fund_data.empty:
            print("❌ 无法获取基金数据")
            return
        
        print(f"   ✅ 成功获取 {len(fund_data)} 天的历史数据")
        print(f"   📅 数据期间: {fund_data['date'].iloc[0].strftime('%Y-%m-%d')} 至 {fund_data['date'].iloc[-1].strftime('%Y-%m-%d')}")
        
        # 2. 回测分析
        print("\n2️⃣ 正在进行回测分析...")
        backtester = FundBacktester(fund_data)
        metrics = backtester.calculate_metrics()
        
        print("   ✅ 基础回测分析完成")
        
        # 3. 策略参数设置
        print("\n3️⃣ 阈值策略参数设置...")
        initial_investment = 50000  # 5万元初始资金
        
        # 策略参数
        strategies = {
            "保守策略": {
                "buy_threshold": -8,    # 跌8%买入
                "sell_threshold": 15,   # 涨15%卖出
                "lookback_period": 30   # 30天回顾期
            },
            "积极策略": {
                "buy_threshold": -5,    # 跌5%买入
                "sell_threshold": 10,   # 涨10%卖出
                "lookback_period": 20   # 20天回顾期
            },
            "激进策略": {
                "buy_threshold": -3,    # 跌3%买入
                "sell_threshold": 8,    # 涨8%卖出
                "lookback_period": 15   # 15天回顾期
            }
        }
        
        print("   策略参数:")
        for name, params in strategies.items():
            print(f"   📈 {name}: 买入阈值{params['buy_threshold']}%, 卖出阈值+{params['sell_threshold']}%, 回顾期{params['lookback_period']}天")
        
        # 4. 运行不同策略
        print("\n4️⃣ 正在运行不同投资策略...")
        
        results = {}
        
        # 基准策略：一次性投资
        print("   🔹 运行基准策略（一次性投资）...")
        lump_sum_data = backtester.simulate_investment(initial_investment, 'lump_sum')
        lump_sum_return = (lump_sum_data['portfolio_value'].iloc[-1] / initial_investment - 1) * 100
        results["一次性投资"] = {
            "final_value": lump_sum_data['portfolio_value'].iloc[-1],
            "return_rate": lump_sum_return,
            "data": lump_sum_data
        }
        
        # 定投策略
        print("   🔹 运行定投策略...")
        dca_data = backtester.simulate_investment(initial_investment, 'dca')
        dca_return = (dca_data['portfolio_value'].iloc[-1] / initial_investment - 1) * 100
        results["定投策略"] = {
            "final_value": dca_data['portfolio_value'].iloc[-1],
            "return_rate": dca_return,
            "data": dca_data
        }
        
        # 阈值策略
        for strategy_name, params in strategies.items():
            print(f"   🔹 运行{strategy_name}...")
            threshold_data = backtester.simulate_investment(
                initial_investment, 
                'threshold',
                buy_threshold=params['buy_threshold'],
                sell_threshold=params['sell_threshold'],
                lookback_period=params['lookback_period']
            )
            threshold_return = (threshold_data['portfolio_value'].iloc[-1] / initial_investment - 1) * 100
            
            # 统计交易次数
            buy_count = len(threshold_data[threshold_data['action'] == 'buy'])
            sell_count = len(threshold_data[threshold_data['action'] == 'sell'])
            
            results[strategy_name] = {
                "final_value": threshold_data['portfolio_value'].iloc[-1],
                "return_rate": threshold_return,
                "buy_count": buy_count,
                "sell_count": sell_count,
                "data": threshold_data,
                "params": params
            }
        
        # 5. 结果对比
        print("\n5️⃣ 策略结果对比...")
        print("=" * 80)
        print(f"{'策略名称':<12} {'最终价值(元)':<12} {'收益率(%)':<10} {'买入次数':<8} {'卖出次数':<8}")
        print("-" * 80)
        
        for strategy_name, result in results.items():
            buy_count = result.get('buy_count', '-')
            sell_count = result.get('sell_count', '-')
            print(f"{strategy_name:<12} {result['final_value']:<12.2f} {result['return_rate']:<10.2f} {buy_count:<8} {sell_count:<8}")
        
        # 找出最佳策略
        best_strategy = max(results.keys(), key=lambda x: results[x]['return_rate'])
        print(f"\n🏆 最佳策略: {best_strategy} (收益率: {results[best_strategy]['return_rate']:.2f}%)")
        
        # 6. 详细分析最佳阈值策略
        if best_strategy in strategies:
            print(f"\n6️⃣ {best_strategy}详细分析...")
            best_data = results[best_strategy]['data']
            best_params = results[best_strategy]['params']
            
            print(f"   策略参数:")
            print(f"   - 买入阈值: {best_params['buy_threshold']}% (回顾期内跌幅达到此值时买入)")
            print(f"   - 卖出阈值: +{best_params['sell_threshold']}% (回顾期内涨幅达到此值时卖出)")
            print(f"   - 回顾期: {best_params['lookback_period']}天")
            
            print(f"\n   交易统计:")
            print(f"   - 总买入次数: {results[best_strategy]['buy_count']} 次")
            print(f"   - 总卖出次数: {results[best_strategy]['sell_count']} 次")
            print(f"   - 最终现金: {best_data['cash'].iloc[-1]:.2f} 元")
            print(f"   - 最终持仓: {best_data['shares'].iloc[-1]:.2f} 份")
            
            # 分析买卖点
            buy_points = best_data[best_data['action'] == 'buy']
            sell_points = best_data[best_data['action'] == 'sell']
            
            if not buy_points.empty:
                avg_buy_return = buy_points['lookback_return'].mean()
                print(f"   - 平均买入时回顾期收益率: {avg_buy_return:.2f}%")
            
            if not sell_points.empty:
                avg_sell_return = sell_points['lookback_return'].mean()
                print(f"   - 平均卖出时回顾期收益率: {avg_sell_return:.2f}%")
        
        # 7. 生成图表
        print("\n7️⃣ 正在生成对比图表...")
        
        # 创建策略对比图
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'基金 {fund_code} 阈值策略回测对比', fontsize=16, fontweight='bold')
        
        # 1. 投资组合价值对比
        ax1 = axes[0, 0]
        for strategy_name, result in results.items():
            data = result['data']
            ax1.plot(data['date'], data['portfolio_value'], 
                    linewidth=2, label=strategy_name, alpha=0.8)
        
        ax1.set_title('投资组合价值对比', fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('价值 (元)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # 2. 最佳阈值策略买卖点
        ax2 = axes[0, 1]
        if best_strategy in strategies:
            best_data = results[best_strategy]['data']
            ax2.plot(best_data['date'], best_data['portfolio_value'], 
                    linewidth=2, color='blue', label='组合价值')
            
            buy_points = best_data[best_data['action'] == 'buy']
            sell_points = best_data[best_data['action'] == 'sell']
            
            if not buy_points.empty:
                ax2.scatter(buy_points['date'], buy_points['portfolio_value'], 
                           color='green', marker='^', s=50, label='买入点', zorder=5)
            if not sell_points.empty:
                ax2.scatter(sell_points['date'], sell_points['portfolio_value'], 
                           color='red', marker='v', s=50, label='卖出点', zorder=5)
            
            ax2.set_title(f'{best_strategy} - 买卖点分析', fontweight='bold')
            ax2.set_xlabel('日期')
            ax2.set_ylabel('价值 (元)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        
        # 3. 收益率对比柱状图
        ax3 = axes[1, 0]
        strategy_names = list(results.keys())
        returns = [results[name]['return_rate'] for name in strategy_names]
        colors = ['skyblue' if name != best_strategy else 'gold' for name in strategy_names]
        
        bars = ax3.bar(strategy_names, returns, color=colors, alpha=0.7)
        ax3.set_title('策略收益率对比', fontweight='bold')
        ax3.set_ylabel('收益率 (%)')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 在柱状图上显示数值
        for bar, return_rate in zip(bars, returns):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{return_rate:.1f}%', ha='center', va='bottom')
        
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        
        # 4. 现金和持仓变化（最佳阈值策略）
        ax4 = axes[1, 1]
        if best_strategy in strategies:
            best_data = results[best_strategy]['data']
            ax4_twin = ax4.twinx()
            
            line1 = ax4.plot(best_data['date'], best_data['cash'], 
                           color='green', linewidth=2, label='现金余额')
            line2 = ax4_twin.plot(best_data['date'], best_data['shares'], 
                                color='orange', linewidth=2, label='持有份额')
            
            ax4.set_title(f'{best_strategy} - 现金与持仓变化', fontweight='bold')
            ax4.set_xlabel('日期')
            ax4.set_ylabel('现金 (元)', color='green')
            ax4_twin.set_ylabel('份额', color='orange')
            
            # 合并图例
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax4.legend(lines, labels, loc='upper left')
            
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        print("   ✅ 图表生成完成！")
        
        # 8. 策略建议
        print("\n8️⃣ 策略建议总结...")
        print("=" * 60)
        
        print("📝 基于回测结果的建议:")
        
        # 比较阈值策略与基准策略
        best_threshold_return = max([results[name]['return_rate'] for name in strategies.keys()])
        lump_sum_return = results["一次性投资"]['return_rate']
        dca_return = results["定投策略"]['return_rate']
        
        if best_threshold_return > max(lump_sum_return, dca_return):
            print("✅ 阈值策略在此期间表现最佳，建议考虑使用")
            print(f"   最佳阈值策略收益率: {best_threshold_return:.2f}%")
            print(f"   超越一次性投资: {best_threshold_return - lump_sum_return:.2f}个百分点")
            print(f"   超越定投策略: {best_threshold_return - dca_return:.2f}个百分点")
        else:
            print("⚠️  在此期间，传统策略表现更好")
        
        print(f"\n💡 {best_strategy}参数建议:")
        if best_strategy in strategies:
            params = strategies[best_strategy]
            print(f"   - 买入阈值: {params['buy_threshold']}% (适合当前市场波动)")
            print(f"   - 卖出阈值: +{params['sell_threshold']}% (平衡收益与风险)")
            print(f"   - 回顾期: {params['lookback_period']}天 (适合中期趋势判断)")
        
        print("\n⚠️  重要提示:")
        print("   - 阈值策略需要频繁交易，注意交易成本")
        print("   - 参数设置需要根据市场环境调整")
        print("   - 历史表现不代表未来收益")
        print("   - 建议结合个人风险承受能力选择策略")
        
        print("\n✅ 阈值策略演示完成！")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        print("💡 这可能是由于网络连接问题或数据源暂时不可用")

if __name__ == "__main__":
    demo_threshold_strategy()