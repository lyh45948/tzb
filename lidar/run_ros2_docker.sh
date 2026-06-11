#!/bin/bash
# ROS2 Lidar Docker 运行脚本

CONTAINER_NAME="ros2-lidar"
ROS2_IMAGE="osrf/ros:humble-desktop"
MOUNT_DIR="/home/tzb/lidar"

# 检查Docker是否运行
if ! systemctl is-active docker > /dev/null 2>&1; then
    echo "Docker服务未运行，正在启动..."
    sudo systemctl start docker
fi

# 检查镜像是否存在，不存在则拉取
if ! docker image inspect $ROS2_IMAGE > /dev/null 2>&1; then
    echo "正在拉取ROS2镜像，这可能需要几分钟到几十分钟..."
    echo "如果下载过慢，可以尝试 Ctrl+C 取消，然后配置其他镜像源"
    docker pull $ROS2_IMAGE
fi

# 运行容器
echo "启动ROS2容器..."
docker run -it --rm \
    --name $CONTAINER_NAME \
    --network host \
    --privileged \
    -v $MOUNT_DIR:$MOUNT_DIR \
    -w $MOUNT_DIR \
    $ROS2_IMAGE bash
