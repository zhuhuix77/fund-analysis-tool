"""
基金回测分析程序
功能：基金数据下载、回测分析、图形趋势分析
"""

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

class FundDataDownloader:
    """基金数据下载器"""
    
    def __init__(self):
        self.base_url = "http://fund.eastmoney.com/f10/F10DataApi.aspx"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_fund_info(self, fund_code: str) -> Dict[str, Any]:
        """获取基金基本信息"""
        try:
            url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                # 解析返回的JavaScript格式数据
                content = response.text.strip()
                
                # 检查返回内容是否为有效的JSONP格式
                if content.startswith('jsonpgz(') and content.endswith(');'):
                    json_str = content[8:-2]  # 去掉 'jsonpgz(' 和 ');'
                    try:
                        data = json.loads(json_str)
                        return data
                    except json.JSONDecodeError as je:
                        print(f"JSON解析失败: {je}")
                        return {}
                else:
                    print(f"返回数据格式不正确: {content[:100]}...")
                    return {}
            return {}
        except Exception as e:
            print(f"获取基金信息失败: {e}")
            return {}
    
    def get_fund_history(self, fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取基金历史净值数据"""
        try:
            # 使用天天基金网的历史净值接口
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 构建请求URL
            url = f"http://fund.eastmoney.com/f10/F10DataApi.aspx"
            params = {
                'type': 'lsjz',
                'code': fund_code,
                'sdate': start_date,
                'edate': end_date,
                'per': 49,
                'page': 1
            }
            
            all_data = []
            page = 1
            
            while True:
                params['page'] = page
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
                
                if response.status_code != 200:
                    break
                
                content = response.text
                # 解析返回的数据
                if 'content:' in content:
                    start_idx = content.find('content:"') + 9
                    end_idx = content.find('",records:')
                    data_content = content[start_idx:end_idx]
                    
                    if not data_content or data_content == '':
                        break
                    
                    # 解析HTML表格数据
                    import re
                    rows = re.findall(r'<tr>(.*?)</tr>', data_content)
                    
                    for row in rows:
                        cols = re.findall(r'<td[^>]*>(.*?)</td>', row)
                        if len(cols) >= 4:
                            try:
                                date = cols[0].strip()
                                nav_str = cols[1].strip()
                                acc_nav_str = cols[2].strip()
                                daily_return = cols[3].strip()
                                
                                # 更严格的数据验证
                                if nav_str and nav_str != '--' and nav_str != '':
                                    nav = float(nav_str)
                                    acc_nav = float(acc_nav_str) if acc_nav_str and acc_nav_str != '--' else nav
                                    
                                    # 验证日期格式
                                    parsed_date = pd.to_datetime(date)
                                    
                                    all_data.append({
                                        'date': parsed_date,
                                        'nav': nav,
                                        'acc_nav': acc_nav,
                                        'daily_return': daily_return
                                    })
                            except (ValueError, IndexError, TypeError) as e:
                                # 跳过无效数据行
                                continue
                    
                    page += 1
                    time.sleep(0.1)  # 避免请求过快
                    
                    if page > 50:  # 防止无限循环
                        break
                else:
                    break
            
            if all_data:
                df = pd.DataFrame(all_data)
                df = df.sort_values('date').reset_index(drop=True)
                return df
            else:
                # 如果无法获取历史数据，生成模拟数据
                print(f"无法获取基金 {fund_code} 的历史数据，生成模拟数据")
                return self._generate_mock_data(fund_code, start_date, end_date)
                
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return self._generate_mock_data(fund_code, start_date, end_date)
    
    def _generate_mock_data(self, fund_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟基金数据"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # 生成交易日期（排除周末）
        dates = pd.bdate_range(start=start, end=end)
        
        # 生成模拟净值数据
        np.random.seed(hash(fund_code) % 2**32)  # 基于基金代码设置随机种子
        
        initial_nav = 1.0 + np.random.uniform(0, 2)  # 初始净值
        returns = np.random.normal(0.0005, 0.02, len(dates))  # 日收益率
        
        navs = [initial_nav]
        for ret in returns[1:]:
            navs.append(navs[-1] * (1 + ret))
        
        df = pd.DataFrame({
            'date': dates,
            'nav': navs,
            'acc_nav': navs,  # 简化处理，累计净值等于净值
            'daily_return': [0] + [f"{ret*100:.2f}%" for ret in returns[1:]]
        })
        
        return df

class FundBacktester:
    """基金回测分析器"""
    
    def __init__(self, fund_data: pd.DataFrame):
        self.data = fund_data.copy()
        self.prepare_data()
    
    def prepare_data(self):
        """准备数据"""
        self.data['returns'] = self.data['nav'].pct_change()
        self.data['cumulative_returns'] = (1 + self.data['returns']).cumprod() - 1
        
    def calculate_metrics(self) -> Dict[str, Any]:
        """计算回测指标"""
        returns = self.data['returns'].dropna()
        
        # 基本统计指标
        total_return = (self.data['nav'].iloc[-1] / self.data['nav'].iloc[0] - 1) * 100
        annual_return = ((1 + total_return/100) ** (252 / len(returns)) - 1) * 100
        volatility = returns.std() * np.sqrt(252) * 100
        
        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return/100 - risk_free_rate) / (volatility/100) if volatility > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        # 胜率
        win_rate = (returns > 0).sum() / len(returns) * 100
        
        return {
            '总收益率(%)': round(total_return, 2),
            '年化收益率(%)': round(annual_return, 2),
            '年化波动率(%)': round(volatility, 2),
            '夏普比率': round(sharpe_ratio, 2),
            '最大回撤(%)': round(max_drawdown, 2),
            '胜率(%)': round(win_rate, 2),
            '交易天数': len(returns)
        }
    
    def simulate_investment(self, initial_amount: float = 10000, 
                          investment_strategy: str = 'lump_sum',
                          buy_threshold: float = None,
                          sell_threshold: float = None,
                          lookback_period: int = 20) -> pd.DataFrame:
        """
        模拟投资
        
        Parameters:
        - initial_amount: 初始投资金额
        - investment_strategy: 投资策略 ('lump_sum', 'dca', 'threshold')
        - buy_threshold: 买入阈值（跌幅百分比，如-5表示跌5%时买入）
        - sell_threshold: 卖出阈值（涨幅百分比，如10表示涨10%时卖出）
        - lookback_period: 回顾期天数（用于计算阈值基准）
        """
        result_data = self.data.copy()
        
        if investment_strategy == 'lump_sum':
            # 一次性投资
            shares = initial_amount / result_data['nav'].iloc[0]
            result_data['portfolio_value'] = shares * result_data['nav']
            result_data['shares'] = shares
            result_data['cash'] = 0
            result_data['action'] = 'hold'
            
        elif investment_strategy == 'dca':
            # 定投策略（每月定投）
            monthly_investment = initial_amount / 12  # 假设分12个月定投
            result_data['shares'] = 0.0
            result_data['portfolio_value'] = 0.0
            result_data['cash'] = 0.0
            result_data['action'] = 'hold'
            
            total_shares = 0
            for i in range(len(result_data)):
                # 每20个交易日（约一个月）定投一次
                if i % 20 == 0:
                    shares_bought = monthly_investment / result_data['nav'].iloc[i]
                    total_shares += shares_bought
                    result_data.loc[i, 'action'] = 'buy'
                
                result_data.loc[i, 'shares'] = total_shares
                result_data.loc[i, 'portfolio_value'] = total_shares * result_data['nav'].iloc[i]
                
        elif investment_strategy == 'threshold':
            # 阈值策略
            result_data = self._simulate_threshold_strategy(
                result_data, initial_amount, buy_threshold, sell_threshold, lookback_period
            )
        
        return result_data
    
    def _simulate_threshold_strategy(self, data: pd.DataFrame, initial_amount: float,
                                   buy_threshold: float, sell_threshold: float, 
                                   lookback_period: int) -> pd.DataFrame:
        """阈值策略模拟"""
        data['shares'] = 0.0
        data['cash'] = initial_amount  # 初始现金
        data['portfolio_value'] = initial_amount
        data['action'] = 'hold'
        data['signal'] = 0  # 1=买入信号, -1=卖出信号, 0=持有
        data['lookback_return'] = 0.0  # 回顾期收益率
        
        shares = 0.0
        cash = initial_amount
        
        for i in range(len(data)):
            current_nav = data['nav'].iloc[i]
            
            # 计算回顾期收益率
            if i >= lookback_period:
                lookback_nav = data['nav'].iloc[i - lookback_period]
                lookback_return = (current_nav / lookback_nav - 1) * 100
                data.loc[i, 'lookback_return'] = lookback_return
                
                # 判断买入信号
                if (buy_threshold is not None and 
                    lookback_return <= buy_threshold and 
                    cash > 0):
                    # 买入信号：回顾期跌幅达到买入阈值
                    buy_amount = min(cash, initial_amount * 0.2)  # 每次最多买入20%
                    shares_to_buy = buy_amount / current_nav
                    shares += shares_to_buy
                    cash -= buy_amount
                    data.loc[i, 'action'] = 'buy'
                    data.loc[i, 'signal'] = 1
                
                # 判断卖出信号
                elif (sell_threshold is not None and 
                      lookback_return >= sell_threshold and 
                      shares > 0):
                    # 卖出信号：回顾期涨幅达到卖出阈值
                    shares_to_sell = shares * 0.3  # 每次卖出30%
                    sell_amount = shares_to_sell * current_nav
                    shares -= shares_to_sell
                    cash += sell_amount
                    data.loc[i, 'action'] = 'sell'
                    data.loc[i, 'signal'] = -1
            
            # 更新持仓信息
            data.loc[i, 'shares'] = shares
            data.loc[i, 'cash'] = cash
            data.loc[i, 'portfolio_value'] = shares * current_nav + cash
        
        return data

class FundAnalyzer:
    """基金分析可视化"""
    
    def __init__(self, fund_code: str, fund_data: pd.DataFrame, backtest_results: Dict[str, Any]):
        self.fund_code = fund_code
        self.data = fund_data
        self.results = backtest_results
    
    def plot_comprehensive_analysis(self):
        """绘制综合分析图表"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'基金 {self.fund_code} 回测分析报告', fontsize=16, fontweight='bold')
        
        # 1. 净值走势图
        ax1 = axes[0, 0]
        ax1.plot(self.data['date'], self.data['nav'], linewidth=2, color='blue')
        ax1.set_title('净值走势', fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('净值')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. 累计收益率
        ax2 = axes[0, 1]
        cumulative_returns = (self.data['nav'] / self.data['nav'].iloc[0] - 1) * 100
        ax2.plot(self.data['date'], cumulative_returns, linewidth=2, color='green')
        ax2.set_title('累计收益率', fontweight='bold')
        ax2.set_xlabel('日期')
        ax2.set_ylabel('收益率 (%)')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # 3. 日收益率分布
        ax3 = axes[1, 0]
        returns = self.data['nav'].pct_change().dropna() * 100
        ax3.hist(returns, bins=50, alpha=0.7, color='orange', edgecolor='black')
        ax3.set_title('日收益率分布', fontweight='bold')
        ax3.set_xlabel('日收益率 (%)')
        ax3.set_ylabel('频次')
        ax3.axvline(x=returns.mean(), color='red', linestyle='--', 
                   label=f'均值: {returns.mean():.2f}%')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 回撤分析
        ax4 = axes[1, 1]
        cumulative = (1 + self.data['nav'].pct_change().fillna(0)).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max * 100
        
        ax4.fill_between(self.data['date'], drawdown, 0, alpha=0.3, color='red')
        ax4.plot(self.data['date'], drawdown, linewidth=1, color='darkred')
        ax4.set_title('回撤分析', fontweight='bold')
        ax4.set_xlabel('日期')
        ax4.set_ylabel('回撤 (%)')
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def plot_investment_comparison(self, simulation_data: pd.DataFrame):
        """绘制投资策略对比"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 投资组合价值走势
        ax1.plot(simulation_data['date'], simulation_data['portfolio_value'], 
                linewidth=2, color='purple', label='投资组合价值')
        ax1.set_title('投资组合价值走势', fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('价值 (元)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 关键指标展示
        ax2.axis('off')
        metrics_text = "回测指标:\n\n"
        for key, value in self.results.items():
            metrics_text += f"{key}: {value}\n"
        
        ax2.text(0.1, 0.9, metrics_text, transform=ax2.transAxes, 
                fontsize=12, verticalalignment='top',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
        
        plt.tight_layout()
        plt.show()
    
    def print_analysis_report(self):
        """打印分析报告"""
        print("="*60)
        print(f"基金 {self.fund_code} 回测分析报告")
        print("="*60)
        
        print(f"分析期间: {self.data['date'].iloc[0].strftime('%Y-%m-%d')} 至 {self.data['date'].iloc[-1].strftime('%Y-%m-%d')}")
        print(f"数据天数: {len(self.data)} 天")
        print()
        
        print("关键指标:")
        print("-"*30)
        for key, value in self.results.items():
            print(f"{key:<15}: {value}")
        
        print()
        print("投资建议:")
        print("-"*30)
        
        # 基于指标给出简单建议
        annual_return = self.results['年化收益率(%)']
        volatility = self.results['年化波动率(%)']
        sharpe_ratio = self.results['夏普比率']
        max_drawdown = abs(self.results['最大回撤(%)'])
        
        if annual_return > 10 and sharpe_ratio > 1 and max_drawdown < 20:
            print("✅ 该基金表现优秀，风险收益比较好")
        elif annual_return > 5 and sharpe_ratio > 0.5:
            print("⚠️  该基金表现中等，可考虑配置")
        else:
            print("❌ 该基金表现较差，建议谨慎投资")
        
        if volatility > 25:
            print("⚠️  该基金波动较大，适合风险承受能力强的投资者")
        
        print("="*60)

def main():
    """主函数"""
    print("基金回测分析程序")
    print("="*50)
    
    # 获取用户输入
    fund_code = input("请输入基金代码 (例如: 000001): ").strip()
    if not fund_code:
        fund_code = "000001"  # 默认基金代码
    
    print(f"\n正在分析基金: {fund_code}")
    
    # 1. 下载基金数据
    print("1. 正在下载基金数据...")
    downloader = FundDataDownloader()
    
    # 获取基金基本信息
    fund_info = downloader.get_fund_info(fund_code)
    if fund_info:
        print(f"基金名称: {fund_info.get('name', '未知')}")
    
    # 获取历史数据
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    fund_data = downloader.get_fund_history(fund_code, start_date)
    
    if fund_data.empty:
        print("无法获取基金数据，程序退出")
        return
    
    print(f"成功获取 {len(fund_data)} 天的数据")
    
    # 2. 进行回测分析
    print("\n2. 正在进行回测分析...")
    backtester = FundBacktester(fund_data)
    metrics = backtester.calculate_metrics()
    
    # 3. 模拟投资
    print("3. 正在模拟投资...")
    simulation_data = backtester.simulate_investment(10000, 'lump_sum')
    
    # 4. 生成分析报告和图表
    print("4. 正在生成分析报告...")
    analyzer = FundAnalyzer(fund_code, fund_data, metrics)
    
    # 打印报告
    analyzer.print_analysis_report()
    
    # 绘制图表
    print("\n5. 正在生成图表...")
    analyzer.plot_comprehensive_analysis()
    analyzer.plot_investment_comparison(simulation_data)
    
    print("\n分析完成！")

if __name__ == "__main__":
    main()