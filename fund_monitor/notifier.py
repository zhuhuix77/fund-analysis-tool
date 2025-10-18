import smtplib
from email.mime.text import MIMEText
from email.header import Header
import logging

def send_email_notification(config: dict, subject: str, content: str):
    """
    Sends an email notification.

    Args:
        config: The email configuration dictionary.
        subject: The subject of the email.
        content: The HTML content of the email.
    """
    try:
        email_config = config['email']
        sender = email_config['sender_email']
        password = email_config['password']
        receivers = email_config['receiver_emails']

        # Create the email message
        message = MIMEText(content, 'html', 'utf-8')
        message['From'] = Header(f"基金监控助手 <{sender}>", 'utf-8')
        message['To'] = Header(",".join(receivers), 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')

        # Send the email
        with smtplib.SMTP_SSL(email_config['smtp_server'], email_config['smtp_port']) as smtp:
            smtp.login(sender, password)
            smtp.sendmail(sender, receivers, message.as_string())
        
        logging.info(f"邮件通知已成功发送至: {', '.join(receivers)}")
        return True

    except smtplib.SMTPAuthenticationError:
        logging.error("邮件发送失败：SMTP认证错误。请检查您的发件箱地址和授权码是否正确。")
        return False
    except Exception as e:
        logging.error(f"邮件发送失败，发生未知错误: {e}")
        return False