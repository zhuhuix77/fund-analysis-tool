import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="交互式基金阈值策略分析器",
    page_icon="📈",
    layout="wide"
)

# --- Helper Functions ---
@st.cache_data
def get_fund_data(fund_code, start_date, end_date):
    """获取基金历史净值数据"""
    try:
        fund_data = ak.fund_open_fund_info_em(fund_code, indicator="单位净值走势")
        
        if fund_data.empty:
            st.warning(f"未找到基金 {fund_code} 的任何数据。")
            return None

        fund_data['净值日期'] = pd.to_datetime(fund_data['净值日期'])
        
        fund_data = fund_data[
            (fund_data['净值日期'] >= pd.to_datetime(start_date)) & 
            (fund_data['净值日期'] <= pd.to_datetime(end_date))
        ]

        if fund_data.empty:
            st.warning(f"在 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 期间未找到基金 {fund_code} 的数据。")
            return None

        fund_data = fund_data.set_index('净值日期')
        fund_data = fund_data.sort_index()
        
        fund_data['单位净值'] = pd.to_numeric(fund_data['单位净值'])
        fund_data['is_trading_day'] = True 
        
        full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        fund_data = fund_data.reindex(full_date_range)
        
        fund_data['单位净值'] = fund_data['单位净值'].ffill()
        fund_data['is_trading_day'] = fund_data['is_trading_day'].fillna(False)
        
        fund_data['单位净值'] = fund_data['单位净值'].bfill()

        fund_data['last_trading_date'] = fund_data.index.to_series()
        fund_data.loc[~fund_data['is_trading_day'], 'last_trading_date'] = pd.NaT
        fund_data['last_trading_date'] = fund_data['last_trading_date'].ffill()

        fund_data.index.name = '净值日期'

        return fund_data
    except Exception as e:
        st.error(f"获取基金数据失败: {e}。请检查基金代码是否正确或网络连接是否正常。")
        return None

@st.cache_data
def get_fund_name(fund_code):
    """获取基金名称"""
    try:
        fund_list = ak.fund_name_em()
        name = fund_list[fund_list['基金代码'] == fund_code]['基金简称'].iloc[0]
        return name
    except Exception:
        return "未知名称"

