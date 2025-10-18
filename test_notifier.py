import json
import logging
from fund_monitor.notifier import send_email_notification

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_user_config():
    """Loads user configuration from user_config.json."""
    try:
        with open('user_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("错误：找不到 user_config.json 文件。请先在 app.py 的“监控与设置”页面完成配置并保存。")
        return None
    except json.JSONDecodeError:
        logging.error("错误：user_config.json 文件格式不正确。")
        return None

def main():
    """Loads config and sends a test email."""
    logging.info("开始发送测试邮件...")
    
    config = load_user_config()
    if not config or 'email' not in config:
        logging.error("无法发送测试邮件，因为邮箱配置不完整。")
        return

    subject = "【基金监控】这是一封测试邮件"
    content = """
    <html>
    <body>
        <h1>邮件配置测试成功！</h1>
        <p>如果您收到了这封邮件，说明您在 `app.py` 中配置的邮箱信息是正确的。</p>
        <p>现在您可以放心地运行 `python monitor.py` 来启动后台监控服务了。</p>
        <hr>
        <p><small>本邮件由 `test_notifier.py` 脚本自动发送。</small></p>
    </body>
    </html>
    """

    if send_email_notification(config, subject, content):
        logging.info("测试邮件已成功发送。请检查您的收件箱。")
    else:
        logging.error("测试邮件发送失败。请检查终端中的错误日志，并核对您在UI上填写的邮箱配置（特别是授权码）。")

if __name__ == "__main__":
    main()