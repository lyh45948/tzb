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
| LD-14P/LD-STL-19P LiDAR | Hi3861 has reserved the data struct (`LiDARFrame`, header `0x54`) in `sys_config.h` and serializes it to JSON in `udp_send_task.c`, but **no parsing task fills it yet** — fields stay zero. Effective LiDAR use is via `lidar/`. | Direct USB serial in Docker (`/dev/ttyCH343USB0`) → `/dev/wheeltec_lidar` | **Mutually exclusive** |
| Yesense H30 IMU | Hi3861 firmware **does not read IMU** (the old IMU task was removed). The `fwwb` backend reads IMU directly via `imu_service.py` (`tcp`/`serial`/`udp_passive`). | Direct USB serial in Docker (`/dev/ttyCH343USB0/1`) → `/dev/yesense_imu` | **Mutually exclusive** |

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

## Git Workflow (Mandatory)

> This is the **unified Git workflow for the entire workspace** — it applies equally to both `fwwb/` and `lidar/` sub-projects. Uses **GitHub Flow** (no `develop` branch). The sub-project `AGENTS.md` / `CLAUDE.md` files follow the same rule, differing only in `scope` naming.

### Iron Rule

- `main` **must always be runnable**. **Never commit any code change directly to `main`.**
- Any code change (`.c/.cpp/.py/.js/.ts/.vue/.lua/.launch/.sh`, etc.) must be made on a dedicated branch cut from the latest `main`, then merged back.
- **Exception**: changes limited to `AGENTS.md` / `CLAUDE.md` / `*.md` / comments (no executable logic) may be committed directly to `main` — but a branch is still encouraged for consistency.

### Standard Flow (every change)

```bash
# 1. Start from the latest main
git checkout main && git pull

# 2. Create a branch (type/scope/summary — see naming below)
git checkout -b <type>/<scope>-<summary>

# 3. Work & commit with Conventional Commits
git commit -m "<type>(<scope>): <subject>"

# 4. Self-check: build/run locally if possible; review diff against main
git diff main

# 5. Merge back to main (no-ff keeps branch history traceable)
git checkout main && git merge --no-ff <branch>

# 6. Delete the branch
git branch -d <branch>
```

### Branch Naming

- **type**: `feat` (new feature), `fix` (bug fix), `docs` (documentation), `refactor`, `chore` (build/tooling)
- **scope** (pick by sub-project):
  - Common: `fwwb`, `lidar`, `docs`, `config`
  - fwwb only: `backend`, `miniapp`, `hi3861`, `stm32`, `dashboard`, `agent`, `vision`
  - lidar only: `slam`, `ldlidar`, `yesense`, `cartographer`, `docker`
- Examples: `feat/backend-add-imu-endpoint`, `fix/ldlidar-frame-parse`, `docs/git-workflow-rules`

### Sync Obligation

If a change affects anything described in a guidance file (`AGENTS.md` / `CLAUDE.md` in either sub-project) — architecture, style, config, ports, FreeRTOS tasks, protocols, TF tree, or the branch model itself — **you must update the corresponding guidance file in the same branch**. Drift between docs and code is technical debt; do not leave it behind.

### Workspace Hygiene

- `git status` should be clean before cutting a new branch. If there are uncommitted changes, `git stash` or commit them first — **never mix unrelated changes into a task branch**.
- Before merging, ensure the branch contains only this task's changes.

## Cross-Cutting Concerns

- **Language**: Both projects use Chinese as the primary language for comments, documentation, logs, and variable names
- **Security**: No authentication on `fwwb` REST/UDP APIs; hardcoded WiFi credentials in `fwwb/1/src/.../voicecar_demo.c`; plaintext database credentials in `fwwb/backend/.env`
- **Testing**: Neither sub-project has automated unit tests for business code; validation is manual/hardware-in-the-loop
