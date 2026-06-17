#!/bin/bash
# ============================================================================
# tzb 项目重装系统后一键安装脚本 (统信UOS Desktop 25)
# ============================================================================
# 包含:
#   1. apt 基础工具 (git, pip, build-essential, cmake, ...)
#   2. MariaDB (fwwb 后端)
#   3. Docker (lidar SLAM)
#   4. fwwb backend Python venv + requirements.txt (含 torch/ultralytics)
#   5. ROS Docker 镜像 osrf/ros:noetic-desktop + catkin_make
#
# 使用:
#   bash install_all.sh            # 全部步骤
#   bash install_all.sh basic      # 仅基础工具
#   bash install_all.sh mysql      # 仅 MariaDB
#   bash install_all.sh docker     # 仅 Docker + ROS 镜像
#   bash install_all.sh python     # 仅 fwwb Python 依赖
#   bash install_all.sh ros        # 仅编译 catkin_ws
# ============================================================================

set -e
WORKDIR=/home/tzb/tzb
USER_NAME="$(whoami)"

log()  { echo -e "\033[1;36m[>]\033[0m $*"; }
ok()   { echo -e "\033[1;32m[✓]\033[0m $*"; }
warn() { echo -e "\033[1;33m[!]\033[0m $*"; }
err()  { echo -e "\033[1;31m[✗]\033[0m $*"; }

step_basic() {
  log "[1/5] 安装基础工具 (apt)"
  sudo apt-get update
  sudo apt-get install -y \
    git curl wget vim ca-certificates gnupg lsb-release \
    build-essential cmake pkg-config \
    python3-pip python3-venv python3-dev \
    libssl-dev libffi-dev \
    libgl1 libglib2.0-0 \
    default-libmysqlclient-dev
  ok "基础工具安装完成"
}

step_mysql() {
  log "[2/5] 安装并初始化 MariaDB"
  sudo apt-get install -y mariadb-server mariadb-client
  sudo systemctl enable mariadb
  sudo systemctl start mariadb
  ok "MariaDB 已启动"

  # 设置 root 密码为 1234 (与 backend 默认一致),并创建数据库
  log "尝试设置 MySQL root 密码 = 1234 并导入 init.sql"
  if sudo mysql -e "SELECT 1;" &>/dev/null; then
    sudo mysql <<'SQL'
ALTER USER 'root'@'localhost' IDENTIFIED BY '1234';
FLUSH PRIVILEGES;
SQL
    sudo mysql -uroot -p1234 < "$WORKDIR/fwwb/backend/sql/init.sql"
    ok "数据库 smart_car 已初始化"
  else
    warn "请手动执行: sudo mysql_secure_installation 然后 mysql -uroot -p < $WORKDIR/fwwb/backend/sql/init.sql"
  fi
}

step_docker() {
  log "[3/5] 安装 Docker"
  if ! command -v docker &>/dev/null; then
    sudo apt-get install -y docker.io
  else
    ok "docker 已存在: $(docker --version)"
  fi
  sudo systemctl enable docker
  sudo systemctl start docker
  if ! groups "$USER_NAME" | grep -q docker; then
    sudo usermod -aG docker "$USER_NAME"
    warn "已将 $USER_NAME 加入 docker 组,需要重新登录或 newgrp docker 才能免 sudo"
  fi
  ok "Docker 服务运行中"

  log "拉取 osrf/ros:noetic-desktop 镜像 (约 2GB)"
  sudo docker pull osrf/ros:noetic-desktop
  ok "ROS 镜像就绪"
}

step_python() {
  log "[4/5] 安装 fwwb Python 依赖 (含 torch/ultralytics 视觉)"
  cd "$WORKDIR/fwwb/backend"

  if [ ! -f .env ]; then
    cp .env.example .env
    sed -i 's/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=1234/' .env
    ok "已生成 .env (MYSQL_PASSWORD=1234)"
  fi

  if [ ! -d .venv ]; then
    python3 -m venv .venv
    ok "已创建 .venv"
  fi
  source .venv/bin/activate
  pip install --upgrade pip setuptools wheel
  # 国内镜像加速 (清华)
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ok "fwwb Python 依赖安装完成"
  deactivate
}

step_ros() {
  log "[5/5] 在 ROS Docker 容器内编译 catkin_ws"
  cd "$WORKDIR/lidar"
  if ! sudo docker images osrf/ros:noetic-desktop --format '{{.Repository}}' | grep -q ros; then
    err "ROS 镜像未拉取,请先运行: bash install_all.sh docker"
    return 1
  fi
  sudo docker run --rm \
    -v "$WORKDIR/lidar/catkin_ws:/catkin_ws" \
    osrf/ros:noetic-desktop \
    bash -c "source /opt/ros/noetic/setup.bash && cd /catkin_ws && catkin_make"
  ok "catkin_ws 编译完成"
}

main() {
  case "${1:-all}" in
    basic)  step_basic ;;
    mysql)  step_mysql ;;
    docker) step_docker ;;
    python) step_python ;;
    ros)    step_ros ;;
    all)
      step_basic
      step_mysql
      step_docker
      step_python
      step_ros
      ;;
    *)
      err "未知步骤: $1"
      grep '^# ' "$0" | sed 's/^# //'
      exit 1
      ;;
  esac
  echo
  ok "完成!"
}

main "$@"
