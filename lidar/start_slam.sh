#!/bin/bash
set -euo pipefail

# ============================================================
# ROS SLAM 一键启动脚本（Cartographer 2D）
# 支持纯雷达运行，检测到 IMU 时自动启用
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
CATKIN_WS="/catkin_ws"
CONTAINER_NAME="ros_container"
IMAGE="osrf/ros:noetic-desktop"

# 默认参数
USE_WHEEL_ODOM="true"

# 参数解析
for arg in "$@"; do
    case "$arg" in
        --no-wheel-odom) USE_WHEEL_ODOM="false" ;;
        -h|--help)
            cat << 'HELP'
用法: sudo ./start_slam.sh [选项]

选项:
  --no-wheel-odom  禁用 Hi3861 轮速里程计（默认启用）
  -h, --help       显示此帮助

说明:
  脚本自动检测 CH343 串口设备。
  如果只连接了雷达，将以纯雷达模式启动。
  如果同时连接了 IMU，将自动启用 IMU 融合。
  默认启用轮速里程计（需同时启动 fwwb 后端转发 UDP 数据）。
HELP
            exit 0
            ;;
    esac
done

# -----------------------------------------------------------
# 检查 root 权限
# -----------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    echo "需要 sudo 权限，正在自动提权..."
    exec sudo bash "$0" "$@"
fi

# -----------------------------------------------------------
# 工具函数
# -----------------------------------------------------------
log_step()  { echo "[$(date +%H:%M:%S)] $1"; }
log_info()  { echo "  [INFO] $1"; }
log_warn()  { echo "  [WARN] $1" >&2; }
log_err()   { echo "  [ERROR] $1" >&2; }

