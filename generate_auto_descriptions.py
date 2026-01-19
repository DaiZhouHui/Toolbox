#!/usr/bin/env python3
"""
Toolbox 主生成脚本 - 自动分析GitHub仓库并生成README仪表板
作者: DaiZhouHui
功能: 自动从指定的GitHub仓库提取信息，生成统一的Toolbox页面
"""
import os
import sys
import time  # 在文件开头的导入部分添加这行
import json  # 确保导入了json模块
import requests
import json
import base64
import binascii  # <-- 新增这行
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
# ========== 配置部分 ==========
# 从环境变量读取GitHub令牌和用户名
from dotenv import load_dotenv
load_dotenv()  # 加载.env文件中的环境变量
# 从环境变量获取配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
USERNAME = os.getenv('GITHUB_USERNAME', 'DaiZhouHui')
# 
# ========== 从congfig.json配置文件读取要分析的仓库列表 ==========
CONFIG_FILE = 'config.json'
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    USERNAME = config.get('github_username', 'DaiZhouHui')
    REPO_LIST = config.get('repositories', [])
    print(f"✅ 已从 {CONFIG_FILE} 加载配置。")
except FileNotFoundError:
    print(f"⚠️  未找到配置文件 {CONFIG_FILE}，使用默认配置。")
    USERNAME = 'DaiZhouHui'
    REPO_LIST = ["NodeWeb", "CustomNode", "50DayChallenge"]
# ====================================

# 如果没有找到令牌，显示错误信息
if not GITHUB_TOKEN:
    print("❌ 错误：未找到 GitHub Token。")
    print("请按照以下步骤操作：")
    print("  1. 在项目根目录创建 .env 文件")
    print("  2. 在 .env 文件中添加: GITHUB_TOKEN=你的GitHub令牌")
    print("  3. 确保 .env 在 .gitignore 中，不会被提交")
    print("")
    print("如何获取GitHub令牌:")
    print("  1. 访问 https://github.com/settings/tokens")
    print("  2. 点击 Generate new token (classic)")
    print("  3. 勾选 'repo' 权限")
    print("  4. 生成并复制令牌")
    sys.exit(1)
# ========== GitHub API 函数 ==========

