# 红外巡线状态机流程图 (Infrared Line Tracking State Machine)

Due to current limitations with the image generation service, this high-density flowchart is provided in **Mermaid** format. This format is standard for academic papers and can be rendered into high-resolution PNG/SVG/PDF using tools like [Mermaid Live Editor](https://mermaid.live/) or VS Code.

## State Machine Flowchart

```mermaid
flowchart TD
    %% Nodes
    Start([开始 (Start)]) --> Init[系统初始化 & PWM开启]
    Init --> Loop{主循环 (Loop)}
    
    Loop --> ReadSensor[读取红外传感器 gLineOut]
    
    %% Main Line Tracking Logic
    subgraph Tracking [巡线控制逻辑 (PID Control)]
        direction TB
        ReadSensor --> SwitchSensor{传感器状态?}
        
        SwitchSensor -- "0xE7 (Center)" --> GoStraight[高速直行 (BaseSpeed)]
        SwitchSensor -- "0xFE/0xFD (Left Dev)" --> TurnRight[右转修正 (L:0.4, R:1.2)]
        SwitchSensor -- "0x7F/0xBF (Right Dev)" --> TurnLeft[左转修正 (L:1.2, R:0.4)]
        SwitchSensor -- "0xFF (Lost)" --> Search[低速搜索 (Speed * 0.6)]
        
        GoStraight --> CalcPID[增量 PID 计算]
        TurnRight --> CalcPID
        TurnLeft --> CalcPID
        Search --> CalcPID
    end

    %% Avoidance Logic
    subgraph Avoidance [避障状态机 (Avoidance State Machine)]
        direction TB
        SafeCheck{前方距离 <= 150mm?}
        
        CalcPID -- MotorOutput --> SafeCheck
        
        SafeCheck -- "Yes (Unsafe)" --> CheckState{当前避障状态?}
        SafeCheck -- "No (Safe)" --> Loop
        
        CheckState -- "IDLE" --> SetBack[进入 BACK 状态]
        SetBack --> BackState[后退避障 (1s)]
        BackState --> BackTimer{计时结束?}
        BackTimer -- Yes --> SetTurn[进入 TURN 状态]
        BackTimer -- No --> Loop
        
        CheckState -- "BACK" --> BackState
        
        CheckState -- "TURN" --> TurnState[左转寻路 (1s)]
        TurnState --> CheckPath{前方畅通 (>150mm)?}
        CheckPath -- Yes --> Restore[恢复 IDLE (巡线)]
        CheckPath -- No --> TurnTimer{超时 (>2s)?}
        TurnTimer -- Yes --> Restore
        TurnTimer -- No --> Loop
        
        Restore --> Loop
    end
    
    %% Styling
    classDef process fill:#fff,stroke:#333,stroke-width:1px;
    classDef decision fill:#f9f9f9,stroke:#333,stroke-width:1px,shape:diamond;
    classDef start fill:#000,stroke:#000,color:#fff;
    
    class Start,Init,ReadSensor,GoStraight,TurnRight,TurnLeft,Search,CalcPID,SetBack,BackState,SetTurn,TurnState,Restore process;
    class Loop,SwitchSensor,SafeCheck,CheckState,BackTimer,CheckPath,TurnTimer decision;
    class Start start;
```
