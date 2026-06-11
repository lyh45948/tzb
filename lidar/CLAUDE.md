# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a LDROBOT LiDAR driver repository with ROS1/ROS2 support for LD series lidar devices (LD-14P, STL06N, STL19P, STL26, STL27L).

## Environment

- **ROS Version**: ROS1 Noetic (primary), ROS2 Humble (secondary)
- **Development**: Docker-based (`osrf/ros:noetic-desktop` image recommended)
- **Lidar Device**: `/dev/ttyCH343USB0` (serial), symlinked to `/dev/wheeltec_lidar`
- **Baud Rate**: 230400

## Common Commands

### Build ROS1 package (in Docker)
```bash
docker run -it --device=/dev/ttyCH343USB0:/dev/ttyCH343USB0 -v /home/tzb/lidar/catkin_ws:/catkin_ws -e DISPLAY=:0 -v /tmp/.X11-unix:/tmp/.X11-unix --privileged osrf/ros:noetic-desktop bash

# Inside container
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
catkin_make
```

### Run Lidar Node
```bash
# Serial mode
roslaunch ldlidar ld14p.launch

# Network mode
roslaunch ldlidar ld14pnet.launch
```

### View Lidar Data
```bash
rostopic echo /scan
rviz  # Fixed frame: laser, Topic: /scan
```

### Container Management
```bash
# Start container
sudo docker run -d --device=/dev/ttyCH343USB0:/dev/ttyCH343USB0 -v /home/tzb/lidar/catkin_ws:/catkin_ws -e DISPLAY=:0 -v /tmp/.X11-unix:/tmp/.X11-unix --name ros_container osrf/ros:noetic-desktop bash -c "sleep infinity"

# Create lidar symlink in container
sudo docker exec ros_container bash -c "ln -sf /dev/ttyCH343USB0 /dev/wheeltec_lidar && chmod 666 /dev/wheeltec_lidar"

# Stop/Remove container
sudo docker stop ros_container && sudo docker rm ros_container
```

## Key Files

- `ldlidar_ros1/ldlidar/` - ROS1 lidar driver package (CMakeLists.txt + src/)
- `ldlidar_ros1/ldlidar_driver/` - Core lidar driver library (standalone, no ROS dependency)
- `ldlidar_ros1/ldlidar_udev.sh` - udev rules for serial port aliasing
- `catkin_ws/src/ldlidar/launch/` - Launch files for different lidar models

## Architecture

- **ldlidar** (ROS node): Wrapper that uses ldlidar_driver, publishes laser scan data
- **ldlidar_driver** (core library): Platform-independent lidar communication (serial/TCP)
  - `include/core/ldlidar_driver.h` - Main API
  - `include/dataprocess/lipkg.h` - Data packet parsing
  - `include/filter/tofbf.h` - Noise filtering

## Device Setup

Serial port `/dev/wheeltec_lidar` is created via symlink to actual device. If using udev rules instead:
```bash
sudo bash /home/tzb/lidar/ldlidar_ros1/ldlidar_udev.sh
```