# 串口自动识别：支持 1~N 个 CH343 端口，动态识别 IMU
# 输出格式: LIDAR_PORT:IMU_PORT（IMU_PORT 为空表示未检测到 IMU）
detect_ports() {
    python3 -c "
import os, glob, termios, fcntl, time, sys

ports = sorted(glob.glob('/dev/ttyCH343USB*'))
if not ports:
    print('UNKNOWN')
    exit(1)

def sniff(path, baud):
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
        attrs = termios.tcgetattr(fd)
        baud_const = {230400: termios.B230400, 460800: termios.B460800}.get(baud, termios.B230400)
        attrs[4] = baud_const
        attrs[5] = baud_const
        attrs[2] = attrs[2] & ~termios.PARENB & ~termios.CSTOPB & ~termios.CSIZE | termios.CS8
        attrs[2] |= termios.CLOCAL | termios.CREAD
        attrs[1] = 0
        attrs[3] = attrs[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 1
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
        termios.tcflush(fd, termios.TCIOFLUSH)
        time.sleep(0.5)
        data = b''
        start = time.time()
        while time.time() - start < 1.5:
            try:
                chunk = os.read(fd, 64)
                if chunk: data += chunk
            except BlockingIOError:
                time.sleep(0.05)
        os.close(fd)
        return data
    except Exception:
        return b''

# 先尝试识别 IMU（帧头 0x59 @ 460800）
imu_ports = []
other_ports = []
for port in ports:
    data = sniff(port, 460800)
    if data[:1] == b'\x59':
        imu_ports.append(port)
    else:
        other_ports.append(port)

# 如果没识别到 IMU，再 retry 一次
if not imu_ports:
    time.sleep(0.5)
    for port in other_ports[:]:
        data = sniff(port, 460800)
        if data[:1] == b'\x59':
            imu_ports.append(port)
            other_ports.remove(port)

# 选择雷达端口：优先从 other_ports 选第一个
if other_ports:
    lidar = other_ports[0]
elif imu_ports and len(ports) > len(imu_ports):
    # 有多个端口且至少一个被识别为 IMU，从非 IMU 中选雷达
    lidar = [p for p in ports if p not in imu_ports][0]
elif ports and not imu_ports:
    # 没有识别到 IMU，所有端口都可能是雷达，选第一个
    lidar = ports[0]
else:
    # 只有一个端口且被识别为 IMU → 无雷达可用
    print('UNKNOWN')
    exit(1)

# 验证雷达端口至少能读到数据（帧头 0x54 @ 230400）
lidar_data = sniff(lidar, 230400)
if not lidar_data:
    print(f'[WARN] 雷达端口 {lidar} 无数据，尝试其他端口...', file=sys.stderr)
    for p in ports:
        if p != lidar and sniff(p, 230400):
            lidar = p
            break

imu = imu_ports[0] if imu_ports else ''
print(f'{lidar}:{imu}')
"
}

# 检测源码是否变更（与上次编译时间比较）
needs_rebuild() {
    local stamp_file="/tmp/.catkin_last_build"
    local newest_src
    newest_src=$(find "$PROJECT_ROOT/catkin_ws/src" \
        -type f \( -name '*.py' -o -name '*.cpp' -o -name '*.h' -o -name '*.launch' -o -name '*.lua' -o -name '*.cfg' \) \
        -newer "$stamp_file" 2>/dev/null | head -1)
    [ -n "$newest_src" ]
}

# -----------------------------------------------------------
# 防重入锁
# -----------------------------------------------------------
LOCK_FILE="/tmp/start_slam.lock"
if [ -e "$LOCK_FILE" ]; then
    old_pid=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
        log_err "脚本已在运行 (PID=$old_pid)，请勿重复启动"
        exit 1
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# -----------------------------------------------------------
# 主流程
# -----------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  模式: Cartographer 2D SLAM                  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. 串口检测与配置
log_step "[1/5] 检测并配置串口..."
PORT_PAIR=$(detect_ports) || {
    log_err "未检测到 CH343 设备，请检查 USB 连接"
    exit 1
}
LIDAR_PORT="${PORT_PAIR%:*}"
IMU_PORT="${PORT_PAIR#*:}"

if [ -z "$LIDAR_PORT" ] || [ "$LIDAR_PORT" = "UNKNOWN" ]; then
    log_err "未检测到激光雷达，请检查 USB 连接"
    exit 1
fi

if [ -n "$IMU_PORT" ]; then
    HAS_IMU="true"
    ln -sf "$IMU_PORT" /dev/yesense_imu
    chmod 666 "$IMU_PORT" /dev/yesense_imu 2>/dev/null || true
    log_info "IMU : $IMU_PORT → /dev/yesense_imu"
else
    HAS_IMU="false"
    rm -f /dev/yesense_imu
    log_info "IMU : 未检测到，以纯雷达模式运行"
fi

ln -sf "$LIDAR_PORT" /dev/wheeltec_lidar
chmod 666 "$LIDAR_PORT" /dev/wheeltec_lidar 2>/dev/null || true
log_info "雷达: $LIDAR_PORT → /dev/wheeltec_lidar"

LIDAR_DEV=$(readlink -f /dev/wheeltec_lidar)
if [ "$HAS_IMU" = "true" ]; then
    IMU_DEV=$(readlink -f /dev/yesense_imu)
fi

# 2. Docker 容器管理
log_step "[2/5] 检查 Docker 容器..."
need_create=0

# 构建当前期望的设备列表（用于检测容器是否需要重建）
EXPECTED_DEVS="$LIDAR_DEV"
if [ "$HAS_IMU" = "true" ]; then
    EXPECTED_DEVS="$EXPECTED_DEVS $IMU_DEV"
fi

if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
    log_info "容器不存在，准备创建"
    need_create=1
elif ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
    log_info "容器已停止，正在启动"
    docker start "$CONTAINER_NAME" >/dev/null
    sleep 2
else
    # 检查容器内是否有所有需要的设备
    dev_missing=0
    for dev in $EXPECTED_DEVS; do
        if ! docker exec "$CONTAINER_NAME" test -e "$dev" 2>/dev/null; then
            dev_missing=1
            break
        fi
    done
    if [ "$dev_missing" -eq 1 ]; then
        log_warn "设备映射过期，重建容器"
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm   "$CONTAINER_NAME" >/dev/null 2>&1 || true
        need_create=1
    else
        log_info "容器运行中，设备映射正常"
    fi
fi

if [ "$need_create" -eq 1 ]; then
    # 轮速里程计需要映射 UDP 7799 端口，让容器内节点接收后端转发
    NETWORK_ARGS=""
    if [ "$USE_WHEEL_ODOM" = "true" ]; then
        NETWORK_ARGS="-p 7799:7799/udp"
    fi

    if [ "$HAS_IMU" = "true" ]; then
        docker run -d \
            --net=host \
            --device="$LIDAR_DEV":"$LIDAR_DEV" \
            --device="$IMU_DEV":"$IMU_DEV" \
            -v "$PROJECT_ROOT/catkin_ws":"$CATKIN_WS" \
            -e DISPLAY=:0 \
            -e QT_X11_NO_MITSHM=1 \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            $NETWORK_ARGS \
            --name "$CONTAINER_NAME" \
            "$IMAGE" bash -c "sleep infinity" >/dev/null
    else
        docker run -d \
            --net=host \
            --device="$LIDAR_DEV":"$LIDAR_DEV" \
            -v "$PROJECT_ROOT/catkin_ws":"$CATKIN_WS" \
            -e DISPLAY=:0 \
            -e QT_X11_NO_MITSHM=1 \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            $NETWORK_ARGS \
            --name "$CONTAINER_NAME" \
            "$IMAGE" bash -c "sleep infinity" >/dev/null
    fi
    sleep 2
    log_info "容器创建成功"
fi

# 配置容器内串口
if [ "$HAS_IMU" = "true" ]; then
    docker exec "$CONTAINER_NAME" bash -c "
        rm -f /dev/wheeltec_lidar /dev/yesense_imu
        ln -sf '$LIDAR_DEV' /dev/wheeltec_lidar
        ln -sf '$IMU_DEV'   /dev/yesense_imu
        chmod 666 '$LIDAR_DEV' '$IMU_DEV' /dev/wheeltec_lidar /dev/yesense_imu 2>/dev/null || true
    " >/dev/null 2>&1
else
    docker exec "$CONTAINER_NAME" bash -c "
        rm -f /dev/wheeltec_lidar /dev/yesense_imu
        ln -sf '$LIDAR_DEV' /dev/wheeltec_lidar
        chmod 666 '$LIDAR_DEV' /dev/wheeltec_lidar 2>/dev/null || true
    " >/dev/null 2>&1
fi
log_info "容器串口配置完成"

# 3. 安装依赖
log_step "[3/5] 检查并安装 ROS 依赖..."
if ! docker exec "$CONTAINER_NAME" test -f /tmp/.ros_deps_installed 2>/dev/null; then
    docker exec "$CONTAINER_NAME" bash -c "
        export DEBIAN_FRONTEND=noninteractive
        # 清华源
        cat > /etc/apt/sources.list << 'EOF'
deb http://archive.ubuntu.com/ubuntu/ focal main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ focal-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ focal-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ focal-security main restricted universe multiverse
EOF
        cat > /etc/apt/sources.list.d/ros1-latest.list << 'EOF'
deb [arch=amd64] http://packages.ros.org/ros/ubuntu/ focal main
EOF
        if ! apt-key list 2>/dev/null | grep -q 'F42ED6FBAB17C654'; then
            curl -sL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | apt-key add - 2>/dev/null || true
        fi
        rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock
        apt-get clean && apt-get update >/dev/null 2>&1
    " >/dev/null 2>&1

    docker exec "$CONTAINER_NAME" bash -c "
        source /opt/ros/noetic/setup.bash
        apt-get install -y git ros-noetic-tf2-tools ros-noetic-rviz-imu-plugin ros-noetic-serial ros-noetic-map-server ros-noetic-imu-complementary-filter libceres1 libgoogle-glog0v5 liblua5.2-0 libpcl-common1.10 >/dev/null 2>&1 || true
    " >/dev/null 2>&1
    docker exec "$CONTAINER_NAME" touch /tmp/.ros_deps_installed
    log_info "依赖安装完成"
else
    log_info "依赖已安装，跳过"
fi

# 4. 编译
log_step "[4/5] 编译 ROS 工作空间..."
need_build=0
if ! docker exec "$CONTAINER_NAME" test -f "$CATKIN_WS/devel/lib/ldlidar/ldlidar" 2>/dev/null; then
    log_info "首次编译..."
    need_build=1
elif needs_rebuild; then
    log_info "检测到源码变更，增量编译..."
    need_build=1
else
    log_info "源码未变更，跳过编译"
fi

if [ "$need_build" -eq 1 ]; then
    docker exec "$CONTAINER_NAME" bash -c "
        source /opt/ros/noetic/setup.bash
        cd $CATKIN_WS
        if [ -d src/cartographer ]; then
            mv src/cartographer /tmp/cartographer_bak_\$\$ && catkin_make 2>&1 | tail -15 && mv /tmp/cartographer_bak_\$\$ src/cartographer
        else
            catkin_make 2>&1 | tail -15
        fi
    "
    # 同步 launch 文件和 lua 配置文件到 install_isolated（catkin_make 只编译不安装）
    docker exec "$CONTAINER_NAME" bash -c "
        for pkg_dir in $CATKIN_WS/src/*/; do
            pkg_name=\$(basename \$pkg_dir)
            # 同步 launch 文件
            if [ -d \$pkg_dir/launch ] && [ -d $CATKIN_WS/install_isolated/share/\$pkg_name/launch ]; then
                cp -u \$pkg_dir/launch/*.launch $CATKIN_WS/install_isolated/share/\$pkg_name/launch/ 2>/dev/null || true
            fi
            # 同步 lua 配置文件（Cartographer 配置）
            if [ -d \$pkg_dir/configuration_files ] && [ -d $CATKIN_WS/install_isolated/share/\$pkg_name/configuration_files ]; then
                cp -u \$pkg_dir/configuration_files/*.lua $CATKIN_WS/install_isolated/share/\$pkg_name/configuration_files/ 2>/dev/null || true
            fi
        done
    "
    touch /tmp/.catkin_last_build
    docker exec "$CONTAINER_NAME" touch /tmp/.catkin_last_build
    log_info "编译完成"
fi

# 5. 启动 ROS 节点
log_step "[5/5] 启动 ROS 节点..."

# 彻底清理残留 ROS 进程
log_info "检查并清理残留进程..."
docker exec "$CONTAINER_NAME" bash -c "
    # 先尝试优雅终止
    for p in \$(pgrep -x roscore 2>/dev/null); do kill -TERM \$p 2>/dev/null; done
    for p in \$(pgrep -f roslaunch 2>/dev/null); do kill -TERM \$p 2>/dev/null; done
    sleep 2
    # 强制终止
    for p in \$(pgrep -x roscore 2>/dev/null); do kill -KILL \$p 2>/dev/null; done
    for p in \$(pgrep -f roslaunch 2>/dev/null); do kill -KILL \$p 2>/dev/null; done
    sleep 1
    # 确认干净
    if pgrep -x roscore >/dev/null 2>&1 || pgrep -f roslaunch >/dev/null 2>&1; then
        echo 'STILL_RUNNING'
    else
        echo 'CLEAN'
    fi
" 2>/dev/null | grep -q 'STILL_RUNNING' && {
    log_warn "残留进程未能清理，重启容器..."
    docker restart "$CONTAINER_NAME" >/dev/null
    sleep 3
}

# 启动 roscore（先检查是否已有）
if ! docker exec "$CONTAINER_NAME" pgrep -x roscore >/dev/null 2>&1; then
    docker exec -d "$CONTAINER_NAME" bash -c "
        export ROS_MASTER_URI=http://localhost:11311
        export ROS_HOSTNAME=localhost
        source /opt/ros/noetic/setup.bash
        roscore > /tmp/roscore.log 2>&1
    "
    log_info "roscore 启动中..."
    sleep 5
else
    log_info "roscore 已在运行"
fi

# 确定 Cartographer 配置名
if [ "$HAS_IMU" = "true" ] && [ "$USE_WHEEL_ODOM" = "true" ]; then
    CONFIG_BASENAME="ld14p_imu_wheel"
elif [ "$HAS_IMU" = "true" ]; then
    CONFIG_BASENAME="ld14p_imu"
elif [ "$USE_WHEEL_ODOM" = "true" ]; then
    CONFIG_BASENAME="ld14p_wheel"
else
    CONFIG_BASENAME="ld14p"
fi

# 启动 launch
LAUNCH_FILE="$CATKIN_WS/src/cartographer_ld06/launch/cartographer_ld06.launch"
SETUP="source $CATKIN_WS/devel/setup.bash && DEVEL_PREFIX=\$CATKIN_DEVEL_PREFIX && source $CATKIN_WS/install_isolated/setup.bash && export CATKIN_DEVEL_PREFIX=\$DEVEL_PREFIX && export ROS_PACKAGE_PATH=\$ROS_PACKAGE_PATH:/catkin_ws/src"
MODE_NAME="Cartographer 2D SLAM"
EXTRA_ARGS="use_imu:=$HAS_IMU config_basename:=$CONFIG_BASENAME use_wheel_odom:=$USE_WHEEL_ODOM"

docker exec -d "$CONTAINER_NAME" bash -c "
    export ROS_MASTER_URI=http://localhost:11311
    export ROS_HOSTNAME=localhost
    source /opt/ros/noetic/setup.bash
    $SETUP
    roslaunch $LAUNCH_FILE $EXTRA_ARGS > /tmp/roslaunch.log 2>&1
"
log_info "roslaunch 启动中 (Cartographer 2D SLAM)..."
sleep 5
log_info "ROS 节点已启动"

# -----------------------------------------------------------
# 启动完成提示
# -----------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                     启动完成                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  模式 : Cartographer 2D SLAM"
echo "  雷达 : $LIDAR_DEV"
if [ "$HAS_IMU" = "true" ]; then
    echo "  IMU  : $IMU_DEV"
else
    echo "  IMU  : 未连接（纯雷达模式）"
fi
echo ""
echo "  TF 树: map → odom → base_link → laser"
if [ "$HAS_IMU" = "true" ]; then
    echo "                                   └─→ imu_link"
fi
echo ""
echo "  常用命令:"
echo "    查看日志   : sudo docker exec $CONTAINER_NAME tail -f /tmp/roslaunch.log"
echo "    查看节点   : sudo docker exec $CONTAINER_NAME bash -c 'source /catkin_ws/devel/setup.bash && rosnode list'"
echo "    查看话题   : sudo docker exec $CONTAINER_NAME bash -c 'source /catkin_ws/devel/setup.bash && rostopic list'"
echo "    查看雷达 Hz: sudo docker exec $CONTAINER_NAME bash -c 'source /catkin_ws/devel/setup.bash && rostopic hz /scan'"
echo "    查看地图 Hz: sudo docker exec $CONTAINER_NAME bash -c 'source /catkin_ws/devel/setup.bash && rostopic hz /map'"
echo "    查看 TF    : sudo docker exec $CONTAINER_NAME bash -c 'source /catkin_ws/devel/setup.bash && rosrun tf tf_echo map laser'"
echo "    打开 RViz  : xhost +local:root && sudo docker exec -it $CONTAINER_NAME bash -c 'export DISPLAY=:0 && source /catkin_ws/devel/setup.bash && rviz -d /catkin_ws/src/cartographer_ld06/rviz/cartographer.rviz'"
echo "    保存地图   : sudo docker exec $CONTAINER_NAME bash -c 'source /catkin_ws/devel/setup.bash && rosrun map_server map_saver -f /catkin_ws/map/my_map'"
echo "    停止系统   : sudo docker stop $CONTAINER_NAME"
echo ""
