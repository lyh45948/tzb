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

## Git Workflow (Mandatory)

> This sub-project follows the workspace-wide **GitHub Flow** (see root `AGENTS.md` §8). Full rules below.

### Iron Rule

- `main` **must always be runnable**. **Never commit any code change directly to `main`** — C++ drivers, Python scripts, launch files, lua configs, and shell scripts all require a branch.
- Any code change must be made on a dedicated branch cut from the latest `main`, then merged back.
- **Exception**: changes limited to `AGENTS.md` / `CLAUDE.md` / `*.md` / comments (no executable logic) may be committed directly to `main` — but a branch is still encouraged.

### Standard Flow (every change)

```bash
# 1. Start from the latest main
git checkout main && git pull

# 2. Create a branch
git checkout -b <type>/<scope>-<summary>

# 3. Work & commit with Conventional Commits
git commit -m "<type>(<scope>): <subject>"

# 4. Self-check: rebuild per §11 checklist if C++/lua/launch changed; review diff
git diff main

# 5. Merge back to main (no-ff keeps branch history)
git checkout main && git merge --no-ff <branch>

# 6. Delete the branch
git branch -d <branch>
```

### Branch Naming

- **Types:** `feat`, `fix`, `docs`, `refactor`, `chore`
- **Scopes:** `slam`, `ldlidar`, `yesense`, `cartographer`, `docker`, `docs`, `config`
- Examples: `fix/ldlidar-frame-parse`, `feat/cartographer-imu-tune`, `chore/docker-resource-limit`

### Commit Format
```
<type>(<scope>): <subject>
```

### Sync Obligation

If a change affects anything described in this file or `AGENTS.md` — TF tree, serial port mapping, Cartographer parameters, launch configs, or the branch model — **update the corresponding guidance file in the same branch**. Docs/code drift is technical debt; do not leave it.

### Workspace Hygiene

- `git status` should be clean before cutting a new branch. `git stash` or commit uncommitted changes first — **never mix unrelated changes into a task branch**.