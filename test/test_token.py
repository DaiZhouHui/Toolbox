import os
import requests
import sys

# 使用我们手动加载 .env 文件的逻辑
def load_env_file():
    env_file = '.env'
    try:
        with open(env_file, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ 已从 {env_file} 加载环境变量。")
    except FileNotFoundError:
        print(f"❌ 未找到 {env_file} 文件。")
        sys.exit(1)

load_env_file()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
USERNAME = os.getenv('GITHUB_USERNAME')

if not GITHUB_TOKEN:
    print("❌ 错误：未在环境变量中找到 GITHUB_TOKEN。")
    sys.exit(1)

print(f"🧪 开始测试令牌，用户: {USERNAME}")
print("-" * 40)

# 测试1: 获取当前用户信息 (验证令牌基础有效性)
url = "https://api.github.com/user"
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"1. 测试用户API... 状态码: {response.status_code}")
    
    if response.status_code == 200:
        user_data = response.json()
        print(f"   ✅ 令牌有效！所属用户: {user_data.get('login')}")
        print(f"   ℹ️  剩余API限制: {response.headers.get('X-RateLimit-Remaining', '未知')}/{response.headers.get('X-RateLimit-Limit', '未知')}")
    elif response.status_code == 401:
        print("   ❌ 令牌无效或已过期 (401 Unauthorized)。请重新生成。")
    elif response.status_code == 403:
        # 可能是权限不足或速率限制
        limit_remaining = response.headers.get('X-RateLimit-Remaining')
        if limit_remaining == '0':
            print("   ⚠️  API速率已达上限 (403 Forbidden)，请稍后再试。")
        else:
            print(f"   ❌ 权限不足 (403 Forbidden)。请确认令牌有 'repo' 权限。")
    else:
        print(f"   ⚠️  意外状态码: {response.status_code}")
        
except requests.exceptions.RequestException as e:
    print(f"   ❌ 网络请求失败: {e}")

print("-" * 40)

# 测试2: 尝试获取一个具体仓库信息（例如你自己的Toolbox仓库）
test_repo = "Toolbox"  # 测试你自己的一个公开仓库
url = f"https://api.github.com/repos/{USERNAME}/{test_repo}"
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"2. 测试仓库API ({USERNAME}/{test_repo})... 状态码: {response.status_code}")
    
    if response.status_code == 200:
        repo_data = response.json()
        print(f"   ✅ 仓库访问成功！描述: {repo_data.get('description', '空')}")
    elif response.status_code == 404:
        print(f"   ⚠️  仓库不存在 (404)，请检查仓库名和权限。")
    elif response.status_code == 403:
        print(f"   ❌ 无权访问此仓库 (403)，令牌可能需要 'repo' 或 'public_repo' 权限。")
    else:
        print(f"   ⚠️  意外状态码: {response.status_code}")
        
except requests.exceptions.RequestException as e:
    print(f"   ❌ 网络请求失败: {e}")

print("-" * 40)
print("测试完成。请根据上方输出排查问题。")