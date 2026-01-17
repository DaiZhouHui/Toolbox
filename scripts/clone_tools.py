#!/usr/bin/env python3
"""
将列表中的仓库克隆为子模块
"""

import os, subprocess

REPOS = ["NodeWeb", "CustomNode", "50DayChallenge"]  # 你的仓库列表
USER = "DaiZhouHui"

def run_cmd(cmd):
    """运行命令并打印输出"""
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, text=True)
    return result.returncode == 0

def main():
    print("🔧 开始设置子模块...")
    
    for repo in REPOS:
        target_dir = f"tools/{repo}"
        if os.path.exists(target_dir):
            print(f"⏭️  跳过 {repo}，目录已存在")
            continue
        
        print(f"\n📥 添加子模块: {repo}")
        cmd = f"git submodule add https://github.com/{USER}/{repo}.git {target_dir}"
        if run_cmd(cmd):
            print(f"   ✅ 成功")
        else:
            print(f"   ❌ 失败")
    
    print("\n🎉 子模块添加完成！")
    print("运行以下命令初始化：")
    print("  git submodule init")
    print("  git submodule update")

if __name__ == "__main__":
    main()