"""
调试基金API返回数据格式
"""

import requests
import json

def debug_fund_api():
    """调试基金API"""
    
    fund_codes = ["000001", "110022", "012348"]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for fund_code in fund_codes:
        print(f"\n🔍 调试基金代码: {fund_code}")
        print("=" * 40)
        
        try:
            url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"状态码: {response.status_code}")
            print(f"响应长度: {len(response.text)}")
            print(f"原始响应: {response.text}")
            
            if response.status_code == 200:
                content = response.text.strip()
                print(f"处理后内容: {content}")
                
                # 尝试不同的解析方法
                if content.startswith('jsonpgz('):
                    print("检测到 jsonpgz 格式")
                    json_str = content[8:-2]  # 正确的索引
                    print(f"提取的JSON: {json_str}")
                    
                    try:
                        data = json.loads(json_str)
                        print(f"✅ 解析成功: {data}")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON解析失败: {e}")
                        print(f"错误位置: {json_str[max(0, e.pos-10):e.pos+10]}")
                
        except Exception as e:
            print(f"请求失败: {e}")

if __name__ == "__main__":
    debug_fund_api()