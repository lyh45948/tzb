#!/bin/bash
# ============================================================================
# 智能小车后端 — 统信UOS一键安装脚本
# ============================================================================
# 使用方法:
#   cd backend
#   bash setup_uos.sh
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  智能小车后端 — 统信UOS安装脚本"
echo "========================================"

# 1. 检查系统
if [ -f /etc/uos-release ] || [ -f /etc/os-release ] && grep -q "UOS" /etc/os-release 2>/dev/null; then
    echo "[✓] 检测到统信UOS系统"
else
    echo "[!] 未检测到统信UOS，继续安装..."
fi

# 2. 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[✗] 未找到 Python3，请手动安装"
    exit 1
fi
PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}')
echo "[✓] Python 版本: $PYTHON_VER"

# 3. 检查 MySQL/MariaDB
echo "[>] 检查 MySQL 服务..."
if systemctl is-active --quiet mysql 2>/dev/null || systemctl is-active --quiet mariadb 2>/dev/null; then
    echo "[✓] MySQL/MariaDB 服务正在运行"
else
    echo "[!] MySQL/MariaDB 服务未运行，尝试安装..."
    echo "    请手动执行: sudo apt-get update && sudo apt-get install -y mysql-server"
    echo "    或参考统信软件商店安装 MariaDB"
    exit 1
fi

# 4. 检查 uv
if ! command -v uv &> /dev/null; then
    echo "[!] 未找到 uv，尝试安装..."
    if command -v pip3 &> /dev/null; then
        pip3 install uv
    elif command -v pip &> /dev/null; then
        pip install uv
    else
        echo "[✗] 未找到 pip，请手动安装 uv: https://github.com/astral-sh/uv"
        exit 1
    fi
fi
echo "[✓] uv 版本: $(uv --version)"

# 5. 创建虚拟环境并安装依赖
if [ ! -d ".venv" ]; then
    echo "[>] 创建 uv 虚拟环境..."
    uv venv
fi

echo "[>] 安装 Python 依赖..."
source .venv/bin/activate
uv pip install -r requirements.txt
echo "[✓] 依赖安装完成"

# 6. 配置环境变量
if [ ! -f ".env" ]; then
    echo "[>] 创建 .env 配置文件..."
    cp .env.example .env
    echo "[!] 请编辑 .env 文件，配置正确的数据库密码和 IP 地址"
fi

# 7. 初始化数据库
echo "[>] 初始化数据库..."
MYSQL_USER=$(grep MYSQL_USER .env | cut -d '=' -f2 | tr -d ' ')
MYSQL_PASSWORD=$(grep MYSQL_PASSWORD .env | cut -d '=' -f2 | tr -d ' ')
MYSQL_HOST=$(grep MYSQL_HOST .env | cut -d '=' -f2 | tr -d ' ')
MYSQL_PORT=$(grep MYSQL_PORT .env | cut -d '=' -f2 | tr -d ' ')

if [ -z "$MYSQL_PASSWORD" ]; then
    MYSQL_PASSWORD="1234"
fi
if [ -z "$MYSQL_USER" ]; then
    MYSQL_USER="root"
fi

# 尝试无密码连接
if mysql -u root -e "SELECT 1;" &>/dev/null; then
    echo "[✓] MySQL root 无密码访问"
    mysql -u root < sql/init.sql
elif mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" &>/dev/null; then
    echo "[✓] MySQL $MYSQL_USER 访问正常"
    mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" < sql/init.sql
else
    echo "[!] 无法连接 MySQL，请检查 .env 中的数据库配置"
    echo "    然后手动执行: mysql -u root -p < sql/init.sql"
fi

# 8. 注册 systemd 服务（可选）
echo "[>] 配置 systemd 服务..."
if [ -d /etc/systemd/system ]; then
    SERVICE_FILE="/etc/systemd/system/smart-car-backend.service"
    # 生成带当前用户的服务文件
    sed "s|User=%I|User=$(whoami)|g" smart-car-backend.service | sudo tee "$SERVICE_FILE" > /dev/null
    sudo systemctl daemon-reload
    echo "[✓] systemd 服务已注册: $SERVICE_FILE"
    echo "    启动命令: sudo systemctl start smart-car-backend"
    echo "    开机自启: sudo systemctl enable smart-car-backend"
else
    echo "[!] 未找到 systemd，跳过服务注册"
fi

# 9. 完成
echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "快速启动:"
echo "  cd backend && bash run.sh"
echo ""
echo "或使用 systemd:"
echo "  sudo systemctl start smart-car-backend"
echo ""
echo "查看日志:"
echo "  sudo journalctl -u smart-car-backend -f"
echo ""
echo "REST API 地址:"
echo "  http://$(hostname -I | awk '{print $1}'):5000/v1/devices"
echo ""
