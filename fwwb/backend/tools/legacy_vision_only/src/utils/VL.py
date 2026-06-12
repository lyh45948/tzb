import os
import base64
import json
import requests
import threading
import logging
import cv2
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import deque, Counter

try:
    from .config_manager import ConfigManager
except ImportError:
    from config_manager import ConfigManager

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

logger = logging.getLogger(__name__)

# ============ 数码管 CRNN 端到端识别 ============
class CRNN(nn.Module):
    """CRNN + CTC 端到端数字序列识别模型"""
    def __init__(self, num_classes: int = 11, hidden_size: int = 256):
        super(CRNN, self).__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 64, 3, 1, 1), nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, 1, 1), nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, 3, 1, 1), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, 1, 1), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),
            nn.Conv2d(256, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),
            nn.Conv2d(512, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),
        )
        self.rnn = nn.LSTM(512, hidden_size, num_layers=2, bidirectional=True, batch_first=False)
        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x):
        x = self.cnn(x)              # (B, 512, 1, T)
        x = x.squeeze(2)             # (B, 512, T)
        x = x.permute(2, 0, 1)       # (T, B, 512)
        x, _ = self.rnn(x)           # (T, B, 512)
        x = self.fc(x)               # (T, B, num_classes)
        return x


def _preprocess_for_crnn(roi_bgr: np.ndarray, img_size: Tuple[int, int] = (32, 128)) -> np.ndarray:
    """将 BGR ROI 预处理为 CRNN 输入格式（灰度、resize、左对齐 pad、归一化）"""
    target_h, target_w = img_size
    if len(roi_bgr.shape) == 3:
        roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    else:
        roi = roi_bgr
    rh = target_h / roi.shape[0]
    new_w = int(roi.shape[1] * rh)
    if new_w > target_w:
        new_w = target_w
    roi = cv2.resize(roi, (new_w, target_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    canvas[:, :new_w] = roi.astype(np.float32)
    canvas = (canvas / 255.0 - 0.5) / 0.5
    return canvas


def _ctc_decode(preds: np.ndarray, blank: int = 10) -> List[str]:
    """贪婪 CTC 解码：去 blank、去连续重复"""
    T, B = preds.shape
    results = []
    for b in range(B):
        seq = preds[:, b].tolist()
        out = []
        prev = -1
        for s in seq:
            if s != blank and s != prev:
                out.append(str(s))
            prev = s
        results.append(''.join(out))
    return results


class CounterTemporalSmoother:
    """计数器读数时序平滑器 —— 连续性约束 + 噪声抑制
    
    核心策略：
    1. 正常递增（差值 <= max_jump）直接通过
    2. 跳跃过大时，需连续 hold_frames 帧指向同一新值才接受
    3. 单帧噪声（如 884, 8884）不会连续出现，自然被过滤
    """
    def __init__(self, max_jump: int = 15, hold_frames: int = 3):
        self.confirmed_value = None
        self.max_jump = max_jump          # 允许的最大单步跳跃（工业计数器每秒可能增多个）
        self.hold_frames = hold_frames    # 跳跃过大时需连续确认帧数
        self.pending_value = None         # 待确认的新值
        self.pending_count = 0            # 连续出现次数
    
    def _parse_value(self, s: str) -> Optional[int]:
        """将识别结果字符串转为整数，空/无效返回 None"""
        if not s or s in ('未检测到面板', '未检测到数字', '模型未加载', '识别错误'):
            return None
        try:
            # 过滤掉明显异常的长字符串（如 "8884" 可能是多帧误拼接）
            val = int(s)
            if val < 0 or val > 999999:
                return None
            return val
        except ValueError:
            return None
    
    def update(self, raw_str: str) -> Tuple[str, str]:
        """输入当前帧原始识别结果，返回 (平滑后结果, 状态说明)"""
        raw_val = self._parse_value(raw_str)
        if raw_val is None:
            return str(self.confirmed_value) if self.confirmed_value is not None else raw_str, "frame_invalid"
        
        # 首次识别
        if self.confirmed_value is None:
            self.confirmed_value = raw_val
            self.pending_value = None
            self.pending_count = 0
            return str(raw_val), "init"
        
        diff = abs(raw_val - self.confirmed_value)
        if diff <= self.max_jump:
            # 正常范围内，直接更新，清空 pending
            self.confirmed_value = raw_val
            self.pending_value = None
            self.pending_count = 0
            return str(raw_val), "confirmed"
        
        # 跳跃过大：检查是否是持续的新值（非噪声）
        if self.pending_value == raw_val:
            self.pending_count += 1
            if self.pending_count >= self.hold_frames:
                # 连续多帧一致，接受新值（如人工清零、大幅跳变）
                self.confirmed_value = raw_val
                self.pending_value = None
                self.pending_count = 0
                return str(raw_val), "jump_accepted"
            return str(self.confirmed_value), f"hold({raw_val},{self.pending_count})"
        else:
            # 新的 pending 值
            self.pending_value = raw_val
            self.pending_count = 1
            return str(self.confirmed_value), f"hold({raw_val},1)"
    
    def reset(self):
        """重置状态（切换场景、重新连接摄像头、启停识别时调用）"""
        self.confirmed_value = None
        self.pending_value = None
        self.pending_count = 0


class ObstacleDetector:
    """基于 YOLOv8 的障碍物检测器"""

    # 常见障碍物类别及其典型物理尺寸（单位：米）
    # [width, height, depth] 或 [width, height] for 2D
    OBJECT_SIZES = {
        # 人形障碍物
        'person': [0.5, 1.7, 0.3],      # 成年人
        'child': [0.4, 1.2, 0.25],
        'baby': [0.3, 0.7, 0.2],

        # 动物
        'dog': [0.5, 0.6, 0.3],
        'cat': [0.4, 0.3, 0.25],
        'bird': [0.15, 0.15, 0.1],

        # 家具
        'chair': [0.5, 0.9, 0.5],
        'table': [1.2, 0.75, 0.6],
        'bench': [1.5, 0.45, 0.4],
        'sofa': [2.0, 0.85, 0.9],
        'bed': [2.0, 0.5, 1.5],

        # 车辆
        'car': [1.8, 1.5, 4.5],
        'truck': [2.5, 2.5, 8.0],
        'bus': [3.0, 3.0, 12.0],
        'bicycle': [0.6, 1.1, 1.8],
        'motorcycle': [0.8, 1.2, 2.0],
        'stroller': [0.6, 1.0, 0.8],

        # 日常物品（地面障碍物）
        'cup': [0.08, 0.12, 0.08],
        'bottle': [0.08, 0.25, 0.08],
        'bag': [0.4, 0.3, 0.2],
        ' suitcase': [0.5, 0.6, 0.3],

        # 建筑元素
        'pole': [0.2, 2.0, 0.2],
        'tree': [2.0, 3.0, 2.0],  # 假设的树冠直径和高度
        'stairs': [1.2, 0.2, 0.3],  # 每级台阶

        # 其他常见障碍物
        'box': [0.5, 0.4, 0.5],
        'bag': [0.4, 0.5, 0.2],
        'umbrella': [0.8, 2.0, 0.8],
        'ball': [0.22, 0.22, 0.22],  # 篮球直径
        'vase': [0.15, 0.3, 0.15],   # 花瓶
        'book': [0.2, 0.3, 0.02],    # 书本
        'remote': [0.05, 0.15, 0.02], # 遥控器
        'keyboard': [0.15, 0.05, 0.02], # 键盘
        'bowl': [0.15, 0.08, 0.15],  # 碗
        'spoon': [0.02, 0.2, 0.005], # 勺子
        'clock': [0.2, 0.2, 0.02],   # 时钟
        'scissors': [0.1, 0.03, 0.005], # 剪刀
        'teddy bear': [0.3, 0.4, 0.2], # 毛绒玩具
        'handbag': [0.4, 0.3, 0.15], # 手提包
        'backpack': [0.4, 0.5, 0.2], # 背包
        'refrigerator': [0.7, 1.8, 0.8], # 冰箱
        'potted plant': [0.3, 0.5, 0.3], # 盆栽
        'bottle': [0.08, 0.25, 0.08], # 瓶子
        'cell phone': [0.07, 0.15, 0.005], # 手机
        'toothbrush': [0.02, 0.18, 0.005], # 牙刷
        'cup': [0.08, 0.12, 0.08],   # 杯子
        'laptop': [0.35, 0.25, 0.03], # 笔记本电脑
        'chair': [0.5, 0.9, 0.5],    # 椅子
        'dining table': [1.2, 0.75, 0.6], # 餐桌
        'couch': [1.8, 0.8, 0.9],    # 沙发
        'tv': [0.8, 0.5, 0.1],       # 电视
        'mouse': [0.06, 0.03, 0.02], # 鼠标
        'keyboard': [0.15, 0.05, 0.02], # 键盘
    }

    # 摄像头内参（默认，待标定）
    DEFAULT_FOCAL_LENGTH = 600  # ESP32广角摄像头典型焦距
    DEFAULT_CAMERA_HEIGHT = 1.2  # 摄像头安装高度（米）

    def __init__(self, model_path: str = None, focal_length: float = None,
                 device: str = None, conf_thresh: float = 0.05):
        """初始化障碍物检测器

        Args:
            model_path: YOLOv11 模型路径，默认使用配置中的项目内模型
            focal_length: 摄像头焦距（像素），可通过标定获得
            device: 推理设备，auto/cpu/cuda
            conf_thresh: 障碍物检测置信度阈值
        """
        self.focal_length = focal_length or self.DEFAULT_FOCAL_LENGTH
        self.model = None
        self.model_path = model_path
        self.device = device or 'auto'
        self.conf_thresh = conf_thresh
        self._initialized = False

    def init(self):
        """初始化 YOLOv11 模型"""
        if self._initialized:
            return True

        try:
            from ultralytics import YOLO
            import torch
            logger.info("正在加载 YOLOv11 模型...")

            # 确定设备（优先使用GPU）
            if self.device == 'cuda' and not torch.cuda.is_available():
                logger.warning("配置要求使用 cuda，但当前 CUDA 不可用，已回退到 cpu")
                device = 'cpu'
            elif self.device in ('cpu', 'cuda'):
                device = self.device
            else:
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"使用设备: {device}")

            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"加载障碍物 YOLO 模型: {self.model_path}")
                self.model = YOLO(self.model_path)
            else:
                logger.error(f"未找到障碍物 YOLO 模型: {self.model_path}")
                return False

            # 将模型移动到指定设备
            self.model.to(device)

            self._initialized = True
            logger.info("YOLOv11 模型加载成功")
            return True

        except ImportError:
            logger.error("请安装 ultralytics: pip install ultralytics")
            return False
        except Exception as e:
            logger.error(f"YOLOv8 模型加载失败: {e}")
            return False

    def calibrate(self, known_distance: float, known_width: float, measured_width: float):
        """通过已知距离的参考物体标定焦距

        Args:
            known_distance: 参考物体到摄像头的实际距离（米）
            known_width: 参考物体的实际宽度（米）
            measured_width: 参考物体在图像中测量的宽度（像素）
        """
        if measured_width > 0:
            self.focal_length = (measured_width * known_distance) / known_width
            logger.info(f"摄像头焦距已标定为: {self.focal_length:.2f} 像素")

    def _estimate_distance(self, class_name: str, bbox_width: int, bbox_height: int,
                          frame_width: int, frame_height: int, bbox_y1: int) -> Optional[float]:
        """根据检测框尺寸估算障碍物距离

        使用针孔相机模型：
        distance = (real_size * focal_length) / apparent_size

        Args:
            class_name: 物体类别名称
            bbox_width: 检测框宽度（像素）
            bbox_height: 检测框高度（像素）
            frame_width: 图像宽度
            frame_height: 图像高度
            bbox_y1: 检测框顶部y坐标（用于位置修正）

        Returns:
            估算距离（米），如果无法估算返回 None
        """
        if class_name not in self.OBJECT_SIZES:
            # 尝试用中文映射
            chinese_map = {
                '人': 'person', '狗': 'dog', '猫': 'cat',
                '车': 'car', '桌子': 'table', '椅子': 'chair',
                '杯子': 'cup', '瓶子': 'bottle', '包': 'bag',
                '树': 'tree', '盒': 'box'
            }
            mapped = chinese_map.get(class_name)
            if mapped and mapped in self.OBJECT_SIZES:
                class_name = mapped
            else:
                return None

        # 获取该类别的典型尺寸
        sizes = self.OBJECT_SIZES[class_name]
        real_width = sizes[0]

        # 计算归一化宽度（相对于图像宽度）
        normalized_width = bbox_width / frame_width

        # 估算距离
        if normalized_width > 0.001:  # 避免除零
            # 基础距离估算：distance = real_width * focal_length / bbox_width
            distance = (real_width * self.focal_length) / bbox_width

            # 加入高度信息辅助估算（取平均）
            if len(sizes) >= 2:
                real_height = sizes[1]
                distance_h = (real_height * self.focal_length) / bbox_height
                # 取调和平均，更信任较小的距离估计（避免过高估计）
                distance = (distance + distance_h) / 2

            # 根据物体在画面中的垂直位置进行修正
            # 画面底部的物体通常更近（地面上的物体）
            # 画面顶部的物体可能更远或在背景中
            if bbox_y1 > 0:
                # 计算物体中心的垂直位置比例（0=顶部, 1=底部）
                bbox_center_y = bbox_y1 + bbox_height / 2
                vertical_ratio = bbox_center_y / frame_height

                # 垂直位置线性修正：顶部1.2 -> 底部0.9，避免临界点跳变
                if vertical_ratio < 0.3:
                    distance *= 1.2
                elif vertical_ratio > 0.6:
                    distance *= 0.9
                else:
                    # 0.3 ~ 0.6 线性插值
                    distance *= (1.5 - vertical_ratio)

            # 限制在合理范围
            return max(0.3, min(distance, 50))  # 限制在 0.3-50 米

        return None

    def detect_obstacles(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """检测障碍物

        Args:
            frame: OpenCV 图像帧 (BGR格式)

        Returns:
            (obstacles_list, annotated_frame)
            obstacles_list: 检测到的障碍物列表，每个包含:
                {
                    'class': 类别名称,
                    'class_id': 类别ID,
                    'confidence': 置信度,
                    'bbox': [x1, y1, x2, y2],
                    'distance': 估算距离（米）
                }
            annotated_frame: 带标注的图像
        """
        if not self._initialized:
            if not self.init():
                return [], frame

        # YOLOv8 检测
        results = self.model(frame, verbose=False)[0]

        obstacles = []
        annotated_frame = frame.copy()

        # 常见的危险障碍物类别（需要重点提醒）
        dangerous_classes = {
            'person', 'child', 'baby', 'dog', 'car', 'truck', 'bus',
            'bicycle', 'motorcycle', 'stroller', 'baby'
        }

        for box in results.boxes:
            # 获取检测信息
            class_id = int(box.cls.cpu().numpy()[0])
            class_name = results.names[class_id]
            confidence = float(box.conf.cpu().numpy()[0])

            # 过滤低置信度
            if confidence < self.conf_thresh:
                continue

            # 获取边界框
            x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])
            bbox_width = x2 - x1
            bbox_height = y2 - y1

            # 估算距离
            distance = self._estimate_distance(
                class_name, bbox_width, bbox_height,
                frame.shape[1], frame.shape[0], y1
            )

            # 构建障碍物信息
            obstacle = {
                'class': class_name,
                'class_id': class_id,
                'confidence': confidence,
                'bbox': [x1, y1, x2, y2],
                'distance': distance,
                'dangerous': class_name in dangerous_classes
            }
            obstacles.append(obstacle)

            # 在图像上绘制标注
            label = f"{class_name} {confidence:.2f}"
            if distance:
                label += f" {distance:.1f}m"

            # 危险障碍物用红色标注
            color = (0, 0, 255) if obstacle['dangerous'] else (0, 255, 0)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return obstacles, annotated_frame

