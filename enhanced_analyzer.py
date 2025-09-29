"""
增强版基金分析器 - 支持阈值策略可视化
"""

from fund_backtest import FundAnalyzer
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

class EnhancedFundAnalyzer(FundAnalyzer):
    """增强版基金分析器"""
    
    def plot_threshold_strategy_analysis(self, simulation_data: pd.DataFrame, 
                                       strategy_name: str = "阈值策略",
                                       buy_threshold: float = None,
                                       sell_threshold: float = None,
                                       lookback_period: int = 20):
        """绘制阈值策略专用分析图表"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'基金 {self.fund_code} - {strategy_name}详细分析', fontsize=16, fontweight='bold')
        
        # 1. 投资组合价值走势 + 买卖点
        ax1 = axes[0, 0]
        ax1.plot(simulation_data['date'], simulation_data['portfolio_value'], 
                linewidth=2, color='blue', label='组合价值')
        
        # 标记买卖点
        buy_points = simulation_data[simulation_data['action'] == 'buy']
        sell_points = simulation_data[simulation_data['action'] == 'sell']
        
        if not buy_points.empty:
            ax1.scatter(buy_points['date'], buy_points['portfolio_value'], 
                       color='green', marker='^', s=60, label=f'买入点({len(buy_points)}次)', zorder=5)
        if not sell_points.empty:
            ax1.scatter(sell_points['date'], sell_points['portfolio_value'], 
                       color='red', marker='v', s=60, label=f'卖出点({len(sell_points)}次)', zorder=5)
        
        ax1.set_title('投资组合价值 & 交易点', fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('价值 (元)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. 现金与持仓变化
        ax2 = axes[0, 1]
        ax2_twin = ax2.twinx()
        
        line1 = ax2.plot(simulation_data['date'], simulation_data['cash'], 
                        color='green', linewidth=2, label='现金余额')
        line2 = ax2_twin.plot(simulation_data['date'], simulation_data['shares'], 
                            color='orange', linewidth=2, label='持有份额')
        
        ax2.set_title('现金与持仓变化', fontweight='bold')
        ax2.set_xlabel('日期')
        ax2.set_ylabel('现金 (元)', color='green')
        ax2_twin.set_ylabel('份额', color='orange')
        ax2.grid(True, alpha=0.3)
        
        # 合并图例
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax2.legend(lines, labels, loc='upper left')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # 3. 回顾期收益率 + 阈值线
        ax3 = axes[0, 2]
        if 'lookback_return' in simulation_data.columns:
            ax3.plot(simulation_data['date'], simulation_data['lookback_return'], 
                    linewidth=1, color='gray', alpha=0.7, label='回顾期收益率')
            
            # 绘制阈值线
            if buy_threshold is not None:
                ax3.axhline(y=buy_threshold, color='green', linestyle='--', 
                           label=f'买入阈值 ({buy_threshold}%)', alpha=0.8)
            if sell_threshold is not None:
                ax3.axhline(y=sell_threshold, color='red', linestyle='--', 
                           label=f'卖出阈值 (+{sell_threshold}%)', alpha=0.8)
            
            # 标记实际买卖点的收益率
            if not buy_points.empty:
                buy_returns = buy_points['lookback_return']
                ax3.scatter(buy_points['date'], buy_returns, 
                           color='green', marker='^', s=40, alpha=0.8, zorder=5)
            if not sell_points.empty:
                sell_returns = sell_points['lookback_return']
                ax3.scatter(sell_points['date'], sell_returns, 
                           color='red', marker='v', s=40, alpha=0.8, zorder=5)
        
        ax3.set_title(f'回顾期收益率 ({lookback_period}天)', fontweight='bold')
        ax3.set_xlabel('日期')
        ax3.set_ylabel('收益率 (%)')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        
        # 4. 基金净值走势
        ax4 = axes[1, 0]
        ax4.plot(self.data['date'], self.data['nav'], linewidth=2, color='blue', label='基金净值')
        
        # 在净值图上也标记买卖点
        if not buy_points.empty:
            buy_navs = []
            for date in buy_points['date']:
                nav = self.data[self.data['date'] == date]['nav']
                if not nav.empty:
                    buy_navs.append((date, nav.iloc[0]))
            if buy_navs:
                buy_dates, buy_nav_values = zip(*buy_navs)
                ax4.scatter(buy_dates, buy_nav_values, 
                           color='green', marker='^', s=50, alpha=0.8, zorder=5)
        
        if not sell_points.empty:
            sell_navs = []
            for date in sell_points['date']:
                nav = self.data[self.data['date'] == date]['nav']
                if not nav.empty:
                    sell_navs.append((date, nav.iloc[0]))
            if sell_navs:
                sell_dates, sell_nav_values = zip(*sell_navs)
                ax4.scatter(sell_dates, sell_nav_values, 
                           color='red', marker='v', s=50, alpha=0.8, zorder=5)
        
        ax4.set_title('基金净值走势 & 交易点', fontweight='bold')
        ax4.set_xlabel('日期')
        ax4.set_ylabel('净值')
        ax4.grid(True, alpha=0.3)
        ax4.legend()
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
        
        # 5. 交易信号分布
        ax5 = axes[1, 1]
        if 'signal' in simulation_data.columns:
            signals = simulation_data['signal']
            signal_counts = signals.value_counts()
            
            labels = []
            values = []
            colors = []
            
            if 1 in signal_counts:
                labels.append(f'买入信号 ({signal_counts[1]}次)')
                values.append(signal_counts[1])
                colors.append('green')
            
            if -1 in signal_counts:
                labels.append(f'卖出信号 ({signal_counts[-1]}次)')
                values.append(signal_counts[-1])
                colors.append('red')
            
            if 0 in signal_counts:
                labels.append(f'持有 ({signal_counts[0]}天)')
                values.append(signal_counts[0])
                colors.append('gray')
            
            if values:
                ax5.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax5.set_title('交易信号分布', fontweight='bold')
        
        # 6. 策略统计信息
        ax6 = axes[1, 2]
        ax6.axis('off')
        
        # 计算统计信息
        stats_text = f"策略参数:\n"
        if buy_threshold is not None:
            stats_text += f"买入阈值: {buy_threshold}%\n"
        if sell_threshold is not None:
            stats_text += f"卖出阈值: +{sell_threshold}%\n"
        stats_text += f"回顾期: {lookback_period}天\n\n"
        
        stats_text += f"交易统计:\n"
        stats_text += f"买入次数: {len(buy_points)}\n"
        stats_text += f"卖出次数: {len(sell_points)}\n"
        
        if not buy_points.empty:
            avg_buy_return = buy_points['lookback_return'].mean()
            stats_text += f"平均买入时收益率: {avg_buy_return:.2f}%\n"
        
        if not sell_points.empty:
            avg_sell_return = sell_points['lookback_return'].mean()
            stats_text += f"平均卖出时收益率: {avg_sell_return:.2f}%\n"
        
        stats_text += f"\n最终状态:\n"
        stats_text += f"现金余额: {simulation_data['cash'].iloc[-1]:.2f}元\n"
        stats_text += f"持有份额: {simulation_data['shares'].iloc[-1]:.2f}\n"
        
        initial_value = simulation_data['portfolio_value'].iloc[0]
        final_value = simulation_data['portfolio_value'].iloc[-1]
        total_return = (final_value / initial_value - 1) * 100
        stats_text += f"总收益率: {total_return:.2f}%\n"
        
        # 添加回测指标
        stats_text += f"\n回测指标:\n"
        for key, value in self.results.items():
            if key in ['年化收益率(%)', '夏普比率', '最大回撤(%)']:
                stats_text += f"{key}: {value}\n"
        
        ax6.text(0.1, 0.9, stats_text, transform=ax6.transAxes, 
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
        
        plt.tight_layout()
        plt.show()
    
    def compare_strategies(self, strategy_results: dict):
        """对比多种策略的结果"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'基金 {self.fund_code} - 多策略对比分析', fontsize=16, fontweight='bold')
        
        # 1. 投资组合价值对比
        ax1 = axes[0, 0]
        for strategy_name, result in strategy_results.items():
            data = result['data']
            ax1.plot(data['date'], data['portfolio_value'], 
                    linewidth=2, label=strategy_name, alpha=0.8)
        
        ax1.set_title('投资组合价值对比', fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('价值 (元)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. 收益率对比
        ax2 = axes[0, 1]
        strategy_names = list(strategy_results.keys())
        returns = [strategy_results[name]['return_rate'] for name in strategy_names]
        
        # 找出最佳策略用不同颜色标记
        best_idx = returns.index(max(returns))
        colors = ['gold' if i == best_idx else 'skyblue' for i in range(len(returns))]
        
        bars = ax2.bar(strategy_names, returns, color=colors, alpha=0.7)
        ax2.set_title('策略收益率对比', fontweight='bold')
        ax2.set_ylabel('收益率 (%)')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 在柱状图上显示数值
        for bar, return_rate in zip(bars, returns):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{return_rate:.1f}%', ha='center', va='bottom')
        
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # 3. 交易次数对比（仅阈值策略）
        ax3 = axes[1, 0]
        threshold_strategies = {k: v for k, v in strategy_results.items() 
                              if 'buy_count' in v and 'sell_count' in v}
        
        if threshold_strategies:
            strategy_names = list(threshold_strategies.keys())
            buy_counts = [threshold_strategies[name]['buy_count'] for name in strategy_names]
            sell_counts = [threshold_strategies[name]['sell_count'] for name in strategy_names]
            
            x = range(len(strategy_names))
            width = 0.35
            
            ax3.bar([i - width/2 for i in x], buy_counts, width, label='买入次数', color='green', alpha=0.7)
            ax3.bar([i + width/2 for i in x], sell_counts, width, label='卖出次数', color='red', alpha=0.7)
            
            ax3.set_title('阈值策略交易次数对比', fontweight='bold')
            ax3.set_ylabel('交易次数')
            ax3.set_xticks(x)
            ax3.set_xticklabels(strategy_names)
            ax3.legend()
            ax3.grid(True, alpha=0.3, axis='y')
            plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        else:
            ax3.text(0.5, 0.5, '无阈值策略数据', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('交易次数对比', fontweight='bold')
        
        # 4. 策略统计表
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        # 创建统计表格
        table_data = []
        headers = ['策略', '收益率(%)', '最终价值(元)']
        
        # 如果有交易数据，添加交易列
        has_trading_data = any('buy_count' in result for result in strategy_results.values())
        if has_trading_data:
            headers.extend(['买入次数', '卖出次数'])
        
        for strategy_name, result in strategy_results.items():
            row = [
                strategy_name,
                f"{result['return_rate']:.2f}",
                f"{result['final_value']:.0f}"
            ]
            
            if has_trading_data:
                row.extend([
                    str(result.get('buy_count', '-')),
                    str(result.get('sell_count', '-'))
                ])
            
            table_data.append(row)
        
        # 创建表格
        table = ax4.table(cellText=table_data, colLabels=headers, 
                         cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        
        # 高亮最佳策略行
        best_strategy = max(strategy_results.keys(), key=lambda x: strategy_results[x]['return_rate'])
        best_row_idx = list(strategy_results.keys()).index(best_strategy) + 1  # +1 因为有表头
        
        for col in range(len(headers)):
            table[(best_row_idx, col)].set_facecolor('gold')
            table[(best_row_idx, col)].set_alpha(0.3)
        
        ax4.set_title('策略对比统计表', fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.show()