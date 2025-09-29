"""
测试JSON解析修复
"""

import json

def test_json_parsing():
    # 模拟API返回的数据
    test_content = 'jsonpgz({"fundcode":"000001","name":"华夏成长混合","jzrq":"2025-09-25","dwjz":"1.1150","gsz":"1.0950","gszzl":"-1.80","gztime":"2025-09-26 15:00"});'
    
    print(f"原始内容: {test_content}")
    print(f"内容长度: {len(test_content)}")
    
    # 测试不同的切片方法
    methods = [
        ("方法1: [8:-2]", test_content[8:-2]),
        ("方法2: [9:-2]", test_content[9:-2]),
        ("方法3: [8:-1]", test_content[8:-1]),
        ("方法4: 手动查找", test_content[test_content.find('{'): test_content.rfind('}')+1])
    ]
    
    for method_name, json_str in methods:
        print(f"\n{method_name}")
        print(f"提取结果: {json_str}")
        try:
            data = json.loads(json_str)
            print(f"✅ 解析成功: {data}")
            break
        except json.JSONDecodeError as e:
            print(f"❌ 解析失败: {e}")

if __name__ == "__main__":
    test_json_parsing()