class ImageAnalyzer:
    """图像分析器 - 单例模式

    基于 YOLOv8 进行障碍物检测与距离估算
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """确保单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化图像分析器"""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._distance_smooth = {}  # 类别 -> EMA平滑后的距离
        self.counter_smoother = CounterTemporalSmoother(max_jump=15, hold_frames=3)
        self._panel_smooth = None    # EMA 平滑后的面板位置 (x, y, w, h)
        self._panel_alpha = 0.2      # 面板位置 EMA 系数（越小越平滑，0.2=80%历史+20%当前）
        # 固定 ROI 配置（v3：基于训练数据统计的机位标定值）
        # 覆盖 320x240 图像中数字显示窗的最大范围
        self._fixed_roi = None  # 弃用固定ROI，改用YOLO检测
        self.config = ConfigManager.get_instance()
        self.device = self._select_device()
        self.counter_crnn = None     # CRNN 端到端模型
        self._crnn_img_size = (32, 128)
        self.yolo_detector = None    # YOLOv8s 数字区域检测器

    def _select_device(self) -> torch.device:
        """根据配置选择推理设备"""
        device_config = self.config.get_device()
        if device_config == 'cuda' and not torch.cuda.is_available():
            logger.warning("配置要求使用 cuda，但当前 CUDA 不可用，已回退到 cpu")
            device_config = 'cpu'
        if device_config not in ('cpu', 'cuda'):
            device_config = 'cuda' if torch.cuda.is_available() else 'cpu'
        return torch.device(device_config)

    def init(self):
        """初始化图像分析器（YOLOv8 障碍物检测 + 计数器数字识别）"""
        self.config = ConfigManager.get_instance()
        self.device = self._select_device()
        obstacle_model = self.config.resolve_path(self.config.get_config("PATHS.OBSTACLE_YOLO", "yolo11s.pt"))
        obstacle_conf = float(self.config.get_config("DETECTION.OBSTACLE_CONF", 0.05))
        # 初始化障碍物检测器
        self.obstacle_detector = ObstacleDetector(
            model_path=str(obstacle_model),
            device=str(self.device),
            conf_thresh=obstacle_conf
        )
        # 初始化 CRNN 端到端计数器识别模型
        self.counter_crnn = None
        try:
            # 加载 YOLOv8s 数字区域检测器
            yolo_path = self.config.resolve_path(self.config.get_config("PATHS.DIGIT_PANEL_YOLO"))
            if yolo_path.exists():
                from ultralytics import YOLO
                self.yolo_detector = YOLO(str(yolo_path))
                self.yolo_detector.to(self.device)
                logger.info(f"YOLOv8s 数字区域检测器已加载: {yolo_path}")
            else:
                logger.warning(f"YOLO 检测器未找到: {yolo_path}，计数器识别将回退到 HSV 定位")
        except Exception as e:
            logger.warning(f"YOLO 检测器加载失败: {e}")

        try:
            # 使用 v2 CRNN（在精确YOLO框下训练，与YOLO检测器输出分布一致）
            crnn_path = self.config.resolve_path(self.config.get_config("PATHS.CRNN"))
            if crnn_path.exists():
                ckpt = torch.load(str(crnn_path), map_location=self.device, weights_only=False)
                saved_args = ckpt.get('args', {})
                hidden_size = saved_args.get('hidden_size', 256)
                self._crnn_img_size = (saved_args.get('img_h', 32), saved_args.get('img_w', 128))
                self.counter_crnn = CRNN(num_classes=11, hidden_size=hidden_size)
                self.counter_crnn.load_state_dict(ckpt['model_state_dict'])
                self.counter_crnn.to(self.device)
                self.counter_crnn.eval()
                logger.info(f"CRNN 端到端模型已加载: {crnn_path}, img_size={self._crnn_img_size}")
            else:
                logger.warning(f"CRNN 模型未找到: {crnn_path}")
        except Exception as e:
            logger.warning(f"CRNN 加载失败: {e}")
        # 兼容旧单例：若 counter_smoother 不存在则创建
        if not hasattr(self, 'counter_smoother') or self.counter_smoother is None:
            self.counter_smoother = CounterTemporalSmoother(max_jump=15, hold_frames=3)
            logger.info("计数器时序平滑器已初始化")
        logger.info("图像分析器初始化完成")

    @classmethod
    def get_instance(cls):
        """获取图像分析器实例（线程安全）"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _locate_counter_panel(self, img: np.ndarray):
        """定位红色数码管面板，返回聚焦到数字显示区域的 (x, y, w, h) 或 None

        使用 EMA 平滑面板位置，避免帧间抖动。v2 改进：
        1. 支持固定 ROI（self._fixed_roi）
        2. HSV 外接矩形向内收缩，去掉白色外壳和标签，聚焦纯数字区域
        """
        # 优先使用固定 ROI
        if self._fixed_roi is not None:
            return self._fixed_roi

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([15, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([155, 60, 60]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(mask1, mask2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return self._panel_smooth  # 当前帧找不到，使用上一次的平滑位置

        best = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(best)
        if area < 200:  # 降低阈值，兼容单数字小区域
            return self._panel_smooth

        raw_panel = cv2.boundingRect(best)

        # EMA 平滑
        if self._panel_smooth is not None:
            rx, ry, rw, rh = raw_panel
            sx, sy, sw, sh = self._panel_smooth
            px = int(self._panel_alpha * rx + (1 - self._panel_alpha) * sx)
            py = int(self._panel_alpha * ry + (1 - self._panel_alpha) * sy)
            pw = int(self._panel_alpha * rw + (1 - self._panel_alpha) * sw)
            ph = int(self._panel_alpha * rh + (1 - self._panel_alpha) * sh)
        else:
            px, py, pw, ph = raw_panel

        # 限制在图像范围内
        h, w = img.shape[:2]
        px = max(0, min(px, w - 1))
        py = max(0, min(py, h - 1))
        pw = min(pw, w - px)
        ph = min(ph, h - py)

        # ---- v2 关键改进：向内收缩，聚焦数字显示区域 ----
        # HSV 外接矩形包含了整个红色面板（含白色外壳、标签），
        # 而 CRNN 训练时只见过纯数字区域，需要裁掉上下边框和左右边框。
        # 根据训练图统计：上下各约 22% 是外壳/标签，左右各约 8% 是边框。
        shrink_top = 0.22
        shrink_bottom = 0.18
        shrink_left = 0.08
        shrink_right = 0.08
        cx = px + int(pw * shrink_left)
        cy = py + int(ph * shrink_top)
        cw = int(pw * (1 - shrink_left - shrink_right))
        ch = int(ph * (1 - shrink_top - shrink_bottom))
        # 二次限制
        cx = max(0, min(cx, w - 1))
        cy = max(0, min(cy, h - 1))
        cw = max(10, min(cw, w - cx))
        ch = max(10, min(ch, h - cy))
        panel = (cx, cy, cw, ch)

        self._panel_smooth = panel
        return panel

    def recognize_counter(self, frame: np.ndarray, conf_thresh: float = None,
                          use_temporal: bool = True) -> Tuple[str, np.ndarray]:
        """端到端识别 JDM11-6H 计数器数码管数字（YOLO + CRNN + CTC）

        流程: YOLO检测数字区域 -> 裁剪 -> CRNN 端到端推理 -> CTC 解码 -> 时序平滑(可选)

        Args:
            frame: OpenCV BGR 图像帧
            conf_thresh: YOLO检测置信度阈值
            use_temporal: 是否启用时序平滑（验证时建议关闭）

        Returns:
            (digit_string, annotated_frame)
        """
        if conf_thresh is None:
            conf_thresh = float(self.config.get_config("DETECTION.COUNTER_CONF", 0.3))
        if self.counter_crnn is None:
            logger.warning("CRNN 模型未加载")
            return "模型未加载", frame

        annotated = frame.copy()
        try:
            # ---- 1. YOLO 检测数字区域 ----
            px, py, pw, ph = 0, 0, 0, 0
            if self.yolo_detector is not None:
                results = self.yolo_detector(frame, verbose=False, device=self.device)
                best_box = None
                best_conf = 0
                for r in results:
                    if r.boxes is None:
                        continue
                    for box in r.boxes:
                        conf = float(box.conf[0])
                        if conf > best_conf and conf >= conf_thresh:
                            best_conf = conf
                            best_box = box.xyxy[0].cpu().numpy().astype(int)
                if best_box is not None:
                    x1, y1, x2, y2 = best_box
                    px, py, pw, ph = x1, y1, x2 - x1, y2 - y1
                else:
                    logger.warning("YOLO 未检测到数字区域，回退到 HSV")
                    panel = self._locate_counter_panel(frame)
                    if panel is None:
                        return "未检测到面板", annotated
                    px, py, pw, ph = panel
            else:
                logger.warning("YOLO 检测器未加载，回退到 HSV")
                panel = self._locate_counter_panel(frame)
                if panel is None:
                    return "未检测到面板", annotated
                px, py, pw, ph = panel

            roi = frame[py:py+ph, px:px+pw]
            if roi.size == 0:
                return "未检测到面板", annotated

            # CRNN 端到端推理（直接用 YOLO 框裁剪，与 v2 训练分布一致）
            img_array = _preprocess_for_crnn(roi, img_size=self._crnn_img_size)
            img_tensor = torch.from_numpy(img_array).unsqueeze(0).unsqueeze(0).to(self.device)

            with torch.no_grad():
                outputs = self.counter_crnn(img_tensor)
                preds = outputs.argmax(dim=2).cpu().numpy()
                pred_texts = _ctc_decode(preds)
                raw_digit_str = pred_texts[0] if pred_texts else ""

            if not raw_digit_str:
                raw_digit_str = "未检测到数字"

            # 绘制标注
            cv2.rectangle(annotated, (px, py), (px+pw, py+ph), (0, 255, 0), 2)

            # 时序平滑：连续性约束 + 噪声抑制（可选）
            if use_temporal and hasattr(self, 'counter_smoother') and self.counter_smoother is not None:
                try:
                    smoothed_str, smooth_status = self.counter_smoother.update(raw_digit_str)
                    display_str = smoothed_str
                    cv2.putText(annotated, f"Raw: {raw_digit_str}", (px, py-35),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 255, 255), 1)
                    cv2.putText(annotated, f"Count: {display_str}", (px, py-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    logger.info(f"计数器识别: raw={raw_digit_str} smoothed={smoothed_str} [{smooth_status}]")
                    return smoothed_str, annotated
                except Exception as e:
                    logger.warning(f"时序平滑失败: {e}，回退到原始值")
                    cv2.putText(annotated, f"Count: {raw_digit_str}", (px, py-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    return raw_digit_str, annotated
            else:
                cv2.putText(annotated, f"Count: {raw_digit_str}", (px, py-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                logger.info(f"计数器识别结果: {raw_digit_str}")
                return raw_digit_str, annotated
        except Exception as e:
            logger.error(f"计数器识别失败: {e}")
            return f"识别错误: {e}", frame

    def detect_obstacles(self, base64_image: str) -> Tuple[List[Dict], str]:
        """检测障碍物并估算距离（带EMA时序平滑）

        Args:
            base64_image: Base64 编码的图像

        Returns:
            (obstacles_list, annotated_image_base64)
            obstacles_list: 检测到的障碍物列表
            annotated_image_base64: 带标注的图像
        """
        # 解码图像
        img_bytes = base64.b64decode(base64_image)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            logger.error("无法解码图像")
            return [], None

        # 检测障碍物
        obstacles, annotated_frame = self.obstacle_detector.detect_obstacles(frame)

        # 对距离做EMA时序平滑（缓解320x240低分辨率下的像素抖动）
        alpha = 0.35  # 新值权重35%，历史65%
        for obs in obstacles:
            cls = obs['class']
            raw_dist = obs['distance']
            if raw_dist is not None:
                prev = self._distance_smooth.get(cls)
                if prev is None:
                    smoothed = raw_dist
                else:
                    smoothed = alpha * raw_dist + (1 - alpha) * prev
                self._distance_smooth[cls] = smoothed
                obs['distance'] = smoothed

        # 编码标注后的图像
        _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        annotated_base64 = base64.b64encode(buffer).decode('utf-8')

        return obstacles, annotated_base64

    def analyze_obstacles(self, obstacles: List[Dict]) -> str:
        """生成障碍物分析报告

        Args:
            obstacles: detect_obstacles 返回的障碍物列表

        Returns:
            障碍物分析文本
        """
        if not obstacles:
            return "未检测到障碍物，前方道路安全。"

        # 按距离排序
        sorted_obs = sorted(
            [o for o in obstacles if o['distance']],
            key=lambda x: x['distance']
        )

        report_lines = []
        dangerous_count = 0

        # 统计信息
        total = len(obstacles)
        close_count = sum(1 for o in obstacles if o['distance'] and o['distance'] < 3)
        dangerous_count = sum(1 for o in obstacles if o['dangerous'])

        report_lines.append(f"检测到 {total} 个障碍物")

        if close_count > 0:
            report_lines.append(f"其中 {close_count} 个在 3 米以内")

        if dangerous_count > 0:
            report_lines.append(f"警告：{dangerous_count} 个危险障碍物")

        report_lines.append("")

        # 详细列表
        for i, obs in enumerate(sorted_obs, 1):
            class_name = obs['class']
            distance = obs['distance']
            confidence = obs['confidence']

            # 中文映射
            name_map = {
                'person': '人', 'child': '小孩', 'baby': '婴儿',
                'dog': '狗', 'cat': '猫',
                'car': '汽车', 'truck': '卡车', 'bus': '公交车',
                'bicycle': '自行车', 'motorcycle': '摩托车',
                'chair': '椅子', 'table': '桌子',
                'cup': '杯子', 'bottle': '瓶子', 'bag': '包',
                'box': '箱子', 'bag': '袋子'
            }
            chinese_name = name_map.get(class_name, class_name)

            conf_str = f"{confidence:.0%}"
            
            if distance:
                dist_str = f"{distance:.1f}米"
                report_lines.append(
                    f"{i}. {chinese_name}，距离约{dist_str}，置信度{conf_str}"
                )
            else:
                report_lines.append(
                    f"{i}. {chinese_name}，置信度{conf_str}"
                )

            if obs['dangerous']:
                report_lines[-1] += " 【注意】"

        # 总结建议
        if sorted_obs:
            nearest = sorted_obs[0]
            name_map = {'person': '行人', 'dog': '宠物', 'car': '车辆'}
            type_name = name_map.get(nearest['class'], '障碍物')
            report_lines.append("")
            if nearest['distance']:
                report_lines.append(f"最近{type_name}约{sorted_obs[0]['distance']:.1f}米，请注意避让。")
            else:
                report_lines.append(f"最近障碍物距离未知，请注意避让。")

        return "\n".join(report_lines)

    def compute_apf_avoidance(self, obstacles: List[Dict], frame_width: int = 320,
                               frame_height: int = 240) -> dict:
        """基于人工势场法（APF）计算避障参数

        物理模型：
        - 小车位于图像底部中心，朝向正上方（Y轴负方向）
        - 正前方目标产生恒定引力
        - 每个障碍物产生斥力（方向远离障碍物，大小与距离平方成反比）
        - 合力方向即为推荐行驶方向

        Args:
            obstacles: detect_obstacles 返回的障碍物列表
            frame_width: 图像宽度
            frame_height: 图像高度

        Returns:
            避障参数字典（含 steer_angle、speed_ratio、force_vectors 等）
        """
        import math

        params = {
            'obstacle_count': len(obstacles),
            'obstacles': [],
            'recommendation': '直行',
            'danger_level': 'safe',
            'nearest_distance': None,
            'nearest_class': None,
            'nearest_position': None,
            'steer_angle': 0.0,
            'speed_ratio': 1.0,
            'target_heading': 0.0,
            'force_vectors': {
                'att': (0.0, 0.0),
                'rep': [],
                'total': (0.0, 0.0),
            },
            'robot_pos': (frame_width // 2, frame_height),
        }

        if not obstacles:
            return params

        # APF 参数
        F_att_max = 100.0
        k_rep = 500.0
        d_influence = 5.0
        d_stop = 0.5
        d_max = 3.0
        eps = 0.1

        robot_x = frame_width / 2.0
        robot_y = float(frame_height)

        # 引力：指向正前方（图像顶部中心）
        f_att_x = 0.0
        f_att_y = -F_att_max

        f_rep_x_total = 0.0
        f_rep_y_total = 0.0
        rep_vectors = []

        # 逐个障碍物分析 + 斥力计算
        for obs in obstacles:
            x1, y1, x2, y2 = obs['bbox']
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            rel_x = center_x / frame_width

            if rel_x < 0.33:
                position = '左侧'
            elif rel_x > 0.67:
                position = '右侧'
            else:
                position = '正前方'

            params['obstacles'].append({
                'class': obs['class'],
                'distance': obs['distance'],
                'confidence': obs['confidence'],
                'center_x': int(center_x),
                'center_y': int(center_y),
                'bbox': obs['bbox'],
                'position': position,
                'relative_x': round(rel_x, 2),
                'dangerous': obs['dangerous'],
            })

            dist = obs.get('distance')
            if dist is not None and dist < d_influence:
                dx = robot_x - center_x
                dy = robot_y - center_y
                norm = math.sqrt(dx * dx + dy * dy) + eps
                ux = dx / norm
                uy = dy / norm
                force = k_rep / ((dist + eps) ** 2)
                frx = force * ux
                fry = force * uy
                f_rep_x_total += frx
                f_rep_y_total += fry
                rep_vectors.append((frx, fry))

        # 合力
        f_total_x = f_att_x + f_rep_x_total
        f_total_y = f_att_y + f_rep_y_total

        # 转向角：合力相对于正前方的角度（正值右转，负值左转）
        steer_angle = math.degrees(math.atan2(f_total_x, -f_total_y))

        # 找最近障碍物
        sorted_by_dist = sorted(
            [o for o in params['obstacles'] if o['distance']],
            key=lambda x: x['distance']
        )
        if sorted_by_dist:
            nearest = sorted_by_dist[0]
            params['nearest_distance'] = nearest['distance']
            params['nearest_class'] = nearest['class']
            params['nearest_position'] = nearest['position']

            d_nearest = nearest['distance']
            speed_ratio = max(0.0, min(1.0, (d_nearest - d_stop) / (d_max - d_stop)))

            # 安全兜底：最近障碍物 <0.5m 且在正前方 ±30° 范围内
            if d_nearest < d_stop and nearest['position'] == '正前方':
                steer_angle = 0.0
                speed_ratio = 0.0
        else:
            speed_ratio = 1.0

        # EMA 时序平滑（与距离平滑保持一致，alpha=0.35）
        if not hasattr(self, '_steer_smooth'):
            self._steer_smooth = 0.0
        if not hasattr(self, '_speed_smooth'):
            self._speed_smooth = 1.0

        alpha = 0.35
        self._steer_smooth = alpha * steer_angle + (1 - alpha) * self._steer_smooth
        self._speed_smooth = alpha * speed_ratio + (1 - alpha) * self._speed_smooth

        params['steer_angle'] = round(self._steer_smooth, 1)
        params['speed_ratio'] = round(self._speed_smooth, 2)
        params['target_heading'] = round(self._steer_smooth, 1)

        # 危险等级和文字建议
        if params['speed_ratio'] <= 0.05:
            params['danger_level'] = 'critical'
            params['recommendation'] = '停止'
        elif abs(params['steer_angle']) > 30:
            params['danger_level'] = 'high'
            params['recommendation'] = '左转避让' if params['steer_angle'] < 0 else '右转避让'
        elif abs(params['steer_angle']) > 10:
            params['danger_level'] = 'medium'
            params['recommendation'] = '左转' if params['steer_angle'] < 0 else '右转'
        else:
            params['danger_level'] = 'safe' if params['speed_ratio'] > 0.8 else 'medium'
            params['recommendation'] = '直行'

        # 向量数据（用于 GUI 绘制）
        params['force_vectors'] = {
            'att': (f_att_x, f_att_y),
            'rep': rep_vectors,
            'total': (f_total_x, f_total_y),
        }
        params['robot_pos'] = (int(robot_x), int(robot_y))

        return params

    def get_avoidance_params(self, obstacles: List[Dict], frame_width: int = 320,
                              frame_height: int = 240) -> dict:
        """生成智能小车避障参数（基于人工势场法 APF）

        Args:
            obstacles: detect_obstacles 返回的障碍物列表
            frame_width: 图像宽度（默认320）
            frame_height: 图像高度（默认240）

        Returns:
            避障参数字典，包含 steer_angle、speed_ratio、障碍物列表等
        """
        return self.compute_apf_avoidance(obstacles, frame_width, frame_height)

