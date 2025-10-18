import logging
from datetime import datetime, timedelta, date
import pandas as pd
import akshare as ak

from .data_fetcher import get_fund_data

def get_reference_nav(fund_code: str, lookback_period: int) -> tuple[float, date] | tuple[None, None]:
    """
    Gets the reference NAV and date from 'lookback_period' days ago.
    """
    try:
        today = datetime.now().date()
        # We need to fetch data from a bit further back to ensure we find a valid trading day
        start_date_for_fetch = today - timedelta(days=lookback_period + 30) 
        
        hist_data_raw = ak.fund_open_fund_info_em(fund_code, indicator="单位净值走势")
        hist_data_raw['净值日期'] = pd.to_datetime(hist_data_raw['净值日期']).dt.date
        
        # Find the most recent NAV date that is on or before the target reference date
        reference_date_target = today - timedelta(days=lookback_period)
        reference_data = hist_data_raw[hist_data_raw['净值日期'] <= reference_date_target].sort_values(by='净值日期', ascending=False)

        if reference_data.empty:
            logging.warning(f"[{fund_code}] 无法找到 {reference_date_target.strftime('%Y-%m-%d')} 或之前的净值数据。")
            return None, None
        
        reference_row = reference_data.iloc[0]
        reference_nav = pd.to_numeric(reference_row['单位净值'])
        reference_date = reference_row['净值日期']
        return reference_nav, reference_date

    except Exception as e:
        logging.error(f"[{fund_code}] 获取历史参考净值时发生错误: {e}")
        return None, None

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

    # 2. Get historical reference NAV
    reference_nav, reference_date = get_reference_nav(fund_code, lookback_period)
    if not reference_nav:
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