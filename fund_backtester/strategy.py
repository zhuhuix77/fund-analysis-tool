# -*- coding: utf-8 -*-
"""
策略模块：定义各种投资策略 (手动实现，无外部依赖)
"""
import pandas as pd

# --- 辅助函数 ---
def _calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def _calculate_macd(data: pd.Series, fast_period: int, slow_period: int, signal_period: int):
    slow_ema = data.ewm(span=slow_period, adjust=False).mean()
    fast_ema = data.ewm(span=fast_period, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    return macd_line, signal_line

# --- 1. 均线交叉策略 ---
def ma_crossover_strategy(data: pd.DataFrame, short_window: int, long_window: int) -> pd.DataFrame:
    signals = pd.DataFrame(index=data.index)
    signals['short_ma'] = data['close'].rolling(window=short_window, min_periods=1).mean()
    signals['long_ma'] = data['close'].rolling(window=long_window, min_periods=1).mean()
    signals['position'] = 0.0
    signals.loc[signals.index[long_window:], 'position'] = (signals['short_ma'][long_window:] > signals['long_ma'][long_window:]).astype(float)
    signals['signal'] = signals['position'].diff()
    data_with_signals = data.copy()
    data_with_signals['short_ma'] = signals['short_ma']
    data_with_signals['long_ma'] = signals['long_ma']
    data_with_signals['signal'] = signals['signal'].fillna(0).infer_objects(copy=False)
    return data_with_signals

# --- 2. RSI 指标策略 ---
def rsi_strategy(data: pd.DataFrame, rsi_period: int, oversold_threshold: int, overbought_threshold: int) -> pd.DataFrame:
    signals = pd.DataFrame(index=data.index)
    signals['rsi'] = _calculate_rsi(data['close'], rsi_period)
    signals['prev_rsi'] = signals['rsi'].shift(1)
    buy_signals = (signals['rsi'] > oversold_threshold) & (signals['prev_rsi'] <= oversold_threshold)
    sell_signals = (signals['rsi'] < overbought_threshold) & (signals['prev_rsi'] >= overbought_threshold)
    signals['position'] = 0.0
    position = 0
    for i in range(len(signals)):
        if buy_signals.iloc[i]: position = 1
        elif sell_signals.iloc[i]: position = 0
        signals.loc[signals.index[i], 'position'] = position
    signals['signal'] = signals['position'].diff()
    data_with_signals = data.copy()
    data_with_signals['rsi'] = signals['rsi']
    data_with_signals['signal'] = signals['signal'].fillna(0).infer_objects(copy=False)
    return data_with_signals

# --- 3. 布林带策略 ---
def bollinger_bands_strategy(data: pd.DataFrame, window: int, std_dev: float) -> pd.DataFrame:
    signals = pd.DataFrame(index=data.index)
    middle_band = data['close'].rolling(window=window).mean()
    std = data['close'].rolling(window=window).std()
    signals['bbl'] = middle_band - (std * std_dev)
    signals['bbu'] = middle_band + (std * std_dev)
    signals['bbm'] = middle_band
    buy_signals = (data['close'] > signals['bbl']) & (data['close'].shift(1) <= signals['bbl'].shift(1))
    sell_signals = (data['close'] < signals['bbu']) & (data['close'].shift(1) >= signals['bbu'].shift(1))
    signals['position'] = 0.0
    position = 0
    for i in range(len(signals)):
        if buy_signals.iloc[i]: position = 1
        elif sell_signals.iloc[i]: position = 0
        signals.loc[signals.index[i], 'position'] = position
    signals['signal'] = signals['position'].diff()
    data_with_signals = data.copy()
    data_with_signals = pd.concat([data_with_signals, signals[['bbl', 'bbu', 'bbm']]], axis=1)
    data_with_signals['signal'] = signals['signal'].fillna(0).infer_objects(copy=False)
    return data_with_signals

# --- 4. MACD 策略 ---
def macd_strategy(data: pd.DataFrame, fast_period: int, slow_period: int, signal_period: int) -> pd.DataFrame:
    signals = pd.DataFrame(index=data.index)
    signals['macd'], signals['signal_line'] = _calculate_macd(data['close'], fast_period, slow_period, signal_period)
    signals['prev_macd'] = signals['macd'].shift(1)
    signals['prev_signal_line'] = signals['signal_line'].shift(1)
    buy_signals = (signals['macd'] > signals['signal_line']) & (signals['prev_macd'] <= signals['prev_signal_line'])
    sell_signals = (signals['macd'] < signals['signal_line']) & (signals['prev_macd'] >= signals['prev_signal_line'])
    signals['position'] = 0.0
    position = 0
    for i in range(len(signals)):
        if buy_signals.iloc[i]: position = 1
        elif sell_signals.iloc[i]: position = 0
        signals.loc[signals.index[i], 'position'] = position
    signals['signal'] = signals['position'].diff()
    data_with_signals = data.copy()
    data_with_signals['macd'] = signals['macd']
    data_with_signals['signal_line'] = signals['signal_line']
    data_with_signals['signal'] = signals['signal'].fillna(0).infer_objects(copy=False)
    return data_with_signals

# --- 5. 定期定额策略 (DCA) ---
def dca_strategy(data: pd.DataFrame, interval_days: int, amount: float) -> pd.DataFrame:
    """
    生成定期定额投资信号。
    信号列直接包含投资金额，而不是简单的 1.0 信号。
    """
    signals = pd.DataFrame(index=data.index)
    signals['signal'] = 0.0
    
    # 从第一个有效日期开始计算定投周期
    days_since_last_investment = interval_days 
    
    for i in range(len(signals)):
        if days_since_last_investment >= interval_days:
            signals.iloc[i, signals.columns.get_loc('signal')] = amount
            days_since_last_investment = 0
        days_since_last_investment += 1
        
    data_with_signals = data.copy()
    data_with_signals['signal'] = signals['signal']
    return data_with_signals

# --- 6. 回顾期价格变动阈值策略 ---
def threshold_strategy(data: pd.DataFrame, lookback_period: int, buy_threshold: float, sell_threshold: float) -> pd.DataFrame:
    """
    根据【当日净值】与【回顾期净值】的【价格变动百分比】生成交易信号。
    这完全遵循用户的最终定义，解决命名和逻辑混淆。
    """
    df = data.copy()
    
    # 1. 计算核心指标
    df['reference_nav'] = df['close'].shift(lookback_period)
    df['reference_date'] = df.index.to_series().shift(lookback_period)
    
    # 核心逻辑: 计算价格变动率, e.g., (1.1 / 1.5) - 1 = -0.2667
    df['price_change_pct'] = (df['close'] / df['reference_nav']) - 1
    
    # 2. 将UI传入的百分比阈值 (e.g., -5.0) 转换为比率 (e.g., -0.05)
    buy_threshold_ratio = buy_threshold / 100.0
    sell_threshold_ratio = sell_threshold / 100.0

    # 3. 生成信号，强制要求价格变动率是有效数字 (not NaN)
    df['signal'] = 0.0
    
    buy_condition = (df['price_change_pct'].notna()) & (df['price_change_pct'] <= buy_threshold_ratio)
    df.loc[buy_condition, 'signal'] = 1.0
    
    sell_condition = (df['price_change_pct'].notna()) & (df['price_change_pct'] >= sell_threshold_ratio)
    df.loc[sell_condition, 'signal'] = -1.0

    # 4. 为了UI显示，将原始的UI阈值(百分比)和计算出的比率都添加到DataFrame中
    df['buy_threshold_pct'] = buy_threshold
    df['sell_threshold_pct'] = sell_threshold
    
    return df