import json
import logging
from datetime import date
import time

from fund_monitor.notifier import send_email_notification
from fund_monitor.core import get_strategy_advice # Import the core logic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_json_file(file_path, default_data=None):
    """通用 JSON 文件加载函数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logging.warning(f"警告：找不到或无法解析 {file_path} 文件。")
        return default_data if default_data is not None else {}

def test_decision_report(user_config, strategies):
    """模拟发送一封“交易决策报告”邮件"""
    if not strategies:
        logging.error("无法测试，因为 fund_strategies.json 中没有配置任何策略。")
        return
        
    logging.info("正在模拟发送一封“交易决策报告”邮件...")

    # We can use the real core logic to get advice for one fund
    # and create mock data for others to show variety.
    fund_code, params = next(iter(strategies.items()))
    first_item = get_strategy_advice(fund_code, params)

    report_items = [first_item]
    # Add some mock data for demonstration
    report_items.append({
        'status': '成功', 'name': '模拟基金B (卖出)', 'code': '000002', 'est_return': 12.34, 'threshold': '-5.0% / 10.0%', 'advice': '建议卖出', 'advice_color': 'red',
        'details': {'estimated_nav': 0.8567, 'gztime': '14:45:00', 'reference_nav': 0.7626, 'reference_date': date(2025, 9, 25), 'lookback_period': 20}
    })
    report_items.append({'status': '获取历史净值失败', 'name': '一个获取失败的基金'})
    
    html_rows = ""
    for item in report_items:
        if item['status'] != '成功':
            html_rows += f"<tr><td>{item['name']}</td><td colspan='3' style='color:red;'>{item['status']}</td></tr>"
        else:
            details = item['details']
            # Handle date object for strftime
            ref_date_str = details['reference_date'].strftime('%Y-%m-%d') if isinstance(details['reference_date'], date) else details['reference_date']
            details_html = f"""
            <ul style="font-size: 0.9em; margin: 5px 0 0 20px; padding-left: 15px; list-style-type: circle; color: #333;">
                <li><b>今日估算净值:</b> {details['estimated_nav']:.4f} (于 {details['gztime']})</li>
                <li><b>参考净值日期:</b> {ref_date_str}</li>
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

    today = date.today()
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
        <h2>基金交易决策报告 (模拟测试)</h2>
        <p>以下是您监控的所有基金在收盘前的决策参考 (此为模拟数据)：</p>
        <table>
            <thead>
                <tr><th>基金名称</th><th>估算回顾期收益率</th><th>买/卖阈值</th><th>操作建议与详情</th></tr>
            </thead>
            <tbody>{html_rows}</tbody>
        </table>
        <hr>
        <p><small>本邮件由 `test_strategy.py` 脚本自动发送。</small></p>
    </body></html>
    """
    
    subject = f"【模拟测试】基金交易决策报告 - {today.strftime('%Y-%m-%d')}"
    if send_email_notification(user_config, subject, html_content):
        logging.info("模拟的决策报告已成功发送。请检查您的收件箱。")
    else:
        logging.error("模拟的决策报告发送失败。")

def main():
    """主函数，提供用户选择"""
    user_config = load_json_file('user_config.json')
    strategies = load_json_file('fund_strategies.json')

    if not user_config or 'email' not in user_config or not user_config.get('email', {}).get('sender_email'):
        logging.error("无法开始测试：邮箱配置不完整或未找到。请先在 app.py 界面完成配置并保存。")
        return

    print("--- 基金监控邮件模拟测试 ---")
    print("此脚本将模拟发送一封“交易决策报告”邮件。")
    
    test_decision_report(user_config, strategies)

if __name__ == "__main__":
    main()