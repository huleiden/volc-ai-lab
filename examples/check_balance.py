import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_profile
from volcenginesdkbilling.api.billing_api import BILLINGApi
from volcenginesdkbilling.models.query_balance_acct_request import QueryBalanceAcctRequest
import volcenginesdkcore

def check_balance():
    load_profile()
    
    # 尝试加载 credentials.properties
    import io
    ak = None
    sk = None
    prop_path = "/Users/bytedance/work/volcanoengine/credentials.properties"
    if os.path.exists(prop_path):
        with open(prop_path, 'r') as f:
            content = "[root]\n" + f.read()
        import configparser
        config = configparser.ConfigParser()
        config.read_string(content)
        if config.has_option('root', 'volc.access.key.id'):
            ak = config.get('root', 'volc.access.key.id').strip('"').strip("'")
        if config.has_option('root', 'volc.access.key.secret'):
            sk = config.get('root', 'volc.access.key.secret').strip('"').strip("'")

    if not ak or not sk:
        print("错误: 无法在 credentials.properties 中找到 AK/SK")
        return

    # 配置官方 SDK
    configuration = volcenginesdkcore.Configuration()
    configuration.ak = ak
    configuration.sk = sk
    configuration.region = "cn-beijing"
    
    print("\n--- 正在查询火山引擎账户余额 (官方 SDK) ---")
    
    try:
        api_instance = BILLINGApi(volcenginesdkcore.ApiClient(configuration))
        request = QueryBalanceAcctRequest()
        
        resp = api_instance.query_balance_acct(request)
        
        print("\n================================")
        print("【 火山引擎账户查账报告 】")
        print("--------------------------------")
        print(f"可用现金余额: ¥ {resp.cash_balance}")
        print(f"当前冻结金额: ¥ {resp.freeze_amount}")
        print(f"账户总可用额: ¥ {resp.available_balance}")
        print("--------------------------------")
        
        try:
            balance = float(resp.cash_balance.replace(',', ''))
            if balance < 200:
                print("⚠️ 警告：当前余额低于 ¥200，大模型实验可能受限。")
            else:
                print("✅ 状态：余额充足。")
        except:
            print("💡 提示：无法解析余额数值，请手动核对。")
            
        print("================================\n")

    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == "__main__":
    check_balance()
