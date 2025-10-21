# -*- coding: utf-8 -*-
"""
数据管理模块：负责获取和管理历史数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime

def get_trade_cal(start_date: str, end_date: str) -> pd.DatetimeIndex:
    """
    获取指定范围内的所有A股交易日。

    Args:
        start_date (str): 开始日期, 格式 "YYYYMMDD".
        end_date (str): 结束日期, 格式 "YYYYMMDD".

    Returns:
        pd.DatetimeIndex: 交易日历的DatetimeIndex.
    """
    print("正在获取A股交易日历...")
    trade_cal_df = ak.tool_trade_date_hist_sina()
    trade_cal_df['trade_date'] = pd.to_datetime(trade_cal_df['trade_date'])
    
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    trade_cal = trade_cal_df[
        (trade_cal_df['trade_date'] >= start_dt) & 
        (trade_cal_df['trade_date'] <= end_dt)
    ]['trade_date']
    
    return pd.DatetimeIndex(trade_cal)

def get_fund_history(fund_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定基金在时间范围内的历史净值数据, 并与交易日对齐。

    Args:
        fund_code (str): 基金代码.
        start_date (str): 开始日期, 格式为 "YYYYMMDD".
        end_date (str): 结束日期, 格式为 "YYYYMMDD".

    Returns:
        pd.DataFrame: 包含历史数据的DataFrame, 如果获取失败则返回空的DataFrame.
    """
    try:
        # 1. 获取标准交易日历
        trade_cal = get_trade_cal(start_date, end_date)
        
        print(f"正在获取基金 {fund_code} 的全部历史数据...")
        # 根据 help 文档, 使用正确的函数和参数, 获取成立以来的所有数据
        fund_data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势", period="成立来")
        
        if fund_data.empty:
            print(f"未能获取到基金 {fund_code} 的数据。")
            return pd.DataFrame()

        # 2. 数据清洗和格式化
        fund_data['净值日期'] = pd.to_datetime(fund_data['净值日期'])
        
        # 3. 手动筛选指定日期范围的数据
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        fund_data = fund_data[(fund_data['净值日期'] >= start_dt) & (fund_data['净值日期'] <= end_dt)]

        if fund_data.empty:
            print(f"基金 {fund_code} 在指定时间范围 {start_date}-{end_date} 内无数据。")
            return pd.DataFrame()
            
        fund_data = fund_data.set_index('净值日期')
        
        # 4. 与交易日历进行重采样对齐
        fund_data = fund_data.reindex(trade_cal)
        
        # 5. 填充非交易日产生的NaN值 (修复 FutureWarning)
        fund_data = fund_data.ffill()
        fund_data = fund_data.bfill()

        # 6. 重命名和数据类型转换 (移除 '累计净值' 解决 KeyError)
        fund_data = fund_data.rename(columns={
            '单位净值': 'close',
            '日增长率': 'pct_change'
        })
        
        # 对于填充的行, 日增长率为0
        # akshare 返回的日增长率是带 % 的字符串，需要处理
        fund_data['pct_change'] = fund_data['pct_change'].astype(str).str.strip('%')
        fund_data['pct_change'] = pd.to_numeric(fund_data['pct_change'], errors='coerce').fillna(0.0) / 100.0
        
        # 确保 'close' 列是数字类型
        fund_data['close'] = pd.to_numeric(fund_data['close'], errors='coerce')
        
        # 重新计算日增长率以确保数据准确性
        fund_data['percent_change'] = fund_data['close'].pct_change() * 100
        fund_data['percent_change'] = fund_data['percent_change'].fillna(0.0)

        # 只保留需要的列
        fund_data = fund_data[['close', 'percent_change']]
        
        print(f"成功获取并处理了 {len(fund_data)} 条对齐后的数据。")
        return fund_data.sort_index(ascending=True)

    except Exception as e:
        print(f"获取基金 {fund_code} 数据时发生错误: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    try:
        from .config import TARGET_FUNDS, BACKTEST_START_DATE, BACKTEST_END_DATE
        
        if TARGET_FUNDS:
            test_fund = TARGET_FUNDS[0]
            history_data = get_fund_history(test_fund, BACKTEST_START_DATE, BACKTEST_END_DATE)
            
            if not history_data.empty:
                print("\n获取到的数据样本:")
                print(history_data.head())
                print("\n数据信息 (查看是否有缺失值):")
                history_data.info()
                # 检查国庆假期附近的数据
                print("\n检查2020年国庆节附近的数据:")
                print(history_data.loc['2020-09-28':'2020-10-12'])

    except ImportError:
        print("无法导入模块。如果要直接测试此文件，请在项目根目录下执行: python -m fund_backtester.data_manager")