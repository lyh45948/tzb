"""
障碍物检测引擎

基于 YOLOv11 / YOLOv8 进行 COCO 类别检测，配合针孔相机模型估算距离。
从 sjsb/vision_only/src/utils/VL.py 的 ObstacleDetector 类提取，去除
ConfigManager 依赖，所有参数由构造注入。
"""
import logging
import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ObstacleDetector:
    """基于 YOLO 的障碍物检测器（含距离估算）"""

    # 常见障碍物类别及其典型物理尺寸（米）：[width, height, depth]
    OBJECT_SIZES = {
        # 人形障碍物
        'person': [0.5, 1.7, 0.3],
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
        'couch': [1.8, 0.8, 0.9],
        'bed': [2.0, 0.5, 1.5],
        'dining table': [1.2, 0.75, 0.6],
        # 车辆
        'car': [1.8, 1.5, 4.5],
        'truck': [2.5, 2.5, 8.0],
        'bus': [3.0, 3.0, 12.0],
        'bicycle': [0.6, 1.1, 1.8],
        'motorcycle': [0.8, 1.2, 2.0],
        'stroller': [0.6, 1.0, 0.8],
        # 日常物品
        'cup': [0.08, 0.12, 0.08],
        'bottle': [0.08, 0.25, 0.08],
        'bag': [0.4, 0.5, 0.2],
        'suitcase': [0.5, 0.6, 0.3],
        'handbag': [0.4, 0.3, 0.15],
        'backpack': [0.4, 0.5, 0.2],
        # 建筑元素
        'pole': [0.2, 2.0, 0.2],
        'tree': [2.0, 3.0, 2.0],
        'stairs': [1.2, 0.2, 0.3],
        # 杂项
        'box': [0.5, 0.4, 0.5],
        'umbrella': [0.8, 2.0, 0.8],
        'ball': [0.22, 0.22, 0.22],
        'vase': [0.15, 0.3, 0.15],
        'book': [0.2, 0.3, 0.02],
        'remote': [0.05, 0.15, 0.02],
        'keyboard': [0.15, 0.05, 0.02],
        'bowl': [0.15, 0.08, 0.15],
        'spoon': [0.02, 0.2, 0.005],
        'clock': [0.2, 0.2, 0.02],
        'scissors': [0.1, 0.03, 0.005],
        'teddy bear': [0.3, 0.4, 0.2],
        'refrigerator': [0.7, 1.8, 0.8],
        'potted plant': [0.3, 0.5, 0.3],
        'cell phone': [0.07, 0.15, 0.005],
        'toothbrush': [0.02, 0.18, 0.005],
        'laptop': [0.35, 0.25, 0.03],
        'tv': [0.8, 0.5, 0.1],
        'mouse': [0.06, 0.03, 0.02],
    }

    DEFAULT_FOCAL_LENGTH = 600  # ESP32 广角摄像头典型焦距（像素）

    def __init__(self, model_path: Optional[str] = None,
                 focal_length: Optional[float] = None,
                 device: str = 'auto',
                 conf_thresh: float = 0.05):
        """初始化

        Args:
            model_path: YOLO 模型路径（.pt 文件）
            focal_length: 像素焦距，可由 calibrate() 标定
            device: 'auto' / 'cpu' / 'cuda'
            conf_thresh: 置信度阈值
        """
        self.model_path = model_path
        self.focal_length = focal_length or self.DEFAULT_FOCAL_LENGTH
        self.device = device
        self.conf_thresh = conf_thresh
        self.model = None
        self._initialized = False

    def init(self) -> bool:
        if self._initialized:
            return True
        try:
            from ultralytics import YOLO
            import torch
            if self.device == 'cuda' and not torch.cuda.is_available():
                logger.warning("配置要求 cuda 但不可用，回退到 cpu")
                device = 'cpu'
            elif self.device in ('cpu', 'cuda'):
                device = self.device
            else:
                device = 'cuda' if torch.cuda.is_available() else 'cpu'

            if not self.model_path or not os.path.exists(self.model_path):
                logger.error(f"障碍物 YOLO 模型不存在: {self.model_path}")
                return False
            logger.info(f"加载障碍物 YOLO 模型: {self.model_path} (device={device})")
            self.model = YOLO(self.model_path)
            self.model.to(device)
            self._initialized = True
            logger.info("障碍物 YOLO 模型加载成功")
            return True
        except ImportError:
            logger.error("缺少 ultralytics，请 pip install ultralytics")
            return False
        except Exception as e:
            logger.error(f"YOLO 加载失败: {e}")
            return False

    def calibrate(self, known_distance: float, known_width: float, measured_width: float):
        """通过已知距离/宽度的参考物体标定焦距"""
        if measured_width > 0:
            self.focal_length = (measured_width * known_distance) / known_width
            logger.info(f"焦距已标定为 {self.focal_length:.2f} px")

    def _estimate_distance(self, class_name: str, bbox_width: int, bbox_height: int,
                           frame_width: int, frame_height: int, bbox_y1: int) -> Optional[float]:
        """针孔相机模型: distance = real_size * focal_length / apparent_size"""
        if class_name not in self.OBJECT_SIZES:
            chinese_map = {
                '人': 'person', '狗': 'dog', '猫': 'cat',
                '车': 'car', '桌子': 'table', '椅子': 'chair',
                '杯子': 'cup', '瓶子': 'bottle', '包': 'bag',
                '树': 'tree', '盒': 'box',
            }
            mapped = chinese_map.get(class_name)
            if mapped and mapped in self.OBJECT_SIZES:
                class_name = mapped
            else:
                return None

        sizes = self.OBJECT_SIZES[class_name]
        real_width = sizes[0]
        normalized_width = bbox_width / max(frame_width, 1)
        if normalized_width <= 0.001:
            return None

        distance = (real_width * self.focal_length) / max(bbox_width, 1)
        if len(sizes) >= 2:
            real_height = sizes[1]
            distance_h = (real_height * self.focal_length) / max(bbox_height, 1)
            distance = (distance + distance_h) / 2

        # 垂直位置修正：底部物体更近
        if bbox_y1 > 0:
            bbox_center_y = bbox_y1 + bbox_height / 2
            vertical_ratio = bbox_center_y / max(frame_height, 1)
            if vertical_ratio < 0.3:
                distance *= 1.2
            elif vertical_ratio > 0.6:
                distance *= 0.9
            else:
                distance *= (1.5 - vertical_ratio)

        return max(0.3, min(distance, 50))

    def detect_obstacles(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """检测障碍物并返回带标注的副本图像

        Returns:
            (obstacles_list, annotated_frame_bgr)
            obstacles_list[i] = {
                'class', 'class_id', 'confidence', 'bbox': [x1,y1,x2,y2],
                'distance': float|None, 'dangerous': bool
            }
        """
        if not self._initialized and not self.init():
            return [], frame

        results = self.model(frame, verbose=False)[0]
        obstacles: List[Dict] = []
        annotated = frame.copy()
        dangerous_classes = {
            'person', 'child', 'baby', 'dog', 'car', 'truck', 'bus',
            'bicycle', 'motorcycle', 'stroller',
        }

        for box in results.boxes:
            class_id = int(box.cls.cpu().numpy()[0])
            class_name = results.names[class_id]
            confidence = float(box.conf.cpu().numpy()[0])
            if confidence < self.conf_thresh:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])
            bw, bh = x2 - x1, y2 - y1
            distance = self._estimate_distance(class_name, bw, bh,
                                               frame.shape[1], frame.shape[0], y1)
            obstacle = {
                'class': class_name,
                'class_id': class_id,
                'confidence': confidence,
                'bbox': [x1, y1, x2, y2],
                'distance': distance,
                'dangerous': class_name in dangerous_classes,
            }
            obstacles.append(obstacle)

            label = f"{class_name} {confidence:.2f}"
            if distance is not None:
                label += f" {distance:.1f}m"
            color = (0, 0, 255) if obstacle['dangerous'] else (0, 255, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, label, (x1, max(y1 - 10, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return obstacles, annotated