def calculate_max_drawdown(series):
    """计算最大回撤"""
    if series.empty or series.isna().all():
        return 0.0
    cumulative_max = series.cummax()
    drawdown = (series - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    return max_drawdown * 100 if pd.notna(max_drawdown) else 0.0

def run_backtest(fund_data, dca_amount, threshold_buy_amount, buy_threshold, sell_threshold, lookback_period, dca_freq, dca_day):
    """运行回测并返回详细结果"""

    def get_dca_investment_dates(data, freq, day):
        valid_data = data.dropna(subset=['单位净值'])
        if valid_data.empty: return pd.DatetimeIndex([])
        all_dates = valid_data.index
        investment_dates = set()
        if freq == '每月':
            for _, group in valid_data.groupby(pd.Grouper(freq='MS')):
                month_start = group.index[0]
                actual_day = min(day, month_start.days_in_month)
                target_date = month_start.replace(day=actual_day)
                potential_dates = all_dates[all_dates >= target_date]
                if not potential_dates.empty:
                    actual_date = potential_dates[0]
                    if actual_date.month == target_date.month and actual_date.year == target_date.year:
                        investment_dates.add(actual_date)
        elif freq == '每周':
            weekday_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4}
            target_weekday = weekday_map.get(day, 0)
            for _, group in valid_data.groupby(pd.Grouper(freq='W-MON')):
                potential_dates = group.index[group.index.weekday >= target_weekday]
                if not potential_dates.empty:
                    investment_dates.add(potential_dates[0])
        return pd.DatetimeIndex(sorted(list(investment_dates)))

    dca_investment_dates = get_dca_investment_dates(fund_data, dca_freq, dca_day)
    dca_investments = pd.Series(0.0, index=fund_data.index)
    if dca_amount > 0 and not dca_investment_dates.empty:
        valid_dates = dca_investment_dates[dca_investment_dates.isin(fund_data.index)]
        shares_bought = dca_amount / fund_data.loc[valid_dates, '单位净值']
        dca_investments.loc[valid_dates] = shares_bought
    
    total_dca_invested = len(dca_investment_dates) * dca_amount
    dca_cumulative_shares = dca_investments.cumsum()
    dca_value = dca_cumulative_shares * fund_data['单位净值']

    thr_cash = 0
    thr_shares = 0
    total_thr_invested = 0
    thr_portfolio_value_list = []
    thr_transactions = []
    
    fund_data['reference_nav'] = fund_data['单位净值'].shift(lookback_period)
    fund_data['reference_date'] = fund_data['last_trading_date'].shift(lookback_period)
    fund_data['lookback_return'] = (fund_data['单位净值'] / fund_data['reference_nav'] - 1) * 100

    for date, row in fund_data.iterrows():
        current_value = thr_cash + thr_shares * row['单位净值']
        
        if pd.notna(row['lookback_return']) and row['is_trading_day']:
            if thr_shares > 0 and row['lookback_return'] >= sell_threshold:
                sale_value = thr_shares * row['单位净值']
                reason = f"回顾期收益率 {row['lookback_return']:.2f}% >= 卖出阈值 {sell_threshold}%"
                reference_nav = row['reference_nav']
                reference_date = row['reference_date']
                thr_transactions.append({'date': date, 'type': '卖出', 'price': row['单位净值'], 'shares': thr_shares, 'value': sale_value, 'reason': reason, 'reference_nav': reference_nav, 'reference_date': reference_date})
                thr_cash += sale_value
                thr_shares = 0
                current_value = thr_cash
            elif row['lookback_return'] <= buy_threshold:
                buy_amount = threshold_buy_amount
                reason = f"回顾期收益率 {row['lookback_return']:.2f}% <= 买入阈值 {buy_threshold}%"
                reference_nav = row['reference_nav']
                reference_date = row['reference_date']
                if thr_cash >= buy_amount:
                    thr_cash -= buy_amount
                    shares_to_buy = buy_amount / row['单位净值']
                else:
                    new_capital = buy_amount - thr_cash
                    total_thr_invested += new_capital
                    thr_cash = 0
                    shares_to_buy = buy_amount / row['单位净值']
                
                thr_shares += shares_to_buy
                thr_transactions.append({'date': date, 'type': '买入', 'price': row['单位净值'], 'shares': shares_to_buy, 'value': buy_amount, 'reason': reason, 'reference_nav': reference_nav, 'reference_date': reference_date})
                current_value = thr_cash + thr_shares * row['单位净值']

        thr_portfolio_value_list.append(current_value)

    threshold_value = pd.Series(thr_portfolio_value_list, index=fund_data.index)

    dca_max_drawdown = calculate_max_drawdown(dca_value)
    thr_max_drawdown = calculate_max_drawdown(threshold_value)

    dca_final_value = dca_value.iloc[-1] if not dca_value.empty else 0
    dca_return_rate = (dca_final_value / total_dca_invested - 1) * 100 if total_dca_invested > 0 else 0
    
    thr_final_value = threshold_value.iloc[-1] if not threshold_value.empty else 0
    thr_return_rate = (thr_final_value / total_thr_invested - 1) * 100 if total_thr_invested > 0 else 0

    results = {
        "dca": {
            "name": "定投策略",
            "final_value": dca_final_value,
            "total_invested": total_dca_invested,
            "return_rate": dca_return_rate,
            "max_drawdown": dca_max_drawdown,
            "series": dca_value,
            "investment_dates": dca_investment_dates
        },
        "threshold": {
            "name": "阈值策略",
            "final_value": thr_final_value,
            "total_invested": total_thr_invested,
            "return_rate": thr_return_rate,
            "max_drawdown": thr_max_drawdown,
            "series": threshold_value,
            "transactions": thr_transactions
        }
    }
    return results

