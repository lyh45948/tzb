# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Overview

This workspace (`/home/tzb/tzb/`) contains **two independent sub-projects** that share physical hardware but have **no software coupling**. There is no root-level build system — all build/test/run commands operate within each subdirectory.

| Directory | Project | Tech Stack |
|-----------|---------|------------|
| `fwwb/` | Smart Factory Safety Monitoring & Control Platform (挑战杯 XA-202606) | OpenHarmony Hi3861, Python Flask, WeChat Mini Program, STM32 |
| `lidar/` | ROS1 Noetic SLAM System | ROS1 Noetic (Docker), C++11, Python 3 |

Each subdirectory has its own `CLAUDE.md` and `AGENTS.md` with detailed architecture, build commands, and protocols. **Read those before making changes within a sub-project.**

## Shared Hardware & Conflict Rules

Both projects use the same LD-14P/LD-STL-19P LiDAR and Yesense H30 IMU, but access them differently:

| Hardware | `fwwb/` Access | `lidar/` Access | Conflict |
|----------|----------------|-----------------|----------|
| LD-14P/LD-STL-19P LiDAR | Hi3861 reads via UART, forwards JSON over UDP to backend | Direct USB serial in Docker (`/dev/ttyCH343USB0`) | **Mutually exclusive** |
| Yesense H30 IMU | Hi3861 reads via I2C/UART, forwards JSON over UDP | Direct USB serial in Docker (`/dev/ttyCH343USB0/1`) | **Mutually exclusive** |

- `lidar/start_slam.sh` auto-detects CH343 ports and identifies devices by first byte (`0x59` = IMU, `0x54` = Lidar)
- If `fwwb` Hi3861 already occupies the hardware, `lidar/` cannot start; stop `fwwb` first or use separate hardware instances
- `fwwb` backend `.env` can set `IMU_MODE=serial` to directly claim USB IMU — this will also conflict with `lidar/`

## Navigation Reference

- **`fwwb/AGENTS.md`** — Full architecture, 5-layer communication protocol, build commands, code style, Git workflow
- **`fwwb/CLAUDE.md`** — Hardware parameters, FreeRTOS task table, PCF8574 I/O map, Vant Weapp icon reference
- **`lidar/AGENTS.md`** — ROS package structure, TF tree, launch file parameters, diagnostic commands
- **`lidar/CLAUDE.md`** — Docker/container commands, build instructions, RViz usage

## Root Directory Has No Build

Do not look for `package.json`, `pyproject.toml`, `CMakeLists.txt`, or `Cargo.toml` at the root level. There are none. Each sub-project is built independently:

```bash
# fwwb — Python backend
cd fwwb/backend && pip install -r requirements.txt && python main.py

# fwwb — Hi3861 firmware
cd fwwb/1/src && hb set && hb build

# lidar — ROS1 SLAM (host-side, uses Docker)
cd lidar && sudo ./start_slam.sh
```

## Cross-Cutting Concerns

- **Language**: Both projects use Chinese as the primary language for comments, documentation, logs, and variable names
- **Security**: No authentication on `fwwb` REST/UDP APIs; hardcoded WiFi credentials in `fwwb/1/src/.../voicecar_demo.c`; plaintext database credentials in `fwwb/backend/.env`
- **Testing**: Neither sub-project has automated unit tests for business code; validation is manual/hardware-in-the-loop
