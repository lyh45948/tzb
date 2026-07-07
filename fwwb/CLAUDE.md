# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Smart Factory Safety Monitoring & Control Platform** based on Hi3861 (OpenHarmony) for the "挑战杯" 揭榜挂帅擂台赛 (XA-202606). It monitors factory environment safety, detects hazardous gases, enables AGV obstacle avoidance, and counts goods — all built on a domestically-developed OS.

**Competition Requirements (XA-202606):**
1. 温湿度智能监控 — Temperature/humidity monitoring
2. 红外感应照明 — IR-based auto lighting
3. 危气监测 — Hazardous gas detection (CO2, smoke, CO)
4. AGV避障系统 — AGV obstacle avoidance via ultrasonic
5. 货物感应计数 — Photoelectric goods counting

## Build Commands

### Python Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # configure MYSQL_*, TCP_*, UDP_*
mysql -u root -p < backend/sql/init.sql
python main.py
```

Backend: TCP service on **8888** for mini-program connections, UDP on **7788** for Hi3861 communication.

### Hi3861 Firmware (DevEco Device Tool)
1. Open VSCode with DevEco Device Tool plugin
2. Import project from `1/src` directory
3. Select SOC: HI3861, Board: hi3861
4. Click "build"

Output: `1/src/out/hispark_pegasus/wifiiot_hispark_pegasus/Hi3861_wifiiot_app_allinone.bin`

### Hi3861 Firmware (Command Line)
```bash
cd 1\src
hb set
hb build
```

### Flashing Hi3861
HiBurn tool: Baud 2000000, Loader: Hi3861_loader_signed.bin

### STM32 Projects
- **Motor Driver** (`FS-Hi3861-Motor-Driver(Release)/`): STM32CubeMX project (.ioc), Keil MDK-ARM build
- **Sensor Board** (`FS-STM32G030-CS100A(Release)/`): STM32CubeMX project, Keil MDK-ARM build

## Architecture

### 5-Layer Communication Protocol
See `4层通信协议汇总.md` for full protocol details.

| Layer | Medium | Format | Port/Baud |
|-------|--------|--------|-----------|
| Mini Program ↔ Backend | WiFi TCP | JSON | 8888 |
| Backend ↔ Hi3861 | WiFi UDP | JSON | 7788 |
| Hi3861 ↔ STM32 Motor | UART | JSON | 115200 |
| STM32 Motor ↔ STM32 Sensor | UART | Binary | 115200 |
| Voice Module → Hi3861 | UART | Hex | 115200 |

### Data Flow
```
[Mini Program] --TCP:8888--> [Backend] --UDP:7788--> [Hi3861] --UART(JSON)--> [STM32 Motor]
     ^                            |                                  |
     +---------TCP:8888-----------+                                  v
                          [MySQL DB]                    [STM32 Sensor Board]