# --- UI Layout ---
st.title("📈 交互式基金阈值策略分析器")
st.markdown("这是一个基于Web界面的基金投资策略分析工具，您可以自定义参数，回测不同策略的表现。")

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("⚙️ 分析参数设置")

    st.subheader("1. 选择分析基金")
    st.markdown("""
    **热门基金参考:**
    - `161725` - 招商中证白酒指数(LOF)A
    - `110022` - 易方达消费行业股票
    - `000001` - 华夏成长混合
    - `012348` - 天弘恒生科技指数(QDII)A
    """)
    fund_code = st.text_input("输入6位基金代码", "161725")

    st.subheader("2. 设置分析时间范围")
    today = datetime.now().date()
    time_range_option = st.selectbox(
        "选择时间范围",
        ["最近1年", "最近2年", "最近3年", "2023年全年", "2022年全年", "自定义"]
    )

    end_date = today

    if time_range_option == "最近1年":
        start_date = today - timedelta(days=365)
    elif time_range_option == "最近2年":
        start_date = today - timedelta(days=730)
    elif time_range_option == "最近3年":
        start_date = today - timedelta(days=1095)
    elif time_range_option == "2023年全年":
        start_date = datetime(2023, 1, 1).date()
        end_date = datetime(2023, 12, 31).date()
    elif time_range_option == "2022年全年":
        start_date = datetime(2022, 1, 1).date()
        end_date = datetime(2022, 12, 31).date()
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", today - timedelta(days=365))
        with col2:
            end_date = st.date_input("结束日期", today)

    st.subheader("3. 设置阈值策略参数")
    strategy_option = st.radio(
        "选择策略类型",
        ["保守策略", "积极策略", "激进策略", "自定义"],
        captions=[
            "买入:-8%, 卖出:15%, 回顾:30天",
            "买入:-5%, 卖出:10%, 回顾:20天",
            "买入:-3%, 卖出:8%, 回顾:15天",
            "手动设置以下参数"
        ],
        index=1, horizontal=True
    )

    if strategy_option == "保守策略":
        buy_threshold, sell_threshold, lookback_period = -8.0, 15.0, 30
    elif strategy_option == "积极策略":
        buy_threshold, sell_threshold, lookback_period = -5.0, 10.0, 20
    elif strategy_option == "激进策略":
        buy_threshold, sell_threshold, lookback_period = -3.0, 8.0, 15
    else:
        buy_threshold = st.number_input("买入阈值 (%)", min_value=-50.0, max_value=-0.1, value=-5.0, step=0.1, help="下跌多少百分比时买入，必须为负数。")
        sell_threshold = st.number_input("卖出阈值 (%)", min_value=0.1, max_value=50.0, value=10.0, step=0.1, help="上涨多少百分比时卖出，必须为正数。")
        lookback_period = st.number_input("回顾期 (天)", min_value=5, max_value=100, value=20, step=1, help="计算收益率的天数，建议10-60天。")

    st.subheader("4. 设置定投策略参数")
    dca_freq = st.radio(
        "定投频率",
        ["每月", "每周"],
        index=0, horizontal=True, help="“每月”指在指定日期或之后第一个交易日定投；“每周”指在指定周几或之后第一个交易日定投。"
    )
    if dca_freq == '每月':
        dca_day = st.number_input("定投日 (1-28)", min_value=1, max_value=28, value=1, step=1)
    else:
        dca_day = st.selectbox("定投日", ["周一", "周二", "周三", "周四", "周五"], index=0)

    st.subheader("5. 设置投资金额")
    dca_amount = st.number_input("每次定投金额 (元)", min_value=100, value=1000, step=100)
    threshold_buy_amount = st.number_input("每次阈值买入金额 (元)", min_value=100, value=10000, step=100)

    start_button = st.button("🚀 开始回测分析", use_container_width=True)

    st.divider()

    st.header("🎯 今日操作指导")
    estimated_nav = st.number_input("输入今日预估净值", min_value=0.0, value=0.7810, format="%.4f", step=0.0001, help="输入您获取到的今日基金预估净值。")
    get_advice_button = st.button("获取操作建议", use_container_width=True)

