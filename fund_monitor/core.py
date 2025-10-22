import logging
from datetime import datetime, timedelta, date
import pandas as pd
import akshare as ak

from .data_fetcher import get_fund_data



def get_strategy_advice(fund_code: str, params: dict) -> dict:
    """
    Calculates the investment advice for a single fund based on its strategy.
    Returns a dictionary with all relevant data.
    """
    buy_threshold = params['buy_threshold']
    sell_threshold = params['sell_threshold']
    lookback_period = params['lookback_period']

    # 1. Get real-time estimated NAV
    realtime_data = get_fund_data(fund_code)
    if not realtime_data or 'gsz' not in realtime_data:
        logging.warning(f"[{fund_code}] 无法获取实时估值。")
        return {'status': '获取实时估值失败', 'name': fund_code}
    
    try:
        estimated_nav = float(realtime_data['gsz'])
        fund_name = realtime_data.get('name', fund_code)
    except (ValueError, KeyError):
        logging.error(f"[{fund_code}] 实时估值数据格式不正确: {realtime_data}")
        return {'status': '估值数据格式错误', 'name': fund_name}

    # 2. Get historical reference NAV, excluding non-trading days
    try:
        hist_data_raw = ak.fund_open_fund_info_em(fund_code, indicator="单位净值走势")
        hist_data_raw['净值日期'] = pd.to_datetime(hist_data_raw['净值日期']).dt.date
        
        today = datetime.now().date()
        
        # Filter for dates up to today and sort descending to get trading days in reverse order
        trading_days_data = hist_data_raw[hist_data_raw['净值日期'] <= today].sort_values(by='净值日期', ascending=False)

        # To go back `lookback_period` trading days, we access the element at index `lookback_period - 1`.
        # e.g., for 1 day lookback, we need the last closing price, which is at index 0.
        reference_index = lookback_period - 1

        if reference_index < 0:
            logging.warning(f"[{fund_code}] lookback_period 必须大于或等于 1。")
            return {'status': '回溯期参数错误', 'name': fund_name}

        if len(trading_days_data) <= reference_index:
            logging.warning(f"[{fund_code}] 历史数据不足，无法回溯 {lookback_period} 个交易日。")
            return {'status': '历史数据不足', 'name': fund_name}
            
        reference_row = trading_days_data.iloc[reference_index]
        reference_nav = pd.to_numeric(reference_row['单位净值'])
        reference_date = reference_row['净值日期']

    except Exception as e:
        logging.error(f"[{fund_code}] 获取历史参考净值时发生错误: {e}")
        return {'status': '获取历史净值失败', 'name': fund_name}


    # 3. Calculate estimated return and check strategy
    estimated_return = (estimated_nav / reference_nav - 1) * 100
    
    advice = "观望"
    color = "gray"
    if estimated_return <= buy_threshold:
        advice = "建议买入"
        color = "green"
    elif estimated_return >= sell_threshold:
        advice = "建议卖出"
        color = "red"

    return {
        'status': '成功',
        'name': fund_name,
        'code': fund_code,
        'est_return': estimated_return,
        'threshold': f"{buy_threshold}% / {sell_threshold}%",
        'advice': advice,
        'advice_color': color,
        'details': {
            'estimated_nav': estimated_nav,
            'gztime': realtime_data.get('gztime', 'N/A'),
            'reference_nav': reference_nav,
            'reference_date': reference_date,
            'lookback_period': lookback_period
        }
    }