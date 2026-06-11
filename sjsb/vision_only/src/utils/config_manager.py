import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import threading

logger = logging.getLogger("ConfigManager")


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    # 项目根目录与配置文件路径
    PROJECT_ROOT = Path(os.environ.get("SJSB_ROOT", Path(__file__).resolve().parents[3])).expanduser()
    CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    # 默认配置
    DEFAULT_CONFIG = {
        "RUNTIME": {
            "PROJECT_ROOT": "",                 # 为空时自动推导项目根目录
            "HEADLESS": "auto",                 # auto/true/false，Linux无显示环境时自动关闭窗口
            "DEVICE": "auto"                    # auto/cpu/cuda，模型推理设备
        },
        "PATHS": {
            "OBSTACLE_YOLO": "yolo11s.pt",
            "DIGIT_PANEL_YOLO": "szsb/checkpoints_v3/digit_panel_yolov8s.pt",
            "CRNN": "szsb/checkpoints_v2/best_crnn.pth",
            "CAPTURE_DIR": "captured_images"
        },
        "ESP32": {
            "IP": "192.168.137.213",
            "CAPTURE_PATH": "/capture",
            "FRAME_WIDTH": 320,
            "FRAME_HEIGHT": 240,
            "FPS": 1,
            "JPEG_QUALITY": 12
        },
        "DETECTION": {
            "OBSTACLE_CONF": 0.05,
            "COUNTER_CONF": 0.3
        },
        "VISION": {
            "ENABLED": True,                    # 是否启用视觉功能
            "API_KEY": "你的API_KEY",                       # 视觉API密钥
            "API_URL": "https://open.bigmodel.cn/api/paas/v4/chat/completions", # API基础URL
            "MODEL": "glm-4v-flash",             # 使用的模型名称
            "CAMERA_INDEX": 0,                   # 摄像头索引
            "KEYWORDS": [                        # 触发视觉识别的关键词列表
                "拍照", "识别场景", "识别物体",
                "导航", "识别", "识别画面",
                "看看", "帮我看看", "帮我分析"
            ],
            "CAMERA_KEYWORDS": [                 # 控制摄像头的关键词
                {"action": "open", "keywords": ["打开摄像头", "开摄像头", "开启摄像头"]},
                {"action": "close", "keywords": ["关闭摄像头", "关摄像头", "停止摄像头"]}
            ],
            "DEFAULT_PROMPT": "图中描绘的是什么景象,请详细描述，因为用户可能是盲人" # 默认提示语
        }
    }

    def __new__(cls):
        """确保单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # 加载配置
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件，如果不存在则创建"""
        try:
            if self.CONFIG_FILE.exists():
                config = json.loads(self.CONFIG_FILE.read_text(encoding='utf-8'))
                return self._merge_configs(self.DEFAULT_CONFIG, config)
            else:
                # 创建默认配置
                self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                self._save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"加载配置出错: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _save_config(self, config: dict) -> bool:
        """保存配置到文件"""
        try:
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.CONFIG_FILE.write_text(
                json.dumps(config, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            return True
        except Exception as e:
            logger.error(f"保存配置出错: {e}")
            return False

    @staticmethod
    def _merge_configs(default: dict, custom: dict) -> dict:
        """递归合并配置字典"""
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def get_config(self, path: str, default: Any = None) -> Any:
        """
        通过路径获取配置值
        path: 点分隔的配置路径，如 "VISION.API_KEY"
        """
        try:
            value = self._config
            for key in path.split('.'):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_project_root(self) -> Path:
        """获取项目根目录，优先使用配置和环境变量"""
        configured = self.get_config("RUNTIME.PROJECT_ROOT", "")
        if configured:
            return Path(configured).expanduser().resolve()
        return self.PROJECT_ROOT.resolve()

    def resolve_path(self, path_value: Union[str, Path, None], default: Optional[Union[str, Path]] = None) -> Path:
        """将配置路径解析为绝对路径

        绝对路径原样返回；相对路径按项目根目录拼接；支持 ~ 展开。
        """
        value = path_value if path_value not in (None, "") else default
        if value in (None, ""):
            return self.get_project_root()
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return (self.get_project_root() / path).resolve()

    def is_headless(self) -> bool:
        """判断当前是否应启用无窗口模式"""
        mode = str(self.get_config("RUNTIME.HEADLESS", "auto")).strip().lower()
        if mode in ("1", "true", "yes", "on"):
            return True
        if mode in ("0", "false", "no", "off"):
            return False
        return os.name != "nt" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def get_device(self) -> str:
        """获取推理设备配置"""
        return str(self.get_config("RUNTIME.DEVICE", "auto")).strip().lower()

    def update_config(self, path: str, value: Any) -> bool:
        """
        更新特定配置项
        path: 点分隔的配置路径，如 "VISION.API_KEY"
        """
        try:
            current = self._config
            *parts, last = path.split('.')
            for part in parts:
                current = current.setdefault(part, {})
            current[last] = value
            return self._save_config(self._config)
        except Exception as e:
            logger.error(f"更新配置出错 {path}: {e}")
            return False

    @classmethod
    def get_instance(cls):
        """获取配置管理器实例（线程安全）"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance