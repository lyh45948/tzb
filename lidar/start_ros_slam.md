# ROS 激光雷达 + IMU + Cartographer SLAM 启动文档

## 硬件连接

| 设备 | USB 端口 | 串口设备 | 波特率 |
|------|----------|----------|--------|
| 激光雷达 (LD06) | USB0 | /dev/ttyCH343USB0 → /dev/wheeltec_lidar | 230400 |
| IMU (Yesense) | USB1 | /dev/ttyCH343USB1 → /dev/yesense_IMU | 460800 |

---

## 1. 启动 Docker 容器

```bash
# 停止旧容器（如有）
sudo docker stop ros_container && sudo docker rm ros_container

# 启动新容器（映射两个串口设备）
sudo docker run -d \
  --device=/dev/ttyCH343USB0:/dev/ttyCH343USB0 \
  --device=/dev/ttyCH343USB1:/dev/ttyCH343USB1 \
  -v /home/tzb/lidar/catkin_ws:/catkin_ws \
  -e DISPLAY=:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --name ros_container \
  osrf/ros:noetic-desktop bash -c "sleep infinity"
```

---

## 2. 配置串口权限和符号链接

```bash
# 主机端设置
sudo ln -sf /dev/ttyCH343USB1 /dev/wheeltec_lidar
sudo ln -sf /dev/ttyCH343USB0 /dev/yesense_imu
sudo chmod 666 /dev/ttyCH343USB0 /dev/ttyCH343USB1
sudo chmod 666 /dev/wheeltec_lidar /dev/yesense_imu

# 容器内设置
sudo docker exec ros_container bash -c "ln -sf /dev/ttyCH343USB1 /dev/wheeltec_lidar"
sudo docker exec ros_container bash -c "ln -sf /dev/ttyCH343USB0 /dev/yesense_imu"
```

---

## 3. 编译工作空间

```bash
# 进入容器
sudo docker exec -it ros_container bash

# 编译
cd /catkin_ws
source /opt/ros/noetic/setup.bash
catkin_make
```

---

## 4. 启动节点（每个命令在独立终端）

### 终端 1：启动 ROS 主节点
```bash
sudo docker exec -it ros_container bash
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
roscore
```

### 终端 2：启动 IMU 节点
```bash
sudo docker exec -it ros_container bash
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
roslaunch yesense_imu yesense_ahrs.launch
```

### 终端 3：启动激光雷达
```bash
sudo docker exec -it ros_container bash
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
roslaunch ldlidar ld06.launch
```

### 终端 4：启动 Cartographer SLAM
```bash
sudo docker exec -it ros_container bash
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
roslaunch cartographer_ld06 cartographer_ld06.launch
```

### 终端 5：启动 RViz 可视化
```bash
sudo docker exec -it ros_container bash
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
rviz
```

---

## 5. RViz 配置

### 查看激光扫描
1. 左下角 **Add** → **By topic** → `/scan` → **OK**
2. 左侧 LaserScan → **Style**: Points，**Size**: 0.1
3. **Fixed Frame**: `base_link`

### 查看 IMU 数据
1. **Add** → **By topic** → `/imu` → **OK**
2. 选中 Imu → 勾选 **Show orientation**

### 查看地图
1. **Add** → **By topic** → `/map` → **OK**

### 查看 TF 坐标树
1. **Add** → **By display type** → **TF**

---

## 6. 一键启动脚本

创建 `/home/tzb/lidar/start_slam.sh`：

```bash
#!/bin/bash
set -e

echo "===== ROS SLAM 启动脚本 ====="

# 检查容器是否运行
if ! sudo docker ps | grep -q ros_container; then
    echo "启动 Docker 容器..."
    sudo docker run -d \
      --device=/dev/ttyCH343USB0:/dev/ttyCH343USB0 \
      --device=/dev/ttyCH343USB1:/dev/ttyCH343USB1 \
      # 注意：实际映射可能与文档相反，请根据 start_slam.sh 中的符号链接配置调整
      -v /home/tzb/lidar/catkin_ws:/catkin_ws \
      -e DISPLAY=:0 \
      -v /tmp/.X11-unix:/tmp/.X11-unix \
      --name ros_container \
      osrf/ros:noetic-desktop bash -c "sleep infinity"

    echo "配置串口设备..."
    sudo docker exec ros_container bash -c "ln -sf /dev/ttyCH343USB0 /dev/wheeltec_lidar"
    sudo docker exec ros_container bash -c "ln -sf /dev/ttyCH343USB1 /dev/yesense_imu"
fi

echo ""
echo "===== 启动完成 ====="
echo "请在新终端中执行以下命令："
echo ""
echo "1. 启动 ROS:     docker exec -it ros_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && roscore'"
echo "2. 启动 IMU:     docker exec -it ros_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && roslaunch yesense_imu yesense_ahrs.launch'"
echo "3. 启动雷达:     docker exec -it ros_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && roslaunch ldlidar ld06.launch'"
echo "4. 启动 SLAM:    docker exec -it ros_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && roslaunch cartographer_ld06 cartographer_ld06.launch'"
echo "5. 启动 RViz:    docker exec -it ros_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && rviz'"
echo ""
```

---

## 7. 常用命令

```bash
# 查看话题列表
rostopic list

# 查看雷达数据
rostopic echo /scan

# 查看 IMU 数据
rostopic echo /imu

# 查看节点关系图
rqt_graph

# 保存地图为图片
rosrun map_server map_saver -f /tmp/my_map
```

---

## 8. 故障排查

| 问题 | 解决方法 |
|------|----------|
| 串口无法打开 | 检查 symlink 和权限 `ls -la /dev/wheeltec*` |
| /scan 话题不存在 | 确认雷达节点已启动，检查 `rostopic list` |
| rviz 无显示 | 检查 Fixed Frame 设置为 `base_link` 或 `map` |
| IMU 无数据 | 检查 IMU 连接端口和波特率配置 |
| 地图不更新 | 确认 Cartographer 节点正在运行 |