# --- Main Panel for Results ---
if start_button:
    with st.spinner(f"正在获取基金 {fund_code} 的数据..."):
        fund_name = get_fund_name(fund_code)
        fund_data = get_fund_data(fund_code, start_date, end_date)

    if fund_data is None or fund_data.empty:
        st.error("无法获取到指定时间范围的基金数据，请检查基金代码或调整时间范围。")
    else:
        fund_data.index.name = '净值日期'
        st.success(f"成功获取 **{fund_name} ({fund_code})** 从 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 的数据。")

        with st.spinner("正在进行策略回测..."):
            results = run_backtest(fund_data, dca_amount, threshold_buy_amount, buy_threshold, sell_threshold, lookback_period, dca_freq, dca_day)

        st.header("📊 分析结果展示")

        st.subheader("策略对比")
        col1, col2 = st.columns(2)
        dca_results = results['dca']
        thr_results = results['threshold']
        
        with col1:
            st.metric(
                label=f"**{dca_results['name']}**",
                value=f"{dca_results['final_value']:,.2f} 元",
                delta=f"总回报率: {dca_results['return_rate']:.2f}%"
            )
            st.markdown(f"<small>总投入: {dca_results['total_invested']:,.2f} 元 | **最大回撤**: <span style='color:red;'>{dca_results['max_drawdown']:.2f}%</span></small>", unsafe_allow_html=True)
        with col2:
            st.metric(
                label=f"**{thr_results['name']}**",
                value=f"{thr_results['final_value']:,.2f} 元",
                delta=f"总回报率: {thr_results['return_rate']:.2f}%"
            )
            st.markdown(f"<small>总投入: {thr_results['total_invested']:,.2f} 元 | **最大回撤**: <span style='color:red;'>{thr_results['max_drawdown']:.2f}%</span></small>", unsafe_allow_html=True)

        fig_value = go.Figure()
        fig_value.add_trace(go.Scatter(x=dca_results['series'].index, y=dca_results['series'].values, mode='lines', name=dca_results['name']))
        fig_value.add_trace(go.Scatter(x=thr_results['series'].index, y=thr_results['series'].values, mode='lines', name=thr_results['name']))
        fig_value.update_layout(title="投资组合价值走势对比", xaxis_title="日期", yaxis_title="价值 (元)", legend=dict(x=0.01, y=0.99))
        st.plotly_chart(fig_value, use_container_width=True)

        st.subheader("阈值策略详细分析")
        
        fig_trades = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_trades.add_trace(go.Scatter(x=thr_results['series'].index, y=thr_results['series'].values, mode='lines', name='策略价值'), secondary_y=False)
        
        fig_trades.add_trace(go.Scatter(x=fund_data.index, y=fund_data['单位净值'], mode='lines', name='基金净值', line=dict(color='gray', dash='dash')), secondary_y=True)

        thr_transactions = thr_results['transactions']
        if thr_transactions:
            buy_dates = [t['date'] for t in thr_transactions if t['type'] == '买入']
            buy_prices = [fund_data['单位净值'].loc[d] for d in buy_dates]
            
            sell_dates = [t['date'] for t in thr_transactions if t['type'] == '卖出']
            sell_prices = [fund_data['单位净值'].loc[d] for d in sell_dates]

            fig_trades.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers', name='买入点', marker=dict(color='red', size=10, symbol='triangle-up')), secondary_y=True)
            fig_trades.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode='markers', name='卖出点', marker=dict(color='green', size=10, symbol='triangle-down')), secondary_y=True)

        dca_investment_dates = results['dca']['investment_dates']
        if not dca_investment_dates.empty:
            valid_dca_dates = dca_investment_dates[dca_investment_dates.isin(fund_data.index)]
            if not valid_dca_dates.empty:
                dca_prices = fund_data['单位净值'].loc[valid_dca_dates]
                fig_trades.add_trace(go.Scatter(x=valid_dca_dates, y=dca_prices, mode='markers', name='定投买入点', marker=dict(color='purple', size=8, symbol='diamond')), secondary_y=True)

        fig_trades.update_layout(title="阈值策略详细分析：价值走势与买卖点", xaxis_title="日期", legend=dict(x=0.01, y=0.99))
        fig_trades.update_yaxes(title_text="策略价值 (元)", secondary_y=False)
        fig_trades.update_yaxes(title_text="基金单位净值", secondary_y=True)
        st.plotly_chart(fig_trades, use_container_width=True)
        
        if thr_transactions:
            st.write("**交易记录:**")
            trans_df = pd.DataFrame(thr_transactions)
            trans_df['date'] = trans_df['date'].dt.strftime('%Y-%m-%d')
            trans_df['reference_date'] = trans_df['reference_date'].dt.strftime('%Y-%m-%d')
            trans_df = trans_df.rename(columns={
                'date': '日期', 'type': '类型', 'price': '成交净值', 
                'shares': '份额', 'value': '成交金额(元)', 'reason': '触发说明',
                'reference_nav': '参考净值', 'reference_date': '参考净值日期'
            })
            trans_df['成交金额(元)'] = trans_df['成交金额(元)'].map('{:,.2f}'.format)
            trans_df['参考净值'] = trans_df['参考净值'].map('{:.4f}'.format)
            st.dataframe(trans_df[['日期', '类型', '成交净值', '参考净值', '参考净值日期', '份额', '成交金额(元)', '触发说明']].set_index('日期'), use_container_width=True)
        else:
            st.info("在分析周期内，没有发生任何买入或卖出交易。")

        st.subheader("💡 智能投资建议")
        if thr_results['return_rate'] > dca_results['return_rate']:
            st.success(f"在此期间，阈值策略的表现优于定投策略，收益率高出 {thr_results['return_rate'] - dca_results['return_rate']:.2f}%。")
            if thr_transactions:
                st.info("该策略通过积极的买卖操作，成功捕捉了市场的波动，实现了超额收益。")
            else:
                st.warning("尽管阈值策略表现更好，但在整个期间内没有触发任何交易。这可能意味着市场波动未达到您设定的阈值。")
        else:
            st.warning(f"在此期间，定投策略的表现优于阈值策略，收益率高出 {dca_results['return_rate'] - thr_results['return_rate']:.2f}%。")
            st.info("这可能意味着市场处于持续上涨的趋势中，任何卖出操作都可能错失后续的增长。对于趋势性行情，定投或一次性买入持有可能是更好的选择。")

        st.markdown("""
        ---
        **⚠️ 重要提示:**
        - **历史不代表未来**: 本分析基于历史数据，不构成未来投资的保证。
        - **成本未计入**: 分析未考虑交易手续费、滑点等实际成本。
        - **市场风险**: 投资有风险，入市需谨慎。
        """)

