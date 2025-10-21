# -*- coding: utf-8 -*-
"""
基金回测系统 Streamlit 可视化应用
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import data_manager
import strategy
import backtester
from config import BACKTEST_START_DATE, BACKTEST_END_DATE, TARGET_FUNDS

# --- 策略名称到函数名的映射 ---
STRATEGY_MAPPING = {
    "均线交叉策略": "ma_crossover_strategy",
    "RSI 指标策略": "rsi_strategy",
    "布林带策略": "bollinger_bands_strategy",
    "MACD 策略": "macd_strategy",
    "定期定额策略 (DCA)": "dca_strategy",
    "回顾期价格变动阈值策略": "threshold_strategy",
}

st.set_page_config(layout="wide", page_title="基金回测系统")
st.title("📈 基金回测系统")
st.write("一个简单的工具，用于测试不同基金的真实投资策略表现。")

# --- 侧边栏 ---
st.sidebar.header("① 回测参数配置")
fund_code = st.sidebar.text_input("基金代码", value=TARGET_FUNDS[0])
start_date = st.sidebar.text_input("开始日期 (YYYYMMDD)", value=BACKTEST_START_DATE)
end_date = st.sidebar.text_input("结束日期 (YYYYMMDD)", value=BACKTEST_END_DATE)
initial_capital = st.sidebar.number_input("初始资金", min_value=1000, value=100000, step=10000)

st.sidebar.header("② 策略选择与配置")
strategy_name = st.sidebar.selectbox(
    "选择一个策略",
    list(STRATEGY_MAPPING.keys())
)

# --- 动态策略参数 ---
params = {}
if strategy_name == "均线交叉策略":
    params['short_window'] = st.sidebar.slider("短期均线", 5, 50, 20, 1)
    params['long_window'] = st.sidebar.slider("长期均线", 20, 200, 60, 5)
    if params['long_window'] <= params['short_window']:
        st.sidebar.error("长期均线必须大于短期均线。")
        st.stop()
elif strategy_name == "RSI 指标策略":
    params['rsi_period'] = st.sidebar.slider("RSI 周期", 7, 30, 14, 1)
    params['oversold_threshold'] = st.sidebar.slider("超卖阈值", 10, 40, 30, 1)
    params['overbought_threshold'] = st.sidebar.slider("超买阈值", 60, 90, 70, 1)
elif strategy_name == "布林带策略":
    params['window'] = st.sidebar.slider("窗口期", 10, 50, 20, 1)
    params['std_dev'] = st.sidebar.slider("标准差倍数", 1.0, 3.0, 2.0, 0.1)
elif strategy_name == "MACD 策略":
    params['fast_period'] = st.sidebar.slider("快线周期(fast)", 5, 50, 12, 1)
    params['slow_period'] = st.sidebar.slider("慢线周期(slow)", 20, 100, 26, 1)
    params['signal_period'] = st.sidebar.slider("信号线周期(signal)", 5, 30, 9, 1)
elif strategy_name == "定期定额策略 (DCA)":
    params['interval_days'] = st.sidebar.slider("定投间隔(天)", 1, 90, 30, 1)
    params['amount'] = st.sidebar.number_input("每次定投金额", min_value=100, value=1000, step=100)
elif strategy_name == "回顾期价格变动阈值策略":
    params['lookback_period'] = st.sidebar.slider("回顾期天数", 1, 200, 20, 1, help="计算价格变动的参考时间窗口。")
    params['buy_threshold'] = st.sidebar.slider("买入阈值 (%)", -50.0, 0.0, -5.0, 0.5, help="当价格变动率低于此值时，触发买入。")
    params['sell_threshold'] = st.sidebar.slider("卖出阈值 (%)", 0.0, 50.0, 10.0, 0.5, help="当价格变动率高于此值时，触发卖出。")

st.sidebar.header("③ 交易模式配置")
trade_amount = None
if strategy_name != "定期定额策略 (DCA)":
    trade_mode = st.sidebar.selectbox("交易模式", ["全仓交易", "固定金额交易"])
    if trade_mode == "固定金额交易":
        trade_amount = st.sidebar.number_input("每次交易金额", min_value=100, value=10000, step=1000)
else:
    st.sidebar.info("DCA策略自带固定金额模式。")

# --- 主逻辑 ---
if st.sidebar.button("🚀 开始回测"):
    with st.spinner(f"正在获取基金 {fund_code} 的历史数据..."):
        fund_history = data_manager.get_fund_history(fund_code, start_date, end_date)
        if fund_history.empty:
            st.error("获取数据失败，请检查基金代码和日期。")
            st.stop()
        st.success("数据获取成功！")

    with st.spinner(f"正在应用 {strategy_name}..."):
        # 使用映射字典来获取正确的函数名
        func_name = STRATEGY_MAPPING[strategy_name]
        strategy_func = getattr(strategy, func_name)
        
        # 策略函数现在自己处理阈值转换，所以直接传递参数
        strategy_params = params.copy()
        strategy_data = strategy_func(fund_history, **strategy_params)
        st.success("策略应用成功！")

    with st.spinner("正在执行回测模拟..."):
        is_dca = "DCA" in strategy_name
        portfolio, performance, trade_log = backtester.run_backtest(
            data=strategy_data,
            initial_capital=initial_capital,
            is_dca=is_dca,
            trade_amount=trade_amount
        )
        st.success("回测模拟完成！")

    # --- 结果展示 ---
    st.header("📊 回测结果")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("初始资金", f"¥{performance['initial_capital']:,.2f}")
    col2.metric("最终资产", f"¥{performance['final_portfolio_value']:,.2f}")
    col3.metric("策略总收益率", f"{performance['total_return']:.2%}")
    col4.metric("基准总收益率", f"{performance['benchmark_return']:.2%}")

    st.subheader("收益曲线与交易信号")
    
    rows = 2 if strategy_name in ["RSI 指标策略", "MACD 策略"] else 1
    heights = [0.7, 0.3] if rows == 2 else [1.0]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=heights)

    fig.add_trace(go.Scatter(x=portfolio.index, y=portfolio['total'] / initial_capital, name='策略收益'), row=1, col=1)
    benchmark_series = fund_history['close'] / fund_history['close'].iloc[0]
    fig.add_trace(go.Scatter(x=benchmark_series.index, y=benchmark_series, name='基准收益'), row=1, col=1)

    if strategy_name == "均线交叉策略":
        fig.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['short_ma'], name='短期均线', line=dict(width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['long_ma'], name='长期均线', line=dict(width=1, dash='dot')), row=1, col=1)
    elif strategy_name == "布林带策略":
        fig.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['bbu'], name='上轨', line=dict(width=1, color='rgba(152,251,152,0.5)')), row=1, col=1)
        fig.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['bbl'], name='下轨', line=dict(width=1, color='rgba(152,251,152,0.5)'), fill='tonexty', fillcolor='rgba(152,251,152,0.1)'), row=1, col=1)
    elif strategy_name == "RSI 指标策略":
        fig.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['rsi'], name='RSI'), row=2, col=1)
        fig.add_hline(y=params['overbought_threshold'], line_width=1, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=params['oversold_threshold'], line_width=1, line_dash="dash", line_color="green", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1)
    elif strategy_name == "MACD 策略":
        fig.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['macd'], name='MACD'), row=2, col=1)
        fig.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['signal_line'], name='Signal Line'), row=2, col=1)
        fig.add_bar(x=strategy_data.index, y=strategy_data['macd'] - strategy_data['signal_line'], name='Histogram', marker_color='grey', row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=2, col=1)

    # --- 从实际交易日志中绘制买卖点 ---
    if not trade_log.empty:
        # trade_log 现在将 'date' 作为一个列
        buy_signals = trade_log[trade_log['action'] == '买入']
        sell_signals = trade_log[trade_log['action'] == '卖出']
        
        if not buy_signals.empty:
            # 使用 'date' 列来绘图
            fig.add_trace(go.Scatter(
                x=buy_signals['date'], 
                y=benchmark_series.loc[buy_signals['date']], 
                mode='markers', marker=dict(color='red', size=10, symbol='triangle-up'), 
                name='实际买入点'
            ), row=1, col=1)
        
        if not sell_signals.empty:
            # 使用 'date' 列来绘图
            fig.add_trace(go.Scatter(
                x=sell_signals['date'], 
                y=benchmark_series.loc[sell_signals['date']], 
                mode='markers', marker=dict(color='green', size=10, symbol='triangle-down'), 
                name='实际卖出点'
            ), row=1, col=1)

    # 为回顾期价格变动阈值策略添加辅助图表
    if strategy_name == "回顾期价格变动阈值策略":
        st.subheader("价格变动率与阈值")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=strategy_data.index, y=strategy_data['price_change_pct'] * 100, name=f"{params['lookback_period']}日价格变动率 (%)"))
        fig2.add_hline(y=params['buy_threshold'], line_width=2, line_dash="dash", line_color="green", name='买入阈值')
        fig2.add_hline(y=params['sell_threshold'], line_width=2, line_dash="dash", line_color="red", name='卖出阈值')
        fig2.update_layout(title_text='价格变动率与交易阈值', yaxis_title='变动率 (%)')
        st.plotly_chart(fig2, use_container_width=True)

    fig.update_layout(title_text='策略收益 vs. 基准收益', legend_title='图例')
    fig.update_yaxes(title_text="归一化净值", row=1, col=1)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("详细交易记录")
    if not trade_log.empty:
        display_log = trade_log.copy()

        # Part 1: 为阈值策略生成触发说明
        if strategy_name == "回顾期价格变动阈值策略" and 'price_change_pct' in display_log.columns:
            def create_explanation(row):
                # 使用新的列名 price_change_pct 和 *_threshold_pct
                if row['action'] == '买入':
                    # 修正：阈值已经是百分比数字，直接格式化为浮点数并手动加“%”
                    return f"价格变动率 {row['price_change_pct']:.2%} <= 买入阈值 {row['buy_threshold_pct']:.1f}%"
                elif row['action'] == '卖出':
                    # 修正：阈值已经是百分比数字，直接格式化为浮点数并手动加“%”
                    return f"价格变动率 {row['price_change_pct']:.2%} >= 卖出阈值 {row['sell_threshold_pct']:.1f}%"
                return ""
            display_log['触发说明'] = display_log.apply(create_explanation, axis=1)

        # Part 2: 格式化所有列
        display_log['date'] = display_log['date'].dt.strftime('%Y-%m-%d')
        display_log['price'] = pd.to_numeric(display_log['price'], errors='coerce').map('{:.4f}'.format)
        display_log['shares'] = pd.to_numeric(display_log['shares'], errors='coerce').map('{:,.2f}'.format)
        display_log['amount'] = pd.to_numeric(display_log['amount'], errors='coerce').map('¥{:,.2f}'.format)
        
        # 格式化阈值策略的特定列
        if 'reference_nav' in display_log.columns:
            display_log['reference_nav'] = pd.to_numeric(display_log['reference_nav'], errors='coerce').map('{:.4f}'.format)
        if 'reference_date' in display_log.columns:
            display_log['reference_date'] = pd.to_datetime(display_log['reference_date'], errors='coerce').dt.strftime('%Y-%m-%d')

        # Part 3: 重命名并选择要显示的列
        display_log.rename(columns={
            'date': '日期',
            'action': '类型',
            'price': '成交净值',
            'shares': '份额',
            'amount': '成交金额(元)',
            'reference_nav': '参考净值',
            'reference_date': '参考净值日期',
        }, inplace=True)
        
        # 根据策略选择最终要显示的列
        if strategy_name == "回顾期价格变动阈值策略":
            final_cols_order = ['日期', '类型', '成交净值', '参考净值', '参考净值日期', '份额', '成交金额(元)', '触发说明']
        else:
            final_cols_order = ['日期', '类型', '成交净值', '份额', '成交金额(元)']

        cols_to_display = [col for col in final_cols_order if col in display_log.columns]
        st.dataframe(display_log[cols_to_display], use_container_width=True, hide_index=True)
    else:
        st.info("在回测期间内未发生任何实际交易。")

else:
    st.info("请在左侧配置参数并点击“开始回测”按钮。")