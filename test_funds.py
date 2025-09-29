"""
测试不同基金代码的数据获取
"""

from fund_backtest import FundDataDownloader

def test_fund_codes():
    """测试多个基金代码"""
    
    # 常见的基金代码
    test_codes = [
        "000001",  # 华夏成长混合
        "110022",  # 易方达消费行业
        "161725",  # 招商中证白酒指数
        "320007",  # 诺安成长混合
        "012348",  # 用户输入的代码
        "519674",  # 银河创新成长混合
        "001102"   # 前海开源国家比较优势混合
    ]
    
    downloader = FundDataDownloader()
    
    print("🔍 测试基金代码数据获取")
    print("=" * 50)
    
    for fund_code in test_codes:
        print(f"\n📊 测试基金: {fund_code}")
        
        # 测试基金信息获取
        fund_info = downloader.get_fund_info(fund_code)
        if fund_info:
            print(f"   ✅ 基金信息: {fund_info.get('name', '未知')}")
            print(f"   💰 当前净值: {fund_info.get('gsz', 'N/A')}")
        else:
            print(f"   ❌ 无法获取基金信息")
        
        # 测试历史数据获取
        try:
            fund_data = downloader.get_fund_history(fund_code, "2024-01-01", "2024-03-31")
            if not fund_data.empty:
                print(f"   ✅ 历史数据: {len(fund_data)} 条记录")
                print(f"   📅 数据期间: {fund_data['date'].iloc[0].strftime('%Y-%m-%d')} 至 {fund_data['date'].iloc[-1].strftime('%Y-%m-%d')}")
            else:
                print(f"   ⚠️  使用模拟数据")
        except Exception as e:
            print(f"   ❌ 数据获取失败: {e}")

if __name__ == "__main__":
    test_fund_codes()