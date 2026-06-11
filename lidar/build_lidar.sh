#!/bin/bash
# 在ROS2容器中编译和运行lidar功能包

echo "===== ROS2 Lidar 环境设置 ====="

# 初始化ROS2环境
source /opt/ros/humble/setup.bash

# 创建工作空间（如果不存在）
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws

# 复制lidar功能包到工作空间
if [ ! -d "src/ldlidar_ros2" ]; then
    cp -r /home/tzb/lidar/ldlidar_ros2 src/
    echo "已复制lidar功能包到工作空间"
fi

cd ~/ros2_ws

# 编译功能包
echo "正在编译ldlidar功能包..."
colcon build --packages-select ldlidar

if [ $? -eq 0 ]; then
    echo "编译成功！"
    echo ""
    echo "===== 使用方法 ====="
    echo "1. 启动stl06n串口雷达: ros2 launch ldlidar stl06n.launch.py"
    echo "2. 启动stl06n网口雷达: ros2 launch ldlidar stl06nnet.launch.py"
    echo "3. 启动ld06串口雷达: ros2 launch ldlidar ld06.launch.py"
    echo "4. 启动ld06网口雷达: ros2 launch ldlidar ld06net.launch.py"
    echo ""
    echo "启动前请确保已source环境: source ~/ros2_ws/install/setup.bash"
else
    echo "编译失败，请检查错误信息"
fi
