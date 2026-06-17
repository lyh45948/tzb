# Hi3861 固件改动报告

> 路径：`fwwb/1/`
> 基线 commit：`20b8ef1b` (Merge branch 'feature/integrate-sjsb-vision', 2026-06-12)
> 改动主题：移除固件侧 `smart_light_task` 智能光照模块，把照明/风扇/RGB 决策权全部上移到后端 `LinkageController`；固件只做 UDP 命令执行 + 传感器上报

## 1. 改动概览

| 文件 | 操作 | +/- | 说明 |
|---|---|---|---|
| `src/vendor/hqyj/fs_hi3861/demo/Ext_VoiceCar_Test/BUILD.gn` | 修改 | -1 | 编译列表移除 `smart_light_task.c` |
| `src/vendor/hqyj/fs_hi3861/demo/Ext_VoiceCar_Test/voicecar_demo.c` | 修改 | -12 | 移除 include / task_id 声明 / `smart_light_init()` / 创建任务整段 |
| `src/vendor/hqyj/fs_hi3861/demo/Ext_VoiceCar_Test/task/udp_recv_task.c` | 修改 | -39 +1 | rgb 字段直接调 `AW2013_Control_RGB`；删除 `smartLight` 字段整段 |
| `src/vendor/hqyj/fs_hi3861/demo/Ext_VoiceCar_Test/task/udp_send_task.c` | 修改 | -10 | 删除 include 与 `smartLight` 子对象上报 |
| `src/vendor/hqyj/fs_hi3861/demo/Ext_VoiceCar_Test/function/sys_config.h` | 修改 | -4 | 删除 `system_value_t.smart_light_mode` / `smart_light_brightness` 字段 |
| `src/vendor/hqyj/fs_hi3861/demo/Ext_VoiceCar_Test/task/smart_light_task.c` | 删除 | -244 | 整文件删除 |
| `src/vendor/hqyj/fs_hi3861/demo/Ext_VoiceCar_Test/task/smart_light_task.h` | 删除 | -90 | 整文件删除 |

合计：1 处新增、399 行删除。**没有新增固件源文件**——固件层只做"瘦身"，不引入新逻辑。

## 2. 行为变化

### 2.1 移除的固件功能
- ~~`smart_light_task` 50ms 主循环~~：根据 lux + 时段算法自动调亮度并写 AW2013
- ~~`smart_light_set_mode` / `smart_light_set_brightness` / `smart_light_set_rgb`~~：UDP 路由到的 RGB 操作函数
- ~~UDP 上行 `env.smartLight`~~：固件不再上报智能光照状态对象

### 2.2 新行为（固件接收 UDP 时）
- `{"rgb":{"r":x,"g":y,"b":z}}` 字段：直接调 `AW2013_Control_RGB(r, g, b)`，不再经过亮度系数和模式判断
- `{"smartLight":{...}}` 字段：**完全忽略**（不报错，仅不再处理）
- `{"fan":0/1}` / `{"led":0/1}` / `{"buzzer":0/1}`：保持不变（手动兜底通路）

### 2.3 决策权迁移
原本由固件 `smart_light_task` 自己决定 RGB 颜色和亮度，现在统一由后端 `LinkageController` 周期性下发以下三类命令：
- 危气告警 → `{"rgb":{"r":...,"g":...,"b":...}}`（warning=黄、danger=红、critical=红 1Hz 闪、normal=灭）
- PIR 检测到人 → `{"led":0/1}`
- 温湿度超阈值 → `{"fan":0/1}`

固件**不需要**任何配套改动来支持这三条规则——所有阈值、去抖、回滞、闪烁相位都在后端完成，固件只是被动执行 UDP 命令。

## 3. 编译验证

```bash
cd fwwb/1/src
rm -rf out/                         # 必须清掉，否则会链接到旧 smart_light_task.o
hb set                              # 选 hispark_pegasus / hi3861
hb build
```

