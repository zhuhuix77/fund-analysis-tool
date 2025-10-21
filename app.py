import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
import time
import base64
from datetime import date
from github import Github, UnknownObjectException

from fund_monitor.core import get_strategy_advice

# --- Page Configuration ---
st.set_page_config(
    page_title="基金策略分析与交易管理",
    page_icon="💼",
    layout="wide"
)

# --- Constants and File Paths ---
TRANSACTIONS_FILE = 'my_transactions.csv'
STRATEGIES_FILE = 'fund_strategies.json'

# --- GitHub Integration Functions ---
@st.cache_resource
def get_github_repo():
    """Initializes connection to the GitHub repo using secrets if available."""
    try:
        # Directly try to access secrets. This is the standard way for cloud deployment.
        github_token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["GITHUB_REPO_NAME"]
        g = Github(github_token)
        return g.get_repo(repo_name)
    except FileNotFoundError:
        # This error is expected in a local environment where secrets.toml does not exist.
        # We catch it and return None to signal that we are in "local mode".
        return None
    except Exception as e:
        # This catches other potential errors, like missing keys in an existing secrets file,
        # or network issues when connecting to GitHub.
        st.error(f"无法连接到 GitHub 仓库，请检查 Streamlit Secrets 配置: {e}")
        return None

def get_json_from_repo(repo, file_path):
    """Fetches and decodes a JSON file from the GitHub repo."""
    try:
        content_obj = repo.get_contents(file_path)
        decoded_content = base64.b64decode(content_obj.content).decode('utf-8')
        return json.loads(decoded_content)
    except UnknownObjectException:
        return {} # File doesn't exist yet, return empty dict
    except Exception as e:
        st.error(f"从 GitHub 读取文件 {file_path} 失败: {e}")
        return {}

def save_json_to_repo(repo, file_path, data, commit_message):
    """Commits and pushes a JSON file to the GitHub repo."""
    try:
        json_content = json.dumps(data, indent=2, ensure_ascii=False)
        
        try:
            # Check if file exists to get its SHA for update
            file_obj = repo.get_contents(file_path)
            repo.update_file(file_path, commit_message, json_content, file_obj.sha)
            st.success(f"策略文件已成功同步到 GitHub！")
        except UnknownObjectException:
            # File doesn't exist, create it
            repo.create_file(file_path, commit_message, json_content)
            st.success(f"策略文件已成功创建并同步到 GitHub！")
        return True
    except Exception as e:
        st.error(f"同步策略文件到 GitHub 失败: {e}")
        return False

def load_strategies_from_local(file_path):
    """Loads strategies from a local JSON file."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"从本地文件 {file_path} 加载策略失败: {e}")
        return {}

def save_strategies_to_local(file_path, data):
    """Saves strategies to a local JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        st.success("策略已成功保存到本地文件！")
        return True
    except Exception as e:
        st.error(f"保存策略到本地文件 {file_path} 失败: {e}")
        return False

def load_transactions_from_file():
    """从 CSV 文件加载个人交易记录"""
    if not os.path.exists(TRANSACTIONS_FILE):
        return pd.DataFrame(columns=['date', 'fund_code', 'type', 'price', 'shares', 'value', 'reason'])
    try:
        # Ensure fund_code is read as a string to prevent type mismatches
        df = pd.read_csv(TRANSACTIONS_FILE, dtype={'fund_code': str})
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.error(f"从文件加载交易记录失败: {e}")
        return pd.DataFrame(columns=['date', 'fund_code', 'type', 'price', 'shares', 'value', 'reason'])

def save_transactions_to_file(df):
    """将个人交易记录保存到 CSV 文件"""
    try:

        df.to_csv(TRANSACTIONS_FILE, index=False)
    except Exception as e:
        st.error(f"保存交易记录到文件失败: {e}")

# 在应用启动时，从文件加载交易记录到 Session State
if 'transactions' not in st.session_state:
    st.session_state.transactions = load_transactions_from_file()

# Strategies are loaded based on environment (cloud vs. local)
if 'strategies' not in st.session_state:
    repo = get_github_repo()
    if repo:
        with st.spinner("正在从 GitHub 同步最新监控策略..."):
            st.session_state.strategies = get_json_from_repo(repo, STRATEGIES_FILE)
    else:
        st.info("未检测到 GitHub Secrets，将使用本地策略文件 `fund_strategies.json`。")
        st.session_state.strategies = load_strategies_from_local(STRATEGIES_FILE)