```

**Port mapping:** Mini Program↔Backend uses **TCP:8888**, Backend↔Hi3861 uses **UDP:7788**

### Key JSON Commands (App → Hi3861)
```json
{"carStatus": "on/off"}                    // Power control
{"carStatus": "run/back/left/right/stop"} // Movement
{"carMode": "manual/avoid/line/path"}     // Mode switch
{"joyX": int, "joyY": int}               // Joystick (-100 to 100)
{"carSpeed": "low/middle/high"}           // Speed gear
{"smartLight": {"mode": "auto/manual", "brightness": 0-100}}
```

## Functional Modules

### 1. Temperature/Humidity Monitoring
- **Sensor**: SHT20 (I2C, address 0x80)
- **Thresholds**: Temp: 30°C warning / 35°C danger; Humidity: 75% warning / 80% danger
- **Data saved** to `sensor_data` table every 1 second

### 2. IR Auto Lighting
- **Sensor**: AP3216C (ambient light/proximity, I2C 0x3C) + PIR human detection via PCF8574
- **Logic**: Brightness auto-adjusts based on ambient light level and time of day
- **PCF8574 P7**: PIR human induction signal
- **Time behavior**: 23:00-05:00 sleep, 05:00-08:00 dawn ramp, 08:00-17:00 day responsive, 17:00-23:00 evening fade

### 3. Hazardous Gas Monitoring
- **Sensors**: SGP30 (CO2/TVOC, I2C 0x80), MQ-2 (smoke), MQ-7 (CO) — gasMic from SGP30
- **Thresholds**: CO2 800ppm warning / 1000ppm danger; Smoke 300/500; CO 35ppm/50ppm
- **UI**: `pages/alert_center/` with multi-level alerts (warning/danger/critical)
- **PCF8574 P5**: Gas sensor signal

### 4. AGV Obstacle Avoidance
- **Sensor**: HC-SR04 ultrasonic (via STM32 UART)
- **Thresholds**: 30cm warning / 15cm danger
- **Hi3861 task**: `auto_avoid_task.c` (5ms interval)
- **Auto stop or绕行** when obstacle detected

### 5. Goods Counting
- **Sensor**: IR infrared (E3F-DS30C) via PCF8574 P6 pulse counter
- Planned feature (sensor not yet installed)

## Backend Structure
```
backend/
├── main.py
├── config.py                  # MYSQL_*, TCP_*, UDP_* env config
├── requirements.txt
├── .env
├── sql/init.sql              # Database schema
└── app/
    ├── __init__.py
    ├── models/
    │   ├── device.py, car_status.py, sensor_data.py
    │   ├── smart_light_status.py, control_command.py
    │   └── car_sensor_data.py, simulated_sensor_data.py
    ├── services/
    │   ├── udp_service.py         # UDP with Hi3861 (port 7788)
    │   ├── udp_miniapp_service.py # TCP with mini-program (port 8888)
    │   ├── tcp_service.py, data_service.py
    │   ├── smart_light_service.py  # Smart lighting logic
    │   └── simulation_service.py   # Sensor data simulation
    └── utils/logger.py, protocol.py
```

### Database Tables
- `devices` — Device registration and status
- `sensor_data` — Temperature, humidity, lux readings (saved every 1 second)
- `car_status` — Car movement and mode status
- `car_sensor_data` — Car-specific sensor readings
- `smart_light_status` — Smart lighting state
- `control_command` — Command history
- `simulated_sensor_data` — Simulated sensor readings

## Hi3861 Source Structure
```
1/src/vendor/hqyj/fs_hi3861/
├── common/bsp/src/           # Hardware drivers
│   ├── hal_bsp_sht20.c       # Temperature/humidity
│   ├── hal_bsp_ap3216c.c     # Ambient light/proximity
│   ├── hal_bsp_ssd1306.c     # OLED display
│   ├── hal_bsp_pcf8574.c     # IO expander
│   └── hal_bsp_aw2013.c      # RGB LED
├── demo/Ext_VoiceCar_Test/
│   ├── voicecar_demo.c       # Entry point (creates FreeRTOS tasks)
│   ├── task/
│   │   ├── udp_recv_task.c   # UDP receiver (port 7788)
│   │   ├── udp_send_task.c  # UDP sender (50ms)
│   │   ├── uart_recv_task.c # STM32 UART2 communication
│   │   ├── oled_show_task.c # Display (100ms)
│   │   ├── auto_avoid_task.c # AGV obstacle avoidance (5ms)
│   │   └── smart_light_task.c # Smart lighting (100ms)
│   └── agriculture/
│       └── agriculture_sensor_task.c  # SGP30 CO2/TVOC collection
└── function/sys_config.h     # Global struct system_value_t
```

## FreeRTOS Tasks on Hi3861

| Task | Priority | Interval | Purpose |
|------|----------|----------|---------|
| UDP Recv | High | Event-driven | Receive commands from backend |
| UDP Send | Medium | 50ms | Send sensor/status to backend |
| UART Recv | High | Event-driven | Receive data from STM32 |
| OLED Show | Low | 100ms | Update display |
| Auto Avoid | Medium | 5ms | Obstacle avoidance algorithm |
| Smart Light | Low | 100ms | Ambient light adjustment |

Synchronization via global `system_value_t systemValue` struct in `sys_config.h`.

## Peripheral I2C Addresses
| Device | Address | Function |
|--------|---------|----------|
| PCF8574 | 0x43 | IO expander (fan/buzzer/LED/PIR/gas) |
| SHT20 | 0x80 | Temperature/humidity sensor |
| SGP30 | 0x80 | CO2/TVOC sensor |
| AW2013 | 0x8A | RGB LED driver |
| AP3216C | 0x3C | Ambient light/proximity sensor |
| SSD1306 | 0x78 | OLED display |

All I2C: GPIO_9 (SCL) + GPIO_10 (SDA) at 100kHz.

## PCF8574 I/O Definition
| Pin | Function |
|-----|----------|
| P0 | Fan control |
| P1 | Buzzer |
| P2 | LED indicator |
| P4 | Flame sensor |
| P5 | Gas sensor |
| P6 | Goods count pulse |
| P7 | PIR human detection |

## UART Pin Mapping
| UART | RX | TX | Purpose |
|------|-----|-----|---------|
| UART1 | GPIO_5 | GPIO_6 | Voice module |
| UART2 | GPIO_12 | GPIO_11 | STM32 motor board |

## Binary Protocol (STM32 Motor ↔ STM32 Sensor)
**Sync Packet** (Motor → Sensor): `0xBB` + `L_spd(2B)` + `R_spd(2B)` + `Status(1B)` + `Mode(1B)` + `Sum(1B)`

**Sensor Packets** (Sensor → Motor):
- Obstacle: `0xFF` + `Dist_H(1B)` + `Dist_L(1B)` + `Sum(1B)`
- Line/Button: `0xAA` + `LineOut(1B)` + `ModeByte(1B)` + `Sum(1B)`

**ModeByte encoding:** `0x00`-Remote, `0xD0`-Avoid, `0xF0`-Line follow, `0xE0`-Path

## Mini Program Pages
Located in `微信小程序端/smart_car_udp/`. Uses Vant Weapp UI library.

```bash
cd 微信小程序端/smart_car_udp/miniprogram
npm install
```

Key pages:
- `pages/factory_dashboard/` — Digital visualization dashboard
- `pages/alert_center/` — Multi-level alert center (gas/fire/temp alerts)
- `pages/equipment_control/` — Equipment control (fan, buzzer, LED)
- `pages/environment/` — Environmental monitoring
- `pages/smart_light/` — Smart lighting control
- `pages/control/` — Car movement control
- `pages/backend_connect/` — Backend connection

### Vant Weapp Icon Usage
`van-icon` requires explicit `color` attribute — does NOT inherit from parent CSS.
- Icons in colored circles/sensors: `color="#fff"`
- Section titles: semantic colors (`#1989fa`, `#7232dd`, `#ee0a24`)
- Valid names: `fire-o`, `water-o`, `lightbulb-o`, `sun-o`, `flower-o`, `setting-o`, `chart-trending-o`, `bell`, `edit`, `flash`, `play-circle-o`, `stop-circle-o`, `replay`