预期产物：`out/hispark_pegasus/wifiiot_hispark_pegasus/Hi3861_wifiiot_app_allinone.bin`

**注意旧 build 残留**：`out/` 下还有以下旧文件需要清理（直接 `rm -rf out/` 或 `hb clean`）：
- `obj/.../task/libvoicecar_demo.smart_light_task.o`
- `Hi3861_wifiiot_app.map` 中对 `smart_light_task.o` 的引用

不清理会出现 `multiple definition` / 链接到已删除符号的报错。

## 4. 烧录

按 `fwwb/CLAUDE.md` 的 HiBurn 流程：
- Baud：2000000
- Loader：`Hi3861_loader_signed.bin`
- 烧录文件：`Hi3861_wifiiot_app_allinone.bin`

## 5. 烧录后串口校验

正常输出**应包含**：
- `Create udp_send_task_id is OK!`
- `Create udp_recv_task_id is OK!`
- `Create auto_avoid_task_id is OK!`
- `Create agriculture_sensor_task_id is OK!`
- `Create imu_task_id is OK!`

**不应再出现**：
- ~~`Create smart_light_task_id is OK!`~~
- ~~`[SmartLight] Initialized, auto_mode=...`~~
- ~~`[UDP_SmartLight]: Mode=AUTO/MANUAL`~~

收到 UDP RGB 命令时打印保留：
- `[UDP_RGB]: R=255, G=0, B=0`

## 6. 与后端的依赖关系

固件本次烧录后**必须**配合以下后端改动一起部署，否则 RGB 灯将一直熄灭（因为没人发 RGB 命令了）：

后端新增/修改文件：
- 新建 `fwwb/backend/app/services/linkage_service.py`（LinkageController）
- 新建 `fwwb/backend/app/utils/alert_rules.py`
- 修改 `fwwb/backend/app/services/dashboard_service.py`、`udp_miniapp_service.py`、`registry.py`、`main.py`、`config.py`、`.env.example`
- 删除 `fwwb/backend/app/services/smart_light_service.py`

后端阈值（在 `.env` 里覆盖）：
- `FAN_TEMP_ON=32` / `FAN_TEMP_OFF=30` / `FAN_HUMI_ON=80` / `FAN_HUMI_OFF=75`
- `IR_PS_THRESHOLD=200` / `IR_IR_THRESHOLD=100`（**需现场标定**）
- `IR_DEBOUNCE_ON=2` / `IR_DEBOUNCE_OFF=5`（tick=1s）
- `RGB_BLINK_HZ=1.0` / `MANUAL_OVERRIDE_TTL=30`

## 7. 详细 diff

完整的统一 diff 见同目录 `firmware-changes.diff`（基于 commit `20b8ef1b` 生成）。
应用方法：

```bash
cd fwwb/1
git checkout 20b8ef1b -- .          # 回到基线（如果当前不在）
git apply firmware-changes.diff     # 应用本次改动
# 或者直接使用 patch
patch -p1 < firmware-changes.diff
```

## 8. 端到端冒烟（烧录后）

1. **PIR → LED**：手遮挡 AP3216C 持续 2 秒 → LED 亮；移开 5 秒 → LED 灭
2. **温湿度 → 风扇**：哈气让 humi ≥ 80% 或加热到 temp ≥ 32°C → 风扇开；恢复 → 风扇关；在 31°C/78% 区间应保持稳定不抖动
3. **危气 → RGB**：
   - co2 ≥ 800 或 gasMic ≥ 300 → RGB 黄色常亮
   - co2 ≥ 1000 或 gasMic ≥ 500 → RGB 红色常亮
   - 火焰传感器触发（flameStatus=1）→ RGB 红色 1Hz 闪烁
   - 全部恢复 → RGB 熄灭
4. **手动覆盖**：自动开风扇后，用小程序按钮关风扇 → 30 秒内不被自动重新打开；30 秒后温度仍高则再次自动开
