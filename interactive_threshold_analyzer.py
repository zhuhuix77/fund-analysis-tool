"""
交互式基金阈值策略分析器
用户可以自定义基金代码、阈值参数等进行个性化分析
"""

from fund_backtest import FundDataDownloader, FundBacktester
from enhanced_analyzer import EnhancedFundAnalyzer
import matplotlib.pyplot as plt
import pandas as pd
import warnings
import datetime
from typing import Dict, Any

warnings.filterwarnings('ignore')

class InteractiveThresholdAnalyzer:
    """交互式阈值策略分析器"""
    
    def __init__(self):
        self.downloader = FundDataDownloader()
        self.current_fund_data = None
        self.current_fund_code = None
        self.current_fund_name = None
    
    def display_welcome(self):
        """显示欢迎界面"""
        print("🎯" + "="*60)
        print("    交互式基金阈值策略分析器")
        print("    Interactive Fund Threshold Strategy Analyzer")
        print("="*63)
        print("📊 功能特色:")
        print("   ✅ 自定义基金代码分析")
        print("   ✅ 个性化阈值参数设置")
        print("   ✅ 多种预设策略选择")
        print("   ✅ 实时图表展示")
        print("   ✅ 详细分析报告")
        print("="*63)
    
    def get_fund_input(self) -> tuple:
        """获取用户输入的基金信息"""
        print("\n📈 第一步：选择分析基金")
        print("-" * 40)
        
        # 显示热门基金示例
        popular_funds = {
            "000001": "华夏成长混合",
            "110022": "易方达消费行业股票", 
            "161725": "招商中证白酒指数(LOF)A",
            "012348": "天弘恒生科技指数(QDII)A",
            "519674": "银河创新成长混合A",
            "000300": "华夏沪深300ETF联接A",
            "110011": "易方达中小盘混合",
            "260108": "景顺长城新兴成长混合"
        }
        
        print("💡 热门基金代码参考:")
        for code, name in popular_funds.items():
            print(f"   {code} - {name}")
        
        while True:
            fund_code = input("\n请输入基金代码 (6位数字): ").strip()
            
            if not fund_code:
                print("❌ 基金代码不能为空，请重新输入")
                continue
            
            if not fund_code.isdigit() or len(fund_code) != 6:
                print("❌ 基金代码格式错误，请输入6位数字")
                continue
            
            # 验证基金代码
            print(f"🔍 正在验证基金代码 {fund_code}...")
            fund_info = self.downloader.get_fund_info(fund_code)
            
            if fund_info and fund_info.get('name'):
                fund_name = fund_info['name']
                current_nav = fund_info.get('gsz', 'N/A')
                print(f"✅ 基金验证成功!")
                print(f"   基金名称: {fund_name}")
                print(f"   当前净值: {current_nav}")
                
                confirm = input(f"\n确认分析此基金吗? (y/n): ").strip().lower()
                if confirm in ['y', 'yes', '是', '确认', '']:
                    return fund_code, fund_name
                else:
                    continue
            else:
                print(f"❌ 基金代码 {fund_code} 无效或暂时无法获取信息")
                retry = input("是否重新输入? (y/n): ").strip().lower()
                if retry not in ['y', 'yes', '是', '']:
                    return None, None
    
    def get_date_range(self) -> tuple:
        """获取分析时间范围"""
        print("\n📅 第二步：设置分析时间范围")
        print("-" * 40)
        
        # 预设时间范围选项
        today = datetime.date.today()
        options = {
            "1": ("最近1年", today - datetime.timedelta(days=365), today),
            "2": ("最近2年", today - datetime.timedelta(days=730), today),
            "3": ("最近3年", today - datetime.timedelta(days=1095), today),
            "4": ("2023年全年", datetime.date(2023, 1, 1), datetime.date(2023, 12, 31)),
            "5": ("2022年全年", datetime.date(2022, 1, 1), datetime.date(2022, 12, 31)),
            "6": ("自定义时间范围", None, None)
        }
        
        print("请选择分析时间范围:")
        for key, (desc, start, end) in options.items():
            if start and end:
                print(f"   {key}. {desc} ({start} 至 {end})")
            else:
                print(f"   {key}. {desc}")
        
        while True:
            choice = input("\n请选择 (1-6): ").strip()
            
            if choice in options:
                desc, start_date, end_date = options[choice]
                
                if choice == "6":  # 自定义时间范围
                    print("\n请输入自定义时间范围:")
                    while True:
                        try:
                            start_str = input("开始日期 (YYYY-MM-DD): ").strip()
                            end_str = input("结束日期 (YYYY-MM-DD): ").strip()
                            
                            start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
                            end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
                            
                            if start_date >= end_date:
                                print("❌ 开始日期必须早于结束日期")
                                continue
                            
                            if end_date > today:
                                print("❌ 结束日期不能超过今天")
                                continue
                            
                            break
                        except ValueError:
                            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
                
                print(f"✅ 已选择: {desc}")
                if start_date and end_date:
                    print(f"   时间范围: {start_date} 至 {end_date}")
                
                return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            else:
                print("❌ 无效选择，请输入 1-6")
    
    def get_strategy_parameters(self) -> Dict[str, Any]:
        """获取策略参数"""
        print("\n⚙️ 第三步：设置阈值策略参数")
        print("-" * 40)
        
        # 预设策略选项
        preset_strategies = {
            "1": {
                "name": "保守策略",
                "buy_threshold": -8,
                "sell_threshold": 15,
                "lookback_period": 30,
                "description": "适合稳健投资者，交易频率低"
            },
            "2": {
                "name": "积极策略", 
                "buy_threshold": -5,
                "sell_threshold": 10,
                "lookback_period": 20,
                "description": "平衡收益与风险，交易频率中等"
            },
            "3": {
                "name": "激进策略",
                "buy_threshold": -3,
                "sell_threshold": 8,
                "lookback_period": 15,
                "description": "追求高收益，交易频率高"
            },
            "4": {
                "name": "自定义策略",
                "description": "完全自定义参数"
            }
        }
        
        print("请选择策略类型:")
        for key, strategy in preset_strategies.items():
            if key != "4":
                print(f"   {key}. {strategy['name']}")
                print(f"      买入阈值: {strategy['buy_threshold']}%, 卖出阈值: +{strategy['sell_threshold']}%, 回顾期: {strategy['lookback_period']}天")
                print(f"      {strategy['description']}")
            else:
                print(f"   {key}. {strategy['name']} - {strategy['description']}")
        
        while True:
            choice = input("\n请选择策略 (1-4): ").strip()
            
            if choice in ["1", "2", "3"]:
                strategy = preset_strategies[choice]
                print(f"✅ 已选择: {strategy['name']}")
                return {
                    "name": strategy['name'],
                    "buy_threshold": strategy['buy_threshold'],
                    "sell_threshold": strategy['sell_threshold'],
                    "lookback_period": strategy['lookback_period']
                }
            
            elif choice == "4":
                print("\n🔧 自定义策略参数:")
                return self.get_custom_parameters()
            
            else:
                print("❌ 无效选择，请输入 1-4")
    
    def get_custom_parameters(self) -> Dict[str, Any]:
        """获取自定义策略参数"""
        while True:
            try:
                print("\n参数说明:")
                print("• 买入阈值: 负数，表示下跌多少百分比时买入 (如: -5 表示跌5%买入)")
                print("• 卖出阈值: 正数，表示上涨多少百分比时卖出 (如: 10 表示涨10%卖出)")
                print("• 回顾期: 正整数，计算收益率的天数 (如: 20 表示看过去20天的表现)")
                
                buy_threshold = float(input("\n买入阈值 (%): "))
                if buy_threshold >= 0:
                    print("❌ 买入阈值应为负数")
                    continue
                
                sell_threshold = float(input("卖出阈值 (%): "))
                if sell_threshold <= 0:
                    print("❌ 卖出阈值应为正数")
                    continue
                
                lookback_period = int(input("回顾期 (天): "))
                if lookback_period <= 0:
                    print("❌ 回顾期应为正整数")
                    continue
                
                if lookback_period > 100:
                    print("⚠️ 回顾期过长可能影响策略敏感性，建议不超过60天")
                    confirm = input("是否继续? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes', '是', '']:
                        continue
                
                print(f"✅ 自定义策略参数:")
                print(f"   买入阈值: {buy_threshold}%")
                print(f"   卖出阈值: +{sell_threshold}%") 
                print(f"   回顾期: {lookback_period}天")
                
                return {
                    "name": "自定义策略",
                    "buy_threshold": buy_threshold,
                    "sell_threshold": sell_threshold,
                    "lookback_period": lookback_period
                }
                
            except ValueError:
                print("❌ 输入格式错误，请输入数字")
    
    def get_investment_amount(self) -> float:
        """获取投资金额"""
        print("\n💰 第四步：设置投资金额")
        print("-" * 40)
        
        preset_amounts = [10000, 50000, 100000, 200000, 500000]
        print("常用投资金额:")
        for i, amount in enumerate(preset_amounts, 1):
            print(f"   {i}. {amount:,}元")
        print(f"   6. 自定义金额")
        
        while True:
            choice = input("\n请选择投资金额 (1-6): ").strip()
            
            if choice in ["1", "2", "3", "4", "5"]:
                amount = preset_amounts[int(choice) - 1]
                print(f"✅ 投资金额: {amount:,}元")
                return amount
            
            elif choice == "6":
                while True:
                    try:
                        amount = float(input("请输入投资金额 (元): "))
                        if amount <= 0:
                            print("❌ 投资金额必须大于0")
                            continue
                        if amount < 1000:
                            print("⚠️ 投资金额过小，建议至少1000元")
                            confirm = input("是否继续? (y/n): ").strip().lower()
                            if confirm not in ['y', 'yes', '是', '']:
                                continue
                        
                        print(f"✅ 投资金额: {amount:,}元")
                        return amount
                    except ValueError:
                        print("❌ 请输入有效的数字")
            else:
                print("❌ 无效选择，请输入 1-6")
    
    def run_analysis(self, fund_code: str, fund_name: str, start_date: str, 
                    end_date: str, strategy_params: Dict[str, Any], 
                    investment_amount: float):
        """运行分析"""
        print("\n🔄 第五步：开始分析")
        print("=" * 50)
        
        try:
            # 1. 下载数据
            print("1️⃣ 正在下载基金数据...")
            fund_data = self.downloader.get_fund_history(fund_code, start_date, end_date)
            
            if fund_data.empty:
                print("❌ 无法获取基金历史数据")
                return False
            
            print(f"   ✅ 成功获取 {len(fund_data)} 天的历史数据")
            print(f"   📅 数据期间: {fund_data['date'].iloc[0].strftime('%Y-%m-%d')} 至 {fund_data['date'].iloc[-1].strftime('%Y-%m-%d')}")
            
            self.current_fund_data = fund_data
            self.current_fund_code = fund_code
            self.current_fund_name = fund_name
            
            # 2. 回测分析
            print("\n2️⃣ 正在进行回测分析...")
            backtester = FundBacktester(fund_data)
            
            # 运行不同策略
            strategies_to_run = {
                "一次性投资": {"strategy": "lump_sum"},
                "定投策略": {"strategy": "dca"},
                strategy_params["name"]: {
                    "strategy": "threshold",
                    "buy_threshold": strategy_params["buy_threshold"],
                    "sell_threshold": strategy_params["sell_threshold"],
                    "lookback_period": strategy_params["lookback_period"]
                }
            }
            
            results = {}
            for strategy_name, params in strategies_to_run.items():
                print(f"   🔹 运行{strategy_name}...")
                
                if params["strategy"] == "threshold":
                    simulation_data = backtester.simulate_investment(
                        investment_amount,
                        params["strategy"],
                        buy_threshold=params["buy_threshold"],
                        sell_threshold=params["sell_threshold"],
                        lookback_period=params["lookback_period"]
                    )
                else:
                    simulation_data = backtester.simulate_investment(
                        investment_amount,
                        params["strategy"]
                    )
                
                final_value = simulation_data['portfolio_value'].iloc[-1]
                return_rate = (final_value / investment_amount - 1) * 100
                
                result = {
                    "final_value": final_value,
                    "return_rate": return_rate,
                    "data": simulation_data
                }
                
                # 如果是阈值策略，添加交易统计
                if params["strategy"] == "threshold":
                    buy_count = len(simulation_data[simulation_data['action'] == 'buy'])
                    sell_count = len(simulation_data[simulation_data['action'] == 'sell'])
                    result.update({
                        "buy_count": buy_count,
                        "sell_count": sell_count,
                        "params": strategy_params
                    })
                
                results[strategy_name] = result
            
            # 3. 显示结果
            print("\n3️⃣ 分析结果")
            print("=" * 60)
            print(f"{'策略名称':<15} {'最终价值(元)':<15} {'收益率(%)':<12} {'交易次数':<10}")
            print("-" * 60)
            
            for strategy_name, result in results.items():
                trades = ""
                if "buy_count" in result and "sell_count" in result:
                    trades = f"{result['buy_count']}买{result['sell_count']}卖"
                else:
                    trades = "-"
                
                print(f"{strategy_name:<15} {result['final_value']:<15.2f} {result['return_rate']:<12.2f} {trades:<10}")
            
            # 找出最佳策略
            best_strategy = max(results.keys(), key=lambda x: results[x]['return_rate'])
            print(f"\n🏆 最佳策略: {best_strategy} (收益率: {results[best_strategy]['return_rate']:.2f}%)")
            
            # 4. 阈值策略详细分析
            threshold_strategy_name = strategy_params["name"]
            if threshold_strategy_name in results:
                print(f"\n4️⃣ {threshold_strategy_name}详细分析")
                print("-" * 50)
                
                threshold_result = results[threshold_strategy_name]
                threshold_data = threshold_result['data']
                
                print(f"📊 策略参数:")
                print(f"   买入阈值: {strategy_params['buy_threshold']}%")
                print(f"   卖出阈值: +{strategy_params['sell_threshold']}%")
                print(f"   回顾期: {strategy_params['lookback_period']}天")
                
                print(f"\n📈 投资结果:")
                print(f"   初始投资: {investment_amount:,.2f}元")
                print(f"   最终价值: {threshold_result['final_value']:,.2f}元")
                print(f"   总收益: {threshold_result['final_value'] - investment_amount:,.2f}元")
                print(f"   收益率: {threshold_result['return_rate']:.2f}%")
                
                print(f"\n🔄 交易统计:")
                print(f"   买入次数: {threshold_result['buy_count']}次")
                print(f"   卖出次数: {threshold_result['sell_count']}次")
                print(f"   最终现金: {threshold_data['cash'].iloc[-1]:,.2f}元")
                print(f"   最终持仓: {threshold_data['shares'].iloc[-1]:.2f}份")
                
                # 分析买卖点
                buy_points = threshold_data[threshold_data['action'] == 'buy']
                sell_points = threshold_data[threshold_data['action'] == 'sell']
                
                if not buy_points.empty:
                    avg_buy_return = buy_points['lookback_return'].mean()
                    print(f"   平均买入时回顾期收益率: {avg_buy_return:.2f}%")
                
                if not sell_points.empty:
                    avg_sell_return = sell_points['lookback_return'].mean()
                    print(f"   平均卖出时回顾期收益率: {avg_sell_return:.2f}%")
            
            # 5. 生成图表
            print(f"\n5️⃣ 正在生成分析图表...")
            
            # 计算基础回测指标
            metrics = backtester.calculate_metrics()
            
            # 使用增强版分析器生成图表
            analyzer = EnhancedFundAnalyzer(fund_code, fund_data, metrics)
            
            # 策略对比图
            analyzer.compare_strategies(results)
            
            # 阈值策略详细分析图
            if threshold_strategy_name in results:
                threshold_data = results[threshold_strategy_name]['data']
                analyzer.plot_threshold_strategy_analysis(
                    threshold_data,
                    strategy_params["name"],
                    strategy_params["buy_threshold"],
                    strategy_params["sell_threshold"],
                    strategy_params["lookback_period"]
                )
            
            print("   ✅ 图表生成完成！")
            
            # 6. 投资建议
            self.generate_investment_advice(results, strategy_params, fund_name)
            
            return True
            
        except Exception as e:
            print(f"❌ 分析过程中出现错误: {e}")
            return False
    
    def generate_investment_advice(self, results: Dict, strategy_params: Dict, fund_name: str):
        """生成投资建议"""
        print(f"\n6️⃣ 投资建议")
        print("=" * 50)
        
        threshold_strategy_name = strategy_params["name"]
        threshold_result = results.get(threshold_strategy_name)
        lump_sum_result = results.get("一次性投资")
        dca_result = results.get("定投策略")
        
        if not threshold_result:
            return
        
        print(f"📝 基于 {fund_name} 的分析建议:")
        
        # 策略表现对比
        threshold_return = threshold_result['return_rate']
        lump_sum_return = lump_sum_result['return_rate'] if lump_sum_result else 0
        dca_return = dca_result['return_rate'] if dca_result else 0
        
        best_return = max(threshold_return, lump_sum_return, dca_return)
        
        if threshold_return == best_return:
            print(f"✅ {threshold_strategy_name}在此期间表现最佳")
            print(f"   收益率: {threshold_return:.2f}%")
            if lump_sum_result:
                print(f"   超越一次性投资: {threshold_return - lump_sum_return:.2f}个百分点")
            if dca_result:
                print(f"   超越定投策略: {threshold_return - dca_return:.2f}个百分点")
        else:
            print(f"⚠️ 在此期间，其他策略表现更好")
            if dca_return == best_return:
                print(f"   定投策略表现最佳: {dca_return:.2f}%")
            elif lump_sum_return == best_return:
                print(f"   一次性投资表现最佳: {lump_sum_return:.2f}%")
        
        # 参数建议
        print(f"\n💡 {threshold_strategy_name}参数评估:")
        
        buy_threshold = strategy_params['buy_threshold']
        sell_threshold = strategy_params['sell_threshold']
        lookback_period = strategy_params['lookback_period']
        
        if threshold_result['buy_count'] == 0:
            print(f"   ⚠️ 买入阈值 {buy_threshold}% 可能过于严格，未触发买入")
            print(f"   建议: 适当放宽买入阈值至 {buy_threshold + 2}% 左右")
        elif threshold_result['buy_count'] > 20:
            print(f"   ⚠️ 买入次数过多 ({threshold_result['buy_count']}次)，可能过于频繁")
            print(f"   建议: 适当收紧买入阈值至 {buy_threshold - 1}% 左右")
        else:
            print(f"   ✅ 买入阈值 {buy_threshold}% 设置合理")
        
        if threshold_result['sell_count'] == 0:
            print(f"   ⚠️ 卖出阈值 +{sell_threshold}% 可能过于严格，未触发卖出")
            print(f"   建议: 适当降低卖出阈值至 +{sell_threshold - 2}% 左右")
        elif threshold_result['sell_count'] > 15:
            print(f"   ⚠️ 卖出次数过多 ({threshold_result['sell_count']}次)，可能过于频繁")
            print(f"   建议: 适当提高卖出阈值至 +{sell_threshold + 2}% 左右")
        else:
            print(f"   ✅ 卖出阈值 +{sell_threshold}% 设置合理")
        
        print(f"   ✅ 回顾期 {lookback_period}天 设置合理")
        
        # 风险提示
        print(f"\n⚠️ 重要提示:")
        print(f"   • 阈值策略需要频繁交易，请考虑交易成本")
        print(f"   • 参数设置需要根据市场环境调整")
        print(f"   • 历史表现不代表未来收益")
        print(f"   • 建议结合基本面分析做出投资决策")
        print(f"   • 请根据个人风险承受能力选择合适的策略")
    
    def ask_continue(self) -> bool:
        """询问是否继续分析"""
        print("\n" + "="*60)
        choice = input("是否继续分析其他基金? (y/n): ").strip().lower()
        return choice in ['y', 'yes', '是', '继续']
    
    def run(self):
        """运行交互式分析器"""
        self.display_welcome()
        
        while True:
            try:
                # 获取用户输入
                fund_code, fund_name = self.get_fund_input()
                if not fund_code:
                    print("👋 感谢使用，再见！")
                    break
                
                start_date, end_date = self.get_date_range()
                strategy_params = self.get_strategy_parameters()
                investment_amount = self.get_investment_amount()
                
                # 确认分析参数
                print("\n📋 分析参数确认:")
                print("-" * 40)
                print(f"基金代码: {fund_code}")
                print(f"基金名称: {fund_name}")
                print(f"分析期间: {start_date} 至 {end_date}")
                print(f"策略类型: {strategy_params['name']}")
                print(f"买入阈值: {strategy_params['buy_threshold']}%")
                print(f"卖出阈值: +{strategy_params['sell_threshold']}%")
                print(f"回顾期: {strategy_params['lookback_period']}天")
                print(f"投资金额: {investment_amount:,}元")
                
                confirm = input("\n确认开始分析? (y/n): ").strip().lower()
                if confirm not in ['y', 'yes', '是', '确认', '']:
                    print("❌ 已取消分析")
                    if not self.ask_continue():
                        break
                    continue
                
                # 运行分析
                success = self.run_analysis(
                    fund_code, fund_name, start_date, end_date,
                    strategy_params, investment_amount
                )
                
                if success:
                    print("\n✅ 分析完成！")
                else:
                    print("\n❌ 分析失败")
                
                # 询问是否继续
                if not self.ask_continue():
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，感谢使用！")
                break
            except Exception as e:
                print(f"\n❌ 程序出现错误: {e}")
                if not self.ask_continue():
                    break
        
        print("\n🎉 感谢使用交互式基金阈值策略分析器！")
        print("💡 如有问题或建议，欢迎反馈改进。")

def main():
    """主函数"""
    analyzer = InteractiveThresholdAnalyzer()
    analyzer.run()

if __name__ == "__main__":
    main()