if get_advice_button:
    if not fund_code or estimated_nav <= 0:
        st.warning("请输入有效的基金代码和今日预估净值。")
    else:
        with st.spinner("正在计算操作建议..."):
            try:
                today = datetime.now().date()
                reference_date_target = today - timedelta(days=lookback_period)

                hist_data_raw = ak.fund_open_fund_info_em(fund_code, indicator="单位净值走势")
                hist_data_raw['净值日期'] = pd.to_datetime(hist_data_raw['净值日期']).dt.date
                
                reference_data = hist_data_raw[hist_data_raw['净值日期'] <= reference_date_target].sort_values(
                    by='净值日期', ascending=False
                )

                if reference_data.empty:
                    st.error(f"无法找到 {reference_date_target.strftime('%Y-%m-%d')} 或之前的有效净值数据，无法计算建议。")
                else:
                    reference_row = reference_data.iloc[0]
                    reference_nav = pd.to_numeric(reference_row['单位净值'])
                    reference_date = reference_row['净值日期']

                    estimated_return = (estimated_nav / reference_nav - 1) * 100

                    advice = "持仓观望"
                    advice_color = "orange"
                    
                    if estimated_return <= buy_threshold:
                        advice = "建议买入"
                        advice_color = "red"
                    elif estimated_return >= sell_threshold:
                        advice = "建议卖出"
                        advice_color = "green"

                    st.header(f"今日操作建议: :{advice_color}[{advice}]")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("预估净值", f"{estimated_nav:.4f}")
                    with col2:
                        st.metric("预估回顾期收益率", f"{estimated_return:.2f}%")

                    with st.expander("查看计算详情"):
                        st.markdown(f"""
                        - **今日 ({today.strftime('%Y-%m-%d')}) 预估净值**: `{estimated_nav:.4f}`
                        - **参考净值日期**: `{reference_date.strftime('%Y-%m-%d')}`
                        - **参考净值**: `{reference_nav:.4f}`
                        - **回顾期**: `{lookback_period}` 天
                        - **买入阈值**: `{buy_threshold}%`
                        - **卖出阈值**: `{sell_threshold}%`
                        ---
                        **计算公式**: 
                        
                        `(`今日预估净值 `/` 参考净值 `- 1) * 100`
                        
                        `({estimated_nav:.4f} / {reference_nav:.4f} - 1) * 100 = {estimated_return:.2f}%`
                        """)
                        
                        if advice == "建议买入":
                            st.success(f"计算出的收益率 **{estimated_return:.2f}%** 小于或等于您的买入阈值 **{buy_threshold}%**，触发买入信号。")
                        elif advice == "建议卖出":
                            st.success(f"计算出的收益率 **{estimated_return:.2f}%** 大于或等于您的卖出阈值 **{sell_threshold}%**，触发卖出信号。")
                        else:
                            st.info(f"计算出的收益率 **{estimated_return:.2f}%** 在您的买卖阈值 `({buy_threshold}%, {sell_threshold}%)` 之间，未触发交易信号。")

            except Exception as e:
                st.error(f"计算建议时发生错误: {e}")