# --- Helper Functions ---
@st.cache_data
def get_trade_cal(start_date, end_date):
    """获取指定范围内的所有A股交易日。"""
    try:
        trade_cal_df = ak.tool_trade_date_hist_sina()
        trade_cal_df['trade_date'] = pd.to_datetime(trade_cal_df['trade_date'])
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        trade_cal = trade_cal_df[
            (trade_cal_df['trade_date'] >= start_dt) & 
            (trade_cal_df['trade_date'] <= end_dt)
        ]['trade_date']
        
        return pd.DatetimeIndex(trade_cal)
    except Exception as e:
        st.warning(f"获取交易日历失败: {e}. 将回退到使用周一至周五作为交易日。")
        return pd.bdate_range(start=start_date, end=end_date)

@st.cache_data
def get_fund_data(fund_code, start_date, end_date):
    """获取基金历史净值数据, 并严格对齐交易日"""
    try:
        # 1. 获取基金原始数据
        fund_data_raw = ak.fund_open_fund_info_em(fund_code, indicator="单位净值走势")
        if fund_data_raw.empty: return None
        
        fund_data_raw['净值日期'] = pd.to_datetime(fund_data_raw['净值日期'])
        fund_data = fund_data_raw.set_index('净值日期').sort_index()
        fund_data['单位净值'] = pd.to_numeric(fund_data['单位净值'])

        # 2. 获取标准交易日历
        cal_start = fund_data.index.min() if not fund_data.empty else start_date
        cal_end = fund_data.index.max() if not fund_data.empty else end_date
        trade_cal = get_trade_cal(cal_start, cal_end)
        
        # 3. 与交易日历进行重采样对齐
        fund_data = fund_data.reindex(trade_cal)
        
        # 4. 填充因基金暂停交易等原因在交易日产生的NaN值
        fund_data['单位净值'] = fund_data['单位净值'].ffill().bfill()
        
        # 5. 筛选回用户指定的日期范围
        fund_data = fund_data[(fund_data.index >= pd.to_datetime(start_date)) & (fund_data.index <= pd.to_datetime(end_date))]

        if fund_data.empty: return None

        # 6. 为了兼容后续代码，添加 is_trading_day 和 last_trading_date
        fund_data['is_trading_day'] = True
        fund_data['last_trading_date'] = fund_data.index.to_series()
        fund_data.index.name = '净值日期'
        
        return fund_data

    except Exception as e:
        st.error(f"获取基金数据时出错: {e}")
        return None

@st.cache_data
def get_fund_name(fund_code):
    """获取基金名称"""
    try:
        fund_list = ak.fund_name_em()
        return fund_list[fund_list['基金代码'] == fund_code]['基金简称'].iloc[0]
    except Exception:
        return "未知名称"

def calculate_max_drawdown(series):
    """计算最大回撤"""
    if series.empty or series.isna().all(): return 0.0
    cumulative_max = series.cummax()
    drawdown = (series - cumulative_max) / cumulative_max
    return drawdown.min() * 100 if pd.notna(drawdown.min()) else 0.0

def run_backtest(fund_data, dca_amount, threshold_buy_amount, buy_threshold, sell_threshold, lookback_period, dca_freq, dca_day):
    """运行回测并返回详细结果"""
    # ... [The existing run_backtest function remains unchanged] ...
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

    return {
        "dca": {"name": "定投策略", "final_value": dca_final_value, "total_invested": total_dca_invested, "return_rate": dca_return_rate, "max_drawdown": dca_max_drawdown, "series": dca_value, "investment_dates": dca_investment_dates},
        "threshold": {"name": "阈值策略", "final_value": thr_final_value, "total_invested": total_thr_invested, "return_rate": thr_return_rate, "max_drawdown": thr_max_drawdown, "series": threshold_value, "transactions": thr_transactions}
    }

