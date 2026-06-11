#!/bin/bash
set -euo pipefail

# ============================================================
# IMU Allan 方差校准脚本
# 用途：录制静止 IMU 数据，用于分析噪声参数
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="ros_container"
BAG_DIR="$SCRIPT_DIR/catkin_ws/imu_calibration"

usage() {
    cat << 'EOF'
用法: ./imu_calibration.sh [选项]

选项:
  record [分钟数]   录制 IMU 静止数据（默认 30 分钟）
  analyze           分析录制的数据（需要 allan_variance_ros）
  help              显示此帮助

流程:
  1. 将小车放在平坦地面上，确保完全静止
  2. 运行: sudo ./imu_calibration.sh record 30
  3. 等待录制完成
  4. 运行: sudo ./imu_calibration.sh analyze
  5. 根据输出的噪声参数更新 launch 文件

说明:
  - 录制时间越长，低频噪声（偏置不稳定性）的分辨率越高
  - 建议至少 30 分钟，理想情况 2 小时
  - 录制期间不要触碰小车
EOF
}

log_step() { echo "[$(date +%H:%M:%S)] $1"; }
log_info() { echo "  [INFO] $1"; }

case "${1:-help}" in
    record)
        MINUTES="${2:-30}"
        DURATION=$((MINUTES * 60))

        echo ""
        echo "╔══════════════════════════════════════════════╗"
        echo "║  IMU Allan 方差校准 - 数据录制               ║"
        echo "╚══════════════════════════════════════════════╝"
        echo ""
        echo "  录制时长: ${MINUTES} 分钟"
        echo "  注意: 请确保小车完全静止！"
        echo ""

        # 确保容器运行中
        if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
            echo "  [ERROR] Docker 容器未运行，请先启动 SLAM: sudo ./start_slam.sh"
            exit 1
        fi

        # 创建输出目录
        mkdir -p "$BAG_DIR"

        # 检查 IMU 话题是否存在
        log_step "[1/3] 检查 IMU 话题..."
        TOPIC=$(docker exec "$CONTAINER_NAME" bash -c \
            "source /catkin_ws/devel/setup.bash && rostopic list 2>/dev/null | grep -E '^/imu$|^/imu_raw$' | head -1" 2>/dev/null || true)

        if [ -z "$TOPIC" ]; then
            echo "  [ERROR] 未找到 /imu 或 /imu_raw 话题，请先启动 SLAM"
            exit 1
        fi
        log_info "使用话题: $TOPIC"

        # 录制
        log_step "[2/3] 开始录制 (${MINUTES} 分钟)..."
        echo "  按 Ctrl+C 可提前结束录制"
        echo ""

        BAG_FILE="$BAG_DIR/imu_static_$(date +%Y%m%d_%H%M%S).bag"

        docker exec "$CONTAINER_NAME" bash -c "
            source /opt/ros/noetic/setup.bash
            source /catkin_ws/devel/setup.bash
            rosbag record -O /catkin_ws/imu_calibration/$(basename "$BAG_FILE") \
                --duration=$DURATION \
                $TOPIC 2>&1
        "

        log_step "[3/3] 录制完成"
        log_info "数据保存在: $BAG_FILE"
        echo ""
        echo "  下一步: sudo ./imu_calibration.sh analyze"
        echo ""

        # 检查是否安装了 allan_variance_ros
        if ! docker exec "$CONTAINER_NAME" test -d /catkin_ws/src/allan_variance_ros 2>/dev/null; then
            echo ""
            echo "  [WARN] 未安装 allan_variance_ros，需要先安装："
            echo "    docker exec $CONTAINER_NAME bash -c '"
            echo "      cd /catkin_ws/src &&"
            echo "      git clone https://github.com/ori-drs/allan_variance_ros.git &&"
            echo "      cd /catkin_ws && catkin_make'"
            echo ""
        fi
        ;;

    analyze)
        echo ""
        echo "╔══════════════════════════════════════════════╗"
        echo "║  IMU Allan 方差校准 - 数据分析               ║"
        echo "╚══════════════════════════════════════════════╝"
        echo ""

        # 检查是否有录制数据
        BAG_FILE=$(docker exec "$CONTAINER_NAME" bash -c "ls -t /catkin_ws/imu_calibration/*.bag 2>/dev/null | head -1" || true)
        if [ -z "$BAG_FILE" ]; then
            echo "  [ERROR] 未找到录制数据，请先运行: sudo ./imu_calibration.sh record"
            exit 1
        fi
        log_info "使用数据: $BAG_FILE"

        # 检查 allan_variance_ros
        if ! docker exec "$CONTAINER_NAME" test -d /catkin_ws/src/allan_variance_ros 2>/dev/null; then
            echo "  [ERROR] 未安装 allan_variance_ros"
            echo "  请先安装:"
            echo "    docker exec $CONTAINER_NAME bash -c '"
            echo "      cd /catkin_ws/src &&"
            echo "      git clone https://github.com/ori-drs/allan_variance_ros.git &&"
            echo "      cd /catkin_ws && catkin_make'"
            exit 1
        fi

        log_step "[1/2] 预处理 bag 文件（按时间戳重排）..."
        COOKED_BAG="/catkin_ws/imu_calibration/imu_cooked.bag"
        docker exec "$CONTAINER_NAME" bash -c "
            source /opt/ros/noetic/setup.bash
            source /catkin_ws/devel/setup.bash
            rosrun allan_variance_ros cookbag.py \
                --input $BAG_FILE \
                --output $COOKED_BAG
        "

        log_step "[2/2] 运行 Allan 方差分析..."
        docker exec "$CONTAINER_NAME" bash -c "
            source /opt/ros/noetic/setup.bash
            source /catkin_ws/devel/setup.bash
            rosrun allan_variance_ros allan_variance \
                /catkin_ws/imu_calibration/ \
                /catkin_ws/src/allan_variance_ros/config/yesense_h30.yaml
        "

        echo ""
        echo "  分析完成！请查看输出目录中的结果文件。"
        echo ""
        echo "  关键参数说明："
        echo "    - Angle Random Walk (ARW): 陀螺仪白噪声，单位 deg/sqrt(hr)"
        echo "    - Bias Instability: 陀螺仪偏置不稳定性，单位 deg/hr"
        echo "    - Velocity Random Walk (VRW): 加速度计白噪声，单位 m/s/sqrt(hr)"
        echo ""
        echo "  将这些值用于更新 yesense_ahrs.launch 中的 stddev 参数："
        echo "    orientation_stddev ≈ ARW * pi/180 / 60"
        echo "    angular_velocity_stddev ≈ ARW * pi/180 / 60"
        echo "    linear_acceleration_stddev ≈ VRW / 60"
        echo ""
        ;;

    help|--help|-h)
        usage
        ;;

    *)
        echo "未知命令: $1"
        usage
        exit 1
        ;;
esac
