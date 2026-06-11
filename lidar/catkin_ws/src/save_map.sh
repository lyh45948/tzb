#!/bin/bash
# 保存 Cartographer 生成的地图

CONTAINER="ros_container"
MAP_DIR="/catkin_ws/map"

if [ "$EUID" -ne 0 ]; then
    exec sudo bash "$0" "$@"
fi

# 检查容器是否运行
if ! docker ps | grep -q "$CONTAINER"; then
    echo "错误: Docker 容器 $CONTAINER 未运行"
    exit 1
fi

# 生成带时间戳的文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAP_NAME="${MAP_DIR}/${TIMESTAMP}"

echo "正在保存地图到 ${MAP_NAME}..."

docker exec "$CONTAINER" bash -c "
    source /opt/ros/noetic/setup.bash
    source /catkin_ws/devel/setup.bash
    mkdir -p ${MAP_DIR}
    rosrun map_server map_saver -f ${MAP_NAME}
"

echo ""
echo "地图保存完成:"
echo "  PGM 图像: ${MAP_NAME}.pgm"
echo "  YAML 配置: ${MAP_NAME}.yaml"