# --- UI Layout ---
st.title("💼 基金策略分析与交易管理")

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("⚙️ 分析参数设置")
    st.subheader("1. 选择分析基金")
    fund_code = st.text_input("输入6位基金代码", "161725")
    
    st.subheader("2. 设置分析时间范围")
    today = datetime.now().date()
    start_date = st.date_input("开始日期", today - timedelta(days=365))
    end_date = st.date_input("结束日期", today)

    st.subheader("3. 设置阈值策略参数")
    buy_threshold = st.number_input("买入阈值 (%)", -50.0, -0.1, -5.0, 0.1)
    sell_threshold = st.number_input("卖出阈值 (%)", 0.1, 50.0, 10.0, 0.1)
    lookback_period = st.number_input("回顾期 (天)", 5, 100, 20, 1)

    st.subheader("4. 设置定投策略参数")
    dca_freq = st.radio("定投频率", ["每月", "每周"], 0, horizontal=True)
    if dca_freq == '每月':
        dca_day = st.number_input("定投日 (1-28)", 1, 28, 1, 1)
    else:
        dca_day = st.selectbox("定投日", ["周一", "周二", "周三", "周四", "周五"], 0)

    st.subheader("5. 设置投资金额")
    dca_amount = st.number_input("每次定投金额 (元)", 100, value=1000, step=100)
    threshold_buy_amount = st.number_input("每次阈值买入金额 (元)", 100, value=1000, step=100)

# --- Main Panel with Tabs ---
tab1, tab2, tab3 = st.tabs(["策略回测分析", "我的交易记录", "云端部署与监控"])