## Key Performance Parameters
- Joystick reports throttled to ≥50ms apart
- Minimum startup PWM: 150 (15%)
- 90-degree turn pulses: 920
- Speed gears: Low=500mm/s, Mid=800mm/s, High=1100mm/s
- UART timeout: 50ms auto-reset
- UDP data send interval: 50ms
- Database save interval: 1 second
- Mode switching: 500ms lockout

## Git Workflow (Mandatory)

> This sub-project follows the workspace-wide **GitHub Flow** (see root `AGENTS.md` §8). Full rules below.

### Iron Rule

- `main` **must always be runnable**. **Never commit any code change directly to `main`** — backend, mini-program, Hi3861 firmware, and STM32 projects all require a branch.
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

# 4. Self-check: run backend locally / verify mini-program in DevTools simulator; review diff
git diff main

# 5. Merge back to main (no-ff keeps branch history)
git checkout main && git merge --no-ff <branch>

# 6. Delete the branch
git branch -d <branch>
```

### Branch Naming

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **Scopes:** `backend`, `miniapp`, `hi3861`, `stm32`, `dashboard`, `agent`, `vision`, `docs`, `config`
- Examples: `feat/backend-add-imu-endpoint`, `fix/miniapp-reconnect`, `feat/dashboard-sse-live`

### Commit Format
```
<type>(<scope>): <subject>
```

### Sync Obligation

If a change affects anything described in this file or `AGENTS.md` — architecture, 5-layer protocol, ports, FreeRTOS tasks, I2C addresses, thresholds, or the branch model — **update the corresponding guidance file in the same branch**. Docs/code drift is technical debt; do not leave it.

### Workspace Hygiene

- `git status` should be clean before cutting a new branch. `git stash` or commit uncommitted changes first — **never mix unrelated changes into a task branch**.