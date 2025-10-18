from .notifier import send_email_notification
import logging
from typing import Dict

# A dictionary to keep track of notifications sent for each fund on the current day
# to avoid sending duplicate alerts.
# The key is fund_code, value is 'buy' or 'sell'
g_sent_notifications: Dict[str, str] = {}

def reset_sent_notifications():
    """Resets the notification tracker. Should be called once a day."""
    global g_sent_notifications
    g_sent_notifications.clear()
    logging.info("每日通知状态已重置。")

def check_and_notify(fund_config: Dict[str, any], fund_data: Dict[str, any], app_config: Dict[str, any]):
    """
    Checks the fund data against the strategy and sends a notification if triggered.

    Args:
        fund_config: Configuration for the specific fund (code, thresholds).
        fund_data: The latest data fetched for the fund.
        app_config: The global application configuration.
    """
    fund_code = fund_data['fundcode']
    fund_name = fund_data['name']
    gszzl = float(fund_data['gszzl'])  # Estimated percentage change
    gsz = fund_data['gsz'] # Estimated value
    gztime = fund_data['gztime'] # Estimation time

    buy_threshold = fund_config['buy_threshold']
    sell_threshold = fund_config['sell_threshold']
    
    notification_type = None

    # Check buy signal
    if gszzl <= buy_threshold:
        if g_sent_notifications.get(fund_code) != 'buy':
            notification_type = 'buy'
            g_sent_notifications[fund_code] = 'buy'

    # Check sell signal
    elif gszzl >= sell_threshold:
        if g_sent_notifications.get(fund_code) != 'sell':
            notification_type = 'sell'
            g_sent_notifications[fund_code] = 'sell'

    if notification_type:
        action_text = "买入" if notification_type == 'buy' else "卖出"
        subject = f"基金交易提醒：【建议{action_text}】{fund_name}"
        content = f"""
        <html>
        <body>
            <h2>基金交易提醒</h2>
            <p><b>基金名称：</b>{fund_name} ({fund_code})</p>
            <p><b>操作建议：<font color='{"red" if action_text == "卖出" else "green"}'>{action_text}</font></b></p>
            <p><b>当前估算涨跌幅：</b><font color='{"red" if gszzl > 0 else "green"}'>{gszzl}%</font></p>
            <p><b>当前估算净值：</b>{gsz}</p>
            <p><b>数据时间：</b>{gztime}</p>
            <hr>
            <p><small>本邮件由基金监控程序自动发送，仅供参考，不构成投资建议。</small></p>
        </body>
        </html>
        """
        logging.info(f"基金 {fund_name} ({fund_code}) 触发 {action_text} 条件，准备发送邮件。")
        send_email_notification(app_config, subject, content)