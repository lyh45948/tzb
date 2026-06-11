#!/bin/bash
# 智能小车后端启动脚本（统信UOS适配版）

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 使用 uv 虚拟环境（统信系统推荐使用 uv 管理 Python 依赖）
if [ -d ".venv" ]; then
    echo "激活 uv 虚拟环境..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "激活 venv 虚拟环境..."
    source venv/bin/activate
else
    echo "警告: 未找到虚拟环境，尝试使用系统 Python"
fi

# 检查必要的环境变量
if [ ! -f ".env" ]; then
    echo "警告: 未找到 .env 文件，请复制 .env.example 并配置数据库连接"
    echo "  cp .env.example .env"
fi

# 启动后端服务
echo "启动智能小车后端服务..."
python main.py