def call_github_api(endpoint: str, retries: int = 2) -> Optional[Dict[str, Any]]:  # 添加重试参数
    """
    调用GitHub API，增加超时和重试机制
    """
    url = f"https://api.github.com{endpoint}"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Toolbox-Auto-Generator'
    }

    # ==== 【修复】带有效性检查的缓存读取 ====
    safe_endpoint = endpoint.replace('/', '_').replace(':', '_')
    cache_dir = "api_cache"
    cache_file = os.path.join(cache_dir, f"cache_{safe_endpoint}.json")
    
    # 如果缓存文件存在且非空，尝试读取
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            # 关键检查：确保缓存的数据是有效的字典，不是None或空
            if isinstance(cached_data, dict) and cached_data:
                print(f"  💾 从缓存加载: {endpoint}")
                return cached_data
            else:
                print(f"  ⚠️  缓存数据无效，重新请求: {endpoint}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ⚠️  缓存文件损坏，重新请求: {endpoint}")
    # ======================================
    
    for attempt in range(retries + 1):
        try:
            # 将超时时间从10秒增加到30秒
            response = requests.get(url, headers=headers, timeout=30)
            
            # 检查HTTP状态
            if response.status_code == 403:
                print(f"  ⚠️ API限制或令牌权限不足: {response.status_code}")
                break
            elif response.status_code == 404:
                print(f"  ⚠️ 仓库不存在: {endpoint}")
                break
            elif response.status_code != 200:
                print(f"  ⚠️ API请求失败 ({endpoint}): HTTP {response.status_code}")
                if attempt < retries:
                    wait_time = 2 ** attempt  # 指数退避等待
                    print(f"    等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                break
                
            # 请求成功，解析数据
            data = response.json()
            
            # ==== 【修复】仅当数据有效时才写入缓存 ====
            if data is not None:  # 关键判断：确保不是None
                try:
                    # 将 endpoint 转换为安全的文件名
                    safe_endpoint = endpoint.replace('/', '_').replace(':', '_')
                    cache_file = os.path.join("api_cache", f"cache_{safe_endpoint}.json")
                    
                    # 确保缓存目录存在
                    os.makedirs("api_cache", exist_ok=True)
                    
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"  ⚠️  缓存写入失败（不影响运行）: {e}")
            # ==========================================
            
            return data
            
        except requests.exceptions.Timeout:
            print(f"  ⚠️ API请求超时 (尝试 {attempt+1}/{retries+1}): {endpoint}")
            if attempt < retries:
                wait_time = 3 * (attempt + 1)  # 等待3秒、6秒
                print(f"    等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                print(f"  ❌ 重试多次后仍失败: {endpoint}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ 网络请求失败 (尝试 {attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                time.sleep(3)
                continue
            return None
        except json.JSONDecodeError as e:
            print(f"  ⚠️ JSON解析失败 ({endpoint}): {e}")
            return None
    
    return None
def get_repository_info(owner: str, repo_name: str) -> Optional[Dict[str, Any]]:
    """
    获取仓库基本信息
    """
    return call_github_api(f"/repos/{owner}/{repo_name}")
def get_repository_readme(owner: str, repo_name: str) -> str:
    """
    获取仓库的README内容
    """
    data = call_github_api(f"/repos/{owner}/{repo_name}/readme")
    
    if data and data.get('encoding') == 'base64':
        try:
            content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
            return content
        except (binascii.Error, UnicodeDecodeError) as e:  # <-- 修改这里
            print(f"  ⚠️ README解码失败: {e}")
            return ""
    
    return ""
def get_repository_languages(owner: str, repo_name: str) -> Dict[str, int]:
    """
    获取仓库使用的编程语言统计
    """
    data = call_github_api(f"/repos/{owner}/{repo_name}/languages")
    return data if data else {}
# ========== README分析函数 ==========
def extract_description_from_readme(readme_content: str, repo_name: str) -> str:
    """
    从README内容中智能提取项目描述
    """
    if not readme_content or not readme_content.strip():
        return f"{repo_name} - 一个实用的开发工具项目"
    
    lines = readme_content.split('\n')
    description_candidates = []
    
    # 第一遍：寻找明显的描述段落
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 跳过空行和明显的非描述行
        if not line:
            continue
        if line.startswith(('#', '!', '[', '```', '<!--', '---', '|', '>', '- ', '* ', '1.')):
            continue
        if len(line) < 25:  # 太短的可能不是描述
            continue
        
        # 检查是否包含描述性关键词
        descriptive_keywords = ['是一个', '用于', '提供', '支持', '基于', '实现', '可以帮助', '用于']
        if any(keyword in line for keyword in descriptive_keywords):
            description_candidates.append(line)
            if len(description_candidates) >= 2:
                break
    
    # 第二遍：如果没找到，取第一段非空文本
    if not description_candidates:
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('#', '!', '[', '```', '<!--')):
                if 30 < len(line) < 200:
                    description_candidates.append(line)
                    break
    
    # 处理找到的描述
    if description_candidates:
        description = description_candidates[0]
        
        # 清理Markdown格式
        description = re.sub(r'!\[.*?\]\(.*?\)', '', description)  # 移除图片
        description = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', description)  # 移除链接保留文本
        description = re.sub(r'`([^`]+)`', r'\1', description)  # 移除代码标记
        description = re.sub(r'\*\*([^*]+)\*\*', r'\1', description)  # 移除粗体
        description = re.sub(r'\*([^*]+)\*', r'\1', description)  # 移除斜体
        
        # 限制长度
        if len(description) > 180:
            description = description[:177] + '...'
        
        return description
    
    # 备用方案：返回简化的描述
    return f"{repo_name} 项目，提供实用的功能和工具"
def analyze_repository(repo_name: str) -> Optional[Dict[str, Any]]:
    """
    分析单个仓库（超级防御版本）
    核心原则：任何一步失败都不崩溃，使用默认值继续。
    """
    print(f"🔍 分析仓库: {repo_name}")
    
    # 1. 获取仓库基本信息 - 这是最可能失败的根源
    repo_data = None
    try:
        repo_data = get_repository_info(USERNAME, repo_name)
    except Exception as e:
        print(f"  ⚠️  调用get_repository_info时发生意外错误: {e}")
    
    # ========== 核心防御：严格检查 repo_data ==========
    if repo_data is None:
        print(f"  ❌ 致命错误：无法获取仓库 '{repo_name}' 的任何信息。将跳过此仓库。")
        return None
    
    if not isinstance(repo_data, dict):
        print(f"  ⚠️  警告：仓库 '{repo_name}' 的数据类型不是字典 ({type(repo_data)})。将使用空字典。")
        repo_data = {}
    # ==================================================
    
    # 2. 智能提取描述（核心逻辑，每一步都加保护）
    final_description = f"{repo_name} - 一个开发项目"  # 最终兜底描述
    
    # 尝试获取GitHub官方描述
    gh_description = ""
    try:
        gh_description = repo_data.get('description', '')
        if gh_description and isinstance(gh_description, str):
            gh_description = gh_description.strip()
    except Exception:
        gh_description = ""
    
    # 如果官方描述有效，直接使用
    if gh_description:
        final_description = gh_description
    else:
        # 否则，尝试通过README提取
        print(f"  📄 尝试从README提取描述...")
        readme_content = ""
        try:
            readme_content = get_repository_readme(USERNAME, repo_name)
        except Exception as e:
            print(f"    ⚠️  获取README失败: {e}")
        
        if readme_content:
            try:
                extracted_desc = extract_description_from_readme(readme_content, repo_name)
                if extracted_desc and extracted_desc != f"{repo_name} - 一个实用的开发工具项目":
                    final_description = extracted_desc
            except Exception as e:
                print(f"    ⚠️  分析README失败: {e}")
    
    # 3. 安全地提取所有其他信息，并为任何可能的异常提供默认值
    try:
        main_language = repo_data.get('language')
        if not main_language or not isinstance(main_language, str):
            main_language = '多种语言'
    except Exception:
        main_language = '多种语言'
    
    try:
        languages_list = []
        # 注意：get_repository_languages 函数也可能返回None或失败
        langs_data = get_repository_languages(USERNAME, repo_name)
        if isinstance(langs_data, dict):
            languages_list = list(langs_data.keys())[:3]
    except Exception:
        languages_list = []
    
    # 4. 构建最终的信息字典（所有字段都有默认值）
    repository_info = {
        # 基本信息（有严格检查，相对安全）
        'name': repo_name,
        'url': repo_data.get('html_url', f'https://github.com/{USERNAME}/{repo_name}'),
        
        # 描述信息（经过多重保护）
        'official_description': gh_description,  # 原始GitHub描述，可能为空
        'extracted_description': final_description,
        'final_description': final_description,
        
        # 统计信息（提供默认值0）
        'stars': repo_data.get('stargazers_count', 0) if isinstance(repo_data.get('stargazers_count'), (int, float)) else 0,
        'forks': repo_data.get('forks_count', 0) if isinstance(repo_data.get('forks_count'), (int, float)) else 0,
        'watchers': repo_data.get('watchers_count', 0) if isinstance(repo_data.get('watchers_count'), (int, float)) else 0,
        'open_issues': repo_data.get('open_issues_count', 0) if isinstance(repo_data.get('open_issues_count'), (int, float)) else 0,
        
        # 时间信息（安全提取，提供空字符串默认值）
        'created_at': (repo_data.get('created_at', '')[:10] if isinstance(repo_data.get('created_at'), str) else ''),
        'updated_at': (repo_data.get('updated_at', '')[:10] if isinstance(repo_data.get('updated_at'), str) else ''),
        'pushed_at': (repo_data.get('pushed_at', '')[:10] if isinstance(repo_data.get('pushed_at'), str) else ''),
        
        # 技术信息
        'language': main_language,
        'languages': languages_list,
        'topics': repo_data.get('topics', []) if isinstance(repo_data.get('topics'), list) else [],
        'license': (repo_data.get('license', {}).get('name') 
                    if repo_data.get('license') and isinstance(repo_data.get('license'), dict) 
                    else None),
        
        # 功能特性
        'has_wiki': repo_data.get('has_wiki', False) if isinstance(repo_data.get('has_wiki'), bool) else False,
        'has_pages': repo_data.get('has_pages', False) if isinstance(repo_data.get('has_pages'), bool) else False,
        'has_projects': repo_data.get('has_projects', False) if isinstance(repo_data.get('has_projects'), bool) else False,
        'has_downloads': repo_data.get('has_downloads', True) if isinstance(repo_data.get('has_downloads'), bool) else True,
        
        # 状态信息
        'archived': repo_data.get('archived', False) if isinstance(repo_data.get('archived'), bool) else False,
        'disabled': repo_data.get('disabled', False) if isinstance(repo_data.get('disabled'), bool) else False,
        'private': repo_data.get('private', False) if isinstance(repo_data.get('private'), bool) else False,
    }
    
    print(f"  ✅ 成功分析: {repo_name} (⭐ {repository_info['stars']})")
    return repository_info
# ========== README生成函数 ==========
def generate_badge(label: str, value: Any, color: str = "blue") -> str:
    """
    生成Shields.io徽章
    """
    value_str = str(value).replace('-', '--').replace('_', '__')
    label_str = str(label).replace('-', '--').replace('_', '__')
    return f"![{label}](https://img.shields.io/badge/{label_str}-{value_str}-{color})"
def generate_repository_card(repo_info: Dict[str, Any]) -> str:
    """
    为单个仓库生成Markdown卡片
    """
    card = f"""
### 🗃️ [{repo_info['name']}]({repo_info['url']})
{repo_info['final_description']}
**📊 统计信息:**
- ⭐ 星标: **{repo_info['stars']}** | 🍴 Fork: **{repo_info['forks']}**
- 📅 更新: `{repo_info['updated_at']}` | 🐛 问题: {repo_info['open_issues']}
- 🔧 语言: `{repo_info['language']}` | 📚 Wiki: {'✅' if repo_info['has_wiki'] else '❌'}
"""
    
    # 添加主题标签
    if repo_info['topics']:
        topics_str = ' '.join([f'`{topic}`' for topic in repo_info['topics'][:5]])
        card += f"**🏷️ 主题标签:** {topics_str}\n\n"
    
    # 添加许可证信息
    if repo_info['license']:
        card += f"**📄 许可证:** {repo_info['license']}\n\n"
    
    card += f"**🔗 快速链接:** [访问仓库]({repo_info['url']})"
    
    # 添加其他语言
    if len(repo_info['languages']) > 1:
        other_langs = ', '.join([f'`{lang}`' for lang in repo_info['languages'][1:3]])
        card += f" | 其他语言: {other_langs}"
    
    card += "\n\n---\n"
    return card
def generate_readme_content(repositories: List[Dict[str, Any]]) -> str:
    """
    生成完整的README.md内容
    """
    # 计算统计信息
    total_repos = len(repositories)
    total_stars = sum(repo['stars'] for repo in repositories)
    total_forks = sum(repo['forks'] for repo in repositories)
    total_issues = sum(repo['open_issues'] for repo in repositories)
    
    # 获取所有语言
    all_languages = []
    for repo in repositories:
        if repo['language'] and repo['language'] != '多种语言':
            all_languages.append(repo['language'])
        all_languages.extend(repo['languages'])
    
    unique_languages = sorted(set(all_languages))
    
    # 按星标数排序
    sorted_repos = sorted(repositories, key=lambda x: x['stars'], reverse=True)
    
    # 生成最近更新的仓库
    recent_repos = sorted(repositories, key=lambda x: x['updated_at'], reverse=True)[:3]
    
    # 开始生成Markdown
    markdown = f"""# 🧰 {USERNAME}'s Toolbox
> 个人开发工具与项目集合 | 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
## 📊 仪表板概览
| 统计项 | 结果 | 说明 |
|--------|------|------|
| 📁 仓库总数 | **{total_repos}** | 收录的项目数量 |
| ⭐ 累计星标 | **{total_stars}** | 所有仓库星标总和 |
| 🍴 累计 Fork | **{total_forks}** | 所有仓库Fork总和 |
| 🔧 使用语言 | **{len(unique_languages)}** 种 | {', '.join(unique_languages[:5])}{'...' if len(unique_languages) > 5 else ''} |
| 📅 最后更新 | `{recent_repos[0]['updated_at'] if recent_repos else 'N/A'}` | {recent_repos[0]['name'] if recent_repos else ''} |
## 🏆 热门项目
以下是根据星标数排序的热门项目:
"""
    
    # 添加仓库卡片
    for i, repo in enumerate(sorted_repos, 1):
        markdown += generate_repository_card(repo)
    
    # 添加最近更新部分
    markdown += f"""
## 🔄 最近更新
| 仓库 | 更新日期 | 星标数 | 状态 |
|------|----------|--------|------|
"""
    for repo in recent_repos:
        status = "🟢 活跃"  # 默认状态
        try:
            if repo['updated_at']:  # 确保日期不为空
                # 增加日期格式解析保护
                date_obj = datetime.strptime(repo['updated_at'], '%Y-%m-%d')
                days_ago = (datetime.now() - date_obj).days
                if days_ago < 30:
                    status = "🟢 活跃"
                elif days_ago < 90:
                    status = "🟡 一般"
                else:
                    status = "🔴 停滞"
        except (ValueError, TypeError):
            # 如果日期解析失败（例如格式不对或为空），保持默认状态
            pass
        
        markdown += f"| [{repo['name']}]({repo['url']}) | {repo['updated_at']} | ⭐ {repo['stars']} | {status} |\n"
    
    # 添加技术栈分析（此处使用 ~~~ 避免嵌套 ``` 导致的显示问题）
    markdown += """
## 🔧 技术栈分析
### 主要编程语言分布
~~~
"""
    
    # 简单的语言统计
    lang_count = {}
    for repo in repositories:
        lang = repo['language']
        if lang and lang != '多种语言':
            lang_count[lang] = lang_count.get(lang, 0) + 1
    
    for lang, count in sorted(lang_count.items(), key=lambda x: x[1], reverse=True):
        bar = '█' * count
        markdown += f"{lang:<15} {bar} ({count})\n"
    
    markdown += """~~~
### 项目特性统计
- 📚 带Wiki的项目: {}/{}
- 🌐 启用Pages的项目: {}/{}
- 🏷️ 平均标签数: {:.1f} 个/项目
- 📄 有许可证的项目: {}/{}
""".format(
        sum(1 for r in repositories if r['has_wiki']), total_repos,
        sum(1 for r in repositories if r['has_pages']), total_repos,
        sum(len(r['topics']) for r in repositories) / total_repos if total_repos > 0 else 0,
        sum(1 for r in repositories if r['license']), total_repos
    )
    
    # 添加使用说明
    markdown += f"""
## 🚀 使用说明
### 手动更新
要手动更新此页面，在项目根目录运行:
~~~bash
# 确保已安装依赖
pip install requests python-dotenv
# 运行生成脚本
python generate_auto_descriptions.py
~~~
### 自动更新
此页面通过GitHub Actions自动更新，每天运行一次。
### 添加新仓库
要添加新仓库到此工具箱，请修改 `generate_auto_descriptions.py` 文件中的 `REPO_LIST`。
## 📁 项目结构
~~~
Toolbox/
├── generate_auto_descriptions.py   # 本脚本
├── README.md                       # 本文件（自动生成）
├── tools_index.json                # JSON格式索引
├── .env                            # 环境变量（本地）
├── .github/workflows/              # GitHub Actions
├── scripts/                        # 辅助脚本
└── tools/                          # 子模块存放处
~~~
## 🤝 贡献与反馈
这个工具箱是自动生成的。如果你发现任何问题或有改进建议，请:
1. 检查 `.env` 文件中的GitHub令牌是否正确
2. 确保要分析的仓库是公开的
3. 检查网络连接是否正常
---
*✨ 此页面由自动化脚本生成 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*[查看生成脚本](generate_auto_descriptions.py) | [报告问题](https://github.com/{USERNAME}/Toolbox/issues)*
"""
    
    return markdown


"""初始化环境：创建缓存目录、验证令牌"""
# 1. 确保缓存目录存在
cache_dir = "api_cache"
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    print(f"📁 创建缓存目录: {cache_dir}")

# 2. 验证令牌基本格式（简单检查）
token = os.getenv('GITHUB_TOKEN')
if not token or len(token) < 20:
    print("❌ 错误：GITHUB_TOKEN 环境变量未设置或格式无效。")
    print("请确保已在GitHub仓库的Secrets中正确设置 PAT_TOKEN 或 GITHUB_TOKEN。")
    sys.exit(1)
# ========== 主程序 ==========
def main():
    """
    主函数：协调整个分析过程
    """
    print("=" * 60)
    print(f"🧰 {USERNAME}'s Toolbox 生成器")
    print("=" * 60)
    print(f"📋 目标仓库 ({len(REPO_LIST)} 个): {', '.join(REPO_LIST)}")
    print("-" * 60)
    
    # 分析所有仓库
    all_repositories = []
    successful_repos = 0
    
    for repo_name in REPO_LIST:
        repo_info = analyze_repository(repo_name)
        if repo_info:
            all_repositories.append(repo_info)
            successful_repos += 1
        else:
            print(f"  ❌ 跳过仓库: {repo_name}")
    
    print("-" * 60)
    
    # 检查是否有成功分析的仓库
    if successful_repos == 0:
        print("❌ 错误：没有成功分析任何仓库。")
        print("可能的原因:")
        print("  1. GitHub令牌无效或权限不足")
        print("  2. 仓库不存在或不是公开仓库")
        print("  3. 网络连接问题")
        print("  4. API速率限制")
        sys.exit(1)
    
    # 生成README
    print("📝 生成README.md文件...")
    readme_content = generate_readme_content(all_repositories)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # 生成JSON索引
    print("📊 生成JSON索引文件...")
    json_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_repositories": successful_repos,
            "username": USERNAME,
            "toolbox_version": "1.0.0"
        },
        "statistics": {
            "total_stars": sum(r['stars'] for r in all_repositories),
            "total_forks": sum(r['forks'] for r in all_repositories),
            "total_issues": sum(r['open_issues'] for r in all_repositories),
            "languages": sorted(set(r['language'] for r in all_repositories if r['language']))
        },
        "repositories": [
            {
                "name": repo['name'],
                "url": repo['url'],
                "description": repo['final_description'],
                "stars": repo['stars'],
                "forks": repo['forks'],
                "language": repo['language'],
                "updated_at": repo['updated_at'],
                "topics": repo['topics'],
                "has_wiki": repo['has_wiki'],
                "license": repo['license']
            }
            for repo in all_repositories
        ]
    }
    
    with open("tools_index.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
    
    # 生成摘要报告
    print("-" * 60)
    print("🎉 生成完成！")
    print("=" * 60)
    print(f"✅ 成功分析: {successful_repos}/{len(REPO_LIST)} 个仓库")
    print(f"⭐ 总星标数: {sum(r['stars'] for r in all_repositories)}")
    print(f"🍴 总Fork数: {sum(r['forks'] for r in all_repositories)}")
    print(f"🔧 涉及语言: {len(set(r['language'] for r in all_repositories))} 种")
    print("")
    print("📁 生成的文件:")
    print(f"  • README.md ({len(readme_content)} 字符)")
    print(f"  • tools_index.json (JSON格式索引)")
    print("")
    print("🚀 下一步:")
    print("  1. 检查 README.md 文件内容")
    print("  2. 提交更改到GitHub: git add . && git commit -m '更新工具箱'")
    print("  3. 推送: git push origin main")
    print("=" * 60)
# ========== 脚本入口 ==========
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作。")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        print("错误类型:", type(e).__name__)
        import traceback
        traceback.print_exc()
        sys.exit(1)