with tab1:
    st.header("🔍 策略回测与今日建议")

    # --- View State Management ---
    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'home' # 'home', 'backtest', 'advice'
    if 'backtest_results' not in st.session_state:
        st.session_state.backtest_results = None
    if 'backtest_fund_data' not in st.session_state: # Used to store the fund_data from backtest
        st.session_state.backtest_fund_data = None
    if 'backtest_fund_code' not in st.session_state: # Used to store the fund_code from backtest
        st.session_state.backtest_fund_code = None

    col_run, col_advice = st.columns(2)
    with col_run:
        if st.button("🚀 开始回测分析", use_container_width=True):
            st.session_state.current_view = 'backtest'
    with col_advice:
        if st.button("🎯 获取今日操作建议", use_container_width=True):
            st.session_state.current_view = 'advice'
    
    estimated_nav_input = st.number_input("输入今日预估净值 (用于获取建议)", 0.0, value=0.7810, format="%.4f", step=0.0001)

    if st.session_state.current_view == 'backtest':
        # ... [Existing backtesting logic and display] ...
        with st.spinner(f"正在获取基金 {fund_code} 的数据..."):
            fund_name = get_fund_name(fund_code)
            fund_data = get_fund_data(fund_code, start_date, end_date)
        if fund_data is None or fund_data.empty:
            st.error("无法获取到指定时间范围的基金数据。")
        else:
            st.success(f"成功获取 **{fund_name} ({fund_code})** 数据。")
            with st.spinner("正在进行策略回测..."):
                results = run_backtest(fund_data, dca_amount, threshold_buy_amount, buy_threshold, sell_threshold, lookback_period, dca_freq, dca_day)
                # Store results and context for tab2
                st.session_state.backtest_results = results
                st.session_state.backtest_fund_data = fund_data.copy()
                st.session_state.backtest_fund_code = fund_code
            st.subheader("📊 分析结果展示")

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
                st.markdown(f"<small>净投入 <span title='策略从外部引入的总资金，不包含盈利再投的部分'>(?):</span> {thr_results['total_invested']:,.2f} 元 | **最大回撤**: <span style='color:red;'>{thr_results['max_drawdown']:.2f}%</span></small>", unsafe_allow_html=True)

            fig_value = go.Figure()
            fig_value.add_trace(go.Scatter(x=dca_results['series'].index, y=dca_results['series'].values, mode='lines', name=dca_results['name']))
            fig_value.add_trace(go.Scatter(x=thr_results['series'].index, y=thr_results['series'].values, mode='lines', name=thr_results['name']))
            fig_value.update_layout(title="投资组合价值走势对比", xaxis_title="日期", yaxis_title="价值 (元)", legend=dict(x=0.01, y=0.99))
            st.plotly_chart(fig_value, use_container_width=True)

            with st.expander("💡 指标计算逻辑说明"):
                st.markdown("#### 核心指标如何计算？")
                
                st.markdown("""
                **1. 最终总价值 (Final Value)**
                - **定义**: 策略在回测结束日期的总资产价值。
                - **计算**: `(期末持有份额 × 期末当日净值) + 期末持有现金`
                - **示例 (阈值策略)**: 最终价值为 **{:.2f}** 元。
                """.format(thr_results['final_value']))

                st.markdown("""
                **2. 总投入成本 (Total Invested)**
                - **定投策略**: 简单地将每次的投资金额累加。
                  - **计算**: `每次定投金额 × 定投总次数`
                  - **示例**: `{} 元 × {} 次 = ` **{:.2f}** 元。
                - **阈值策略**: 只计算策略从"外部"拿钱的总额 (净投入)，卖出盈利后的再投资不计入成本。
                  - **计算**: 仅在策略持有的现金不足以支付当次买入时，从外部补充的资金才计入总投入。
                  - **示例**: 本次策略净投入为 **{:.2f}** 元。
                """.format(dca_amount, len(dca_results['investment_dates']), dca_results['total_invested'], thr_results['total_invested']))

                st.markdown("""
                **3. 总回报率 (Total Return Rate)**
                - **定义**: 衡量策略盈利能力的核心指标。
                - **计算**: `(最终总价值 / 总投入成本 - 1) * 100%`
                - **示例 (阈值策略)**: `({:.2f} / {:.2f} - 1) * 100% = ` **{:.2f}%**
                """.format(thr_results['final_value'], thr_results['total_invested'] if thr_results['total_invested'] > 0 else 1, thr_results['return_rate']))

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
            
            # --- Add to Monitor Button ---
            st.info("如果觉得当前参数下的阈值策略表现良好，可以一键将其加入后台监控。")
            if st.button("📈 将此策略加入后台监控 (自动同步到 GitHub)", key=f"add_strat_{fund_code}", use_container_width=True):
                strategy_key = fund_code
                strategy_data = {
                    "buy_threshold": buy_threshold,
                    "sell_threshold": sell_threshold,
                    "lookback_period": lookback_period
                }
                st.session_state.strategies[strategy_key] = strategy_data
                repo = get_github_repo()
                if repo:
                    save_json_to_repo(repo, STRATEGIES_FILE, st.session_state.strategies, f"Add/Update strategy for {fund_code}")
                else:
                    save_strategies_to_local(STRATEGIES_FILE, st.session_state.strategies)

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

    if st.session_state.current_view == 'advice':
        if not fund_code or estimated_nav_input <= 0:
            st.warning("请输入有效的基金代码和今日预估净值。")
        else:
            # --- Part 1: Calculate and Display Advice ---
            with st.spinner("正在计算操作建议..."):
                try:
                    today = datetime.now().date()
                    # 获取所有历史数据，并按日期排序
                    hist_data_raw = ak.fund_open_fund_info_em(fund_code, indicator="单位净值走势")
                    hist_data_raw['净值日期'] = pd.to_datetime(hist_data_raw['净值日期']).dt.date
                    past_data = hist_data_raw[hist_data_raw['净值日期'] < today].sort_values(by='净值日期', ascending=True)

                    if len(past_data) < lookback_period:
                        st.error(f"历史数据不足 {lookback_period} 个交易日，无法计算建议。")
                    else:
                        # 获取倒数第 N 个交易日的数据作为参考点
                        reference_row = past_data.iloc[-lookback_period]
                        reference_nav = pd.to_numeric(reference_row['单位净值'])
                        reference_date = reference_row['净值日期']
                        estimated_return = (estimated_nav_input / reference_nav - 1) * 100
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
                            st.metric("预估净值", f"{estimated_nav_input:.4f}")
                        with col2:
                            st.metric("预估回顾期收益率", f"{estimated_return:.2f}%")

                        with st.expander("查看计算详情"):
                            st.markdown(f"""
                            - **今日 ({today.strftime('%Y-%m-%d')}) 预估净值**: `{estimated_nav_input:.4f}`
                            - **参考净值日期**: `{reference_date.strftime('%Y-%m-%d')}`
                            - **参考净值**: `{reference_nav:.4f}`
                            - **回顾期**: `{lookback_period}` 天
                            - **买入阈值**: `{buy_threshold}%`
                            - **卖出阈值**: `{sell_threshold}%`
                            ---
                            **计算公式**: `(`今日预估净值 `/` 参考净值 `- 1) * 100`
                            `({estimated_nav_input:.4f} / {reference_nav:.4f} - 1) * 100 = {estimated_return:.2f}%`
                            """)
                            if advice == "建议买入":
                                st.success(f"计算出的收益率 **{estimated_return:.2f}%** 小于或等于您的买入阈值 **{buy_threshold}%**，触发买入信号。")
                            elif advice == "建议卖出":
                                st.success(f"计算出的收益率 **{estimated_return:.2f}%** 大于或等于您的卖出阈值 **{sell_threshold}%**，触发卖出信号。")
                            else:
                                st.info(f"计算出的收益率 **{estimated_return:.2f}%** 在您的买卖阈值 `({buy_threshold}%, {sell_threshold}%)` 之间，未触发交易信号。")
                except Exception as e:
                    st.error(f"计算建议时发生错误: {e}")

        # --- Part 2: Display and Process Transaction Form ---
        st.subheader("✍️ 记录您的交易")
        with st.form("transaction_form"):
            buy_amount_input = st.number_input("买入金额 (元)", min_value=0.0, step=100.0)
            sell_shares_input = st.number_input("卖出份额", min_value=0.0, step=0.01)
            submitted = st.form_submit_button("✔️ 确认并记录交易")

            if submitted:
                trans_type = None
                if buy_amount_input > 0 and sell_shares_input > 0:
                    st.error("不能同时输入买入金额和卖出份额。")
                elif buy_amount_input > 0:
                    if estimated_nav_input <= 0:
                        st.error("无法记录交易，因为预估净值为0或负数。")
                    else:
                        trans_type = '买入'
                        trans_value = buy_amount_input
                        trans_shares = buy_amount_input / estimated_nav_input
                        reason = f"手动买入 (预估净值: {estimated_nav_input:.4f})"
                elif sell_shares_input > 0:
                    if estimated_nav_input <= 0:
                        st.error("无法记录交易，因为预估净值为0或负数。")
                    else:
                        trans_type = '卖出'
                        trans_shares = sell_shares_input
                        trans_value = sell_shares_input * estimated_nav_input
                        reason = f"手动卖出 (预估净值: {estimated_nav_input:.4f})"
                else:
                    st.warning("请输入买入金额或卖出份额。")

                if trans_type:
                    new_transaction = pd.DataFrame([{
                        'date': pd.to_datetime(datetime.now().date()),
                        'fund_code': fund_code,
                        'type': trans_type,
                        'price': estimated_nav_input,
                        'shares': trans_shares,
                        'value': trans_value,
                        'reason': reason
                    }])
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_transaction], ignore_index=True)
                    save_transactions_to_file(st.session_state.transactions)
                    st.success(f"✅ {trans_type} 交易记录成功！请切换到“我的交易记录”标签页查看。")
                    st.balloons()

with tab2:
    st.header("📈 我的交易记录与持仓分析")
    # 直接从 Session State 读取数据，确保实时性
    my_trans_df = st.session_state.transactions

    if my_trans_df.empty:
        st.info("您还没有任何交易记录。请在“策略回测分析”标签页的“今日操作建议”部分录入您的第一笔交易。")
    else:
        st.subheader("所有交易记录")
        st.dataframe(my_trans_df.sort_values('date', ascending=False).style.format({
            'price': '{:.4f}', 'shares': '{:,.2f}', 'value': '{:,.2f}'
        }), use_container_width=True)

        st.subheader("持仓分析")
        fund_codes_in_log = my_trans_df['fund_code'].unique()
        selected_fund_code = st.selectbox("选择要分析的基金", fund_codes_in_log)

        if selected_fund_code:
            selected_fund_trans = my_trans_df[my_trans_df['fund_code'] == selected_fund_code].copy()
            # Normalize transaction dates to midnight to match historical data index
            selected_fund_trans['date'] = pd.to_datetime(selected_fund_trans['date']).dt.normalize()

            try:
                latest_nav_data = ak.fund_open_fund_info_em(selected_fund_code, indicator="单位净值走势").iloc[-1]
                latest_nav = pd.to_numeric(latest_nav_data['单位净值'])
                latest_nav_date = pd.to_datetime(latest_nav_data['净值日期']).strftime('%Y-%m-%d')
                
                buy_shares = selected_fund_trans[selected_fund_trans['type'] == '买入']['shares'].sum()
                sell_shares = selected_fund_trans[selected_fund_trans['type'] == '卖出']['shares'].sum()
                total_shares = buy_shares - sell_shares

                buy_cost = selected_fund_trans[selected_fund_trans['type'] == '买入']['value'].sum()
                sell_value = selected_fund_trans[selected_fund_trans['type'] == '卖出']['value'].sum()
                
                current_market_value = total_shares * latest_nav
                total_profit = current_market_value + sell_value - buy_cost
                return_rate = (total_profit / buy_cost) * 100 if buy_cost > 0 else 0

                st.markdown(f"**{get_fund_name(selected_fund_code)} ({selected_fund_code})** 的持仓详情 (最新净值: {latest_nav:.4f} @ {latest_nav_date})")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("当前总持仓份额", f"{total_shares:,.2f}")
                col2.metric("持仓总市值 (元)", f"{current_market_value:,.2f}")
                col3.metric("累计投入成本 (元)", f"{buy_cost:,.2f}")

                col4, col5 = st.columns(2)
                col4.metric("累计收益 (元)", f"{total_profit:,.2f}", delta=f"{total_profit:,.2f} 元")
                col5.metric("累计回报率 (%)", f"{return_rate:.2f}%", delta=f"{return_rate:.2f}%")

                st.subheader("交易择时复盘：实际操作 vs. 策略信号")
                
                # --- Smartly load fund data for chart ---
                # Priority 1: Use data from backtest if fund code matches
                if (st.session_state.backtest_fund_code == selected_fund_code and 
                    st.session_state.backtest_fund_data is not None):
                    hist_data = st.session_state.backtest_fund_data.copy()
                    st.info("图表背景已加载前序回测数据，以供精确对比。")
                # Priority 2: Fetch data based on personal transaction history
                else:
                    min_date = selected_fund_trans['date'].min().date()
                    hist_data = get_fund_data(selected_fund_code, min_date, datetime.now().date())
                
                if hist_data is not None:
                    # --- Create Figure ---
                    fig = go.Figure()
                    
                    # Plot 1: Fund NAV (Main Curve)
                    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['单位净值'], mode='lines', name='基金净值', line=dict(color='cornflowerblue', width=2)))
                    
                    # Plot 2: User's Real Buy/Sell Points (on NAV Curve)
                    my_buy_points = selected_fund_trans[selected_fund_trans['type'] == '买入']
                    my_sell_points = selected_fund_trans[selected_fund_trans['type'] == '卖出']
                    
                    valid_my_buys = my_buy_points[my_buy_points['date'].isin(hist_data.index)]
                    if not valid_my_buys.empty:
                        fig.add_trace(go.Scatter(x=valid_my_buys['date'], y=hist_data.loc[valid_my_buys['date'], '单位净值'], mode='markers', name='我的买入点', marker=dict(color='red', size=10, symbol='triangle-up')))

                    valid_my_sells = my_sell_points[my_sell_points['date'].isin(hist_data.index)]
                    if not valid_my_sells.empty:
                        fig.add_trace(go.Scatter(x=valid_my_sells['date'], y=hist_data.loc[valid_my_sells['date'], '单位净值'], mode='markers', name='我的卖出点', marker=dict(color='green', size=10, symbol='triangle-down')))

                    # Plot 3: Backtest Strategy Signal Points (on NAV Curve)
                    if st.session_state.backtest_results:
                        # Check if the backtest fund code matches the currently analyzed fund
                        if st.session_state.backtest_fund_code == selected_fund_code:
                            thr_transactions = st.session_state.backtest_results['threshold']['transactions']
                            if thr_transactions:
                                strat_buy_dates = [t['date'] for t in thr_transactions if t['type'] == '买入']
                                strat_sell_dates = [t['date'] for t in thr_transactions if t['type'] == '卖出']

                                valid_strat_buys = [d for d in strat_buy_dates if d in hist_data.index]
                                if valid_strat_buys:
                                    fig.add_trace(go.Scatter(x=valid_strat_buys, y=hist_data.loc[valid_strat_buys, '单位净值'], mode='markers', name='策略建议买点', marker=dict(color='red', size=9, symbol='diamond-open')))
                                
                                valid_strat_sells = [d for d in strat_sell_dates if d in hist_data.index]
                                if valid_strat_sells:
                                    fig.add_trace(go.Scatter(x=valid_strat_sells, y=hist_data.loc[valid_strat_sells, '单位净值'], mode='markers', name='策略建议卖点', marker=dict(color='green', size=9, symbol='diamond-open')))
                        else:
                            st.warning("当前分析的基金与回测的基金不一致，无法显示策略建议点。")


                    # --- Finalize Layout ---
                    fig.update_layout(
                        title=f"交易择时复盘：实际操作 vs. 策略信号 ({selected_fund_code})",
                        xaxis_title="日期",
                        yaxis_title="基金单位净值 (元)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("无法获取用于绘制图表的基金历史数据。")

            except Exception as e:
                st.error(f"分析个人持仓时出错: {e}")

with tab3:
    st.header("⚙️ 云端部署与监控")
    st.info("""
    本应用已适配云端部署。后台监控任务 (`monitor.py`) 将通过 GitHub Actions 自动运行，您的机密信息（如邮箱密码、GitHub 令牌）将通过 Streamlit 和 GitHub 的 **Secrets** 功能进行安全管理。
    
    **在部署前，请务必仔细阅读 `DEPLOYMENT.md` 文件，并按照指南完成所有 Secrets 的配置。**
    """)

    # --- Real-time Dashboard ---
    st.subheader("实时监控看板")
    st.markdown("点击下方按钮，可实时获取当前所有监控策略的最新估值和操作建议。")

    if 'dashboard_results' not in st.session_state:
        st.session_state.dashboard_results = []

    if st.button("🔄 刷新实时数据", use_container_width=True):
        current_strategies = st.session_state.strategies
        if current_strategies:
            with st.spinner("正在获取所有监控中基金的最新估值和建议..."):
                results = []
                for fund_code, params in current_strategies.items():
                    advice_result = get_strategy_advice(fund_code, params)
                    results.append(advice_result)
                    time.sleep(1) # Be polite to API
                st.session_state.dashboard_results = results
        else:
            st.session_state.dashboard_results = []
            st.warning("您还没有添加任何监控策略，无法获取实时数据。")

    if st.session_state.dashboard_results:
        st.write("---")
        for advice_result in st.session_state.dashboard_results:
            if advice_result['status'] == '成功':
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**{advice_result['name']}** (`{advice_result['code']}`)")
                with col2:
                    st.metric(
                        label="估算回顾期收益率",
                        value=f"{advice_result['est_return']:.2f}%"
                    )
                with col3:
                    st.markdown(f"**操作建议: <font color='{advice_result['advice_color']}'>{advice_result['advice']}!</font>**", unsafe_allow_html=True)

                with st.expander(f"查看 {advice_result['code']} 计算详情"):
                    details = advice_result['details']
                    if isinstance(details.get('reference_date'), date):
                        details['reference_date'] = details['reference_date'].strftime('%Y-%m-%d')
                    st.json(details)
            else:
                st.error(f"**{advice_result.get('name', '未知基金')}**: {advice_result['status']}")
            st.divider()

    # --- Monitored Strategies ---
    st.subheader("当前监控的策略 (已同步到 GitHub)")
    if not st.session_state.strategies:
        st.warning("目前没有正在监控的策略。请在“策略回测分析”页面添加。")
    else:
        for fund_code, params in list(st.session_state.strategies.items()):
            fund_name = get_fund_name(fund_code)
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                st.markdown(f"**{fund_name}** (`{fund_code}`)")
            with col2:
                st.metric("买入阈值", f"{params['buy_threshold']}%")
            with col3:
                st.metric("卖出阈值", f"{params['sell_threshold']}%")
            with col4:
                st.metric("回顾期", f"{params['lookback_period']} 天")
            with col5:
                if st.button("🗑️", key=f"del_{fund_code}", help="删除此监控策略并同步到 GitHub"):
                    del st.session_state.strategies[fund_code]
                    repo = get_github_repo()
                    if repo:
                        save_json_to_repo(repo, STRATEGIES_FILE, st.session_state.strategies, f"Remove strategy for {fund_code}")
                    else:
                        save_strategies_to_local(STRATEGIES_FILE, st.session_state.strategies)
                    st.rerun()
            st.divider()