import json
import time
import sched
from datetime import datetime, date
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
g_decision_report_sent_date = date.min # Tracks if the daily decision report has been sent

# --- Core Modules ---
from fund_monitor.core import get_strategy_advice
from fund_monitor.notifier import send_email_notification

# --- Helper Functions ---
def load_user_config():
    """Loads user configuration from user_config.json."""
    try:
        with open('user_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def load_strategies():
    """Loads strategies from fund_strategies.json."""
    try:
        with open('fund_strategies.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def is_time_to_send_report():
    """Checks if it's time to send the decision report (weekday, after 14:45)."""
    now = datetime.now()
    is_weekday = now.weekday() < 5
    is_time = now.hour == 14 and now.minute >= 45
    return is_weekday and is_time

def send_decision_report(user_config):
    """
    Generates and sends the single daily decision report for all monitored funds.
    """
    global g_decision_report_sent_date
    today = date.today()
    
    logging.info("临近收盘，开始生成交易决策报告...")
    
    strategies = load_strategies()
    if not strategies:
        logging.info("没有配置监控策略，跳过发送决策报告。")
        g_decision_report_sent_date = today # Mark as "sent" to avoid re-checking
        return

    report_items = []
    for fund_code, params in strategies.items():
        advice_result = get_strategy_advice(fund_code, params)
        report_items.append(advice_result)
        time.sleep(1) # Be polite to API

    # Build HTML content
    html_rows = ""
    for item in report_items:
        if item['status'] != '成功':
            html_rows += f"<tr><td>{item['name']}</td><td colspan='3' style='color:red;'>{item['status']}</td></tr>"
        else:
            details = item['details']
            details_html = f"""
            <ul style="font-size: 0.9em; margin: 5px 0 0 20px; padding-left: 15px; list-style-type: circle; color: #333;">
                <li><b>今日估算净值:</b> {details['estimated_nav']:.4f} (于 {details['gztime']})</li>
                <li><b>参考净值日期:</b> {details['reference_date'].strftime('%Y-%m-%d')}</li>
                <li><b>参考净值:</b> {details['reference_nav']:.4f}</li>
                <li><b>回顾期:</b> {details['lookback_period']} 天</li>
            </ul>
            """
            html_rows += f"""
            <tr>
                <td>{item['name']} ({item['code']})</td>
                <td>{item['est_return']:.2f}%</td>
                <td>{item['threshold']}</td>
                <td>
                    <font color='{item['advice_color']}'><b>{item['advice']}</b></font>
                    <details style="margin-top: 5px;">
                        <summary style="cursor: pointer; font-size: 0.9em; color: #555;">计算详情</summary>
                        {details_html}
                    </details>
                </td>
            </tr>
            """

    html_content = f"""
    <html>
    <head>
        <style>
            table {{ border-collapse: collapse; width: 100%; font-family: sans-serif; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
            thead {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h2>基金交易决策报告 ({today.strftime('%Y-%m-%d')})</h2>
        <p>以下是您监控的所有基金在收盘前的决策参考：</p>
        <table>
            <thead>
                <tr><th>基金名称</th><th>估算回顾期收益率</th><th>买/卖阈值</th><th>操作建议与详情</th></tr>
            </thead>
            <tbody>{html_rows}</tbody>
        </table>
        <hr>
        <p><small>本邮件由 `monitor.py` 自动发送。</small></p>
    </body></html>
    """
    
    subject = f"基金交易决策报告 - {today.strftime('%Y-%m-%d')}"
    if send_email_notification(user_config, subject, html_content):
        logging.info("交易决策报告已成功发送。")
    else:
        logging.error("交易决策报告发送失败。")
        
    g_decision_report_sent_date = today

def monitor_job(scheduler, user_config):
    """The main monitoring job."""
    interval = user_config.get("monitoring_interval_seconds", 300)
    scheduler.enter(interval, 1, monitor_job, (scheduler, user_config))
    
    global g_decision_report_sent_date
    today = date.today()
    
    # If report for today has been sent, do nothing until tomorrow.
    if today == g_decision_report_sent_date:
        logging.info(f"今日 {today} 的决策报告已发送，暂停监控直到午夜。")
        return

    # Check if it's time to send the report.
    if is_time_to_send_report():
        send_decision_report(user_config)
    else:
        now = datetime.now()
        logging.info(f"当前时间 {now.strftime('%H:%M:%S')}，未到决策报告发送时间 (14:45)。")

def main():
    """Main function to start the monitor."""
    logging.info("基金监控提醒程序已启动。")
    user_config = load_user_config()
    if not user_config or 'email' not in user_config:
        logging.error("无法启动监控：邮箱配置不完整或未找到。请先在 app.py 界面完成配置。")
        return
    
    s = sched.scheduler(time.time, time.sleep)
    s.enter(1, 1, monitor_job, (s, user_config))
    s.run()

if __name__ == "__main__":
    main()