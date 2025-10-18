import requests
import logging
import time
import json
from typing import Dict, Optional


def get_fund_data(fund_code: str) -> Optional[Dict]:
    """
    Fetches real-time data for a specific fund from the Tiantian Fund API.

    Args:
        fund_code: The 6-digit fund code.

    Returns:
        A dictionary containing fund data or None if the request fails.
        Example:
        {
            "fundcode": "161725",
            "name": "招商中证白酒指数(LOF)A",
            "jzrq": "2025-10-14", // 净值日期
            "dwjz": "0.8020",    // 单位净值
            "gsz": "0.7968",     // 估算净值
            "gszzl": "-0.65",    // 估算涨跌率
            "gztime": "2025-10-15 15:00:00" // 估值时间
        }
    """
    # Add a timestamp to prevent caching issues
    timestamp = int(time.time() * 1000)
    # The API URL from Tiantian Fund's mobile endpoint
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={timestamp}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Referer': f'http://fund.eastmoney.com/{fund_code}.html'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # The response is a JSONP format like "jsonpgz( {...} );"
        # We need to extract the JSON part.
        json_str = response.text.strip()
        if not json_str.startswith('jsonpgz(') or not json_str.endswith(');'):
            logging.error(f"解析基金 {fund_code} 数据时格式不匹配: {json_str}")
            return None
            
        json_content = json_str[len('jsonpgz('):-2]
        data = json.loads(json_content)
        return data

    except requests.exceptions.RequestException as e:
        logging.error(f"获取基金 {fund_code} 数据时发生网络错误: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"解析基金 {fund_code} 数据时发生错误，原始返回内容: {response.text}")
        return None
    except Exception as e:
        logging.error(f"获取基金 {fund_code} 数据时发生未知错误: {e}")
        return None