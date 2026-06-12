"""
图像分析器 —— 障碍物检测 + 计数器识别 + APF 避障的组合编排

从 sjsb/vision_only/src/utils/VL.py 的 ImageAnalyzer 提取，关键改造：
- 去除单例（VisionService 持有唯一实例）
- 去除 ConfigManager 依赖，所有路径与阈值由构造参数注入
- 拆 detect_obstacles 为两个入口：
    * detect_obstacles_from_frame(frame): 直接接收 numpy BGR
    * detect_obstacles(base64_image): 兼容旧 API base64 入参
"""
import base64
import logging
import math
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

from app.vision.engine.counter_recognizer import (
    CounterTemporalSmoother,
    ctc_decode,
    load_crnn_from_checkpoint,
    preprocess_for_crnn,
)
from app.vision.engine.obstacle_detector import ObstacleDetector

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """图像分析器 —— 由 VisionService 持有，非单例"""

    def __init__(self,
                 obstacle_model_path: Optional[str] = None,
                 digit_panel_model_path: Optional[str] = None,
                 crnn_model_path: Optional[str] = None,
                 device: str = 'auto',
                 obstacle_conf: float = 0.05,
                 counter_conf: float = 0.3):
        self.obstacle_model_path = obstacle_model_path
        self.digit_panel_model_path = digit_panel_model_path
        self.crnn_model_path = crnn_model_path
        self.device_pref = device
        self.obstacle_conf = obstacle_conf
        self.counter_conf = counter_conf

        # 运行时状态
        self.device: torch.device = self._select_device(device)
        self.obstacle_detector: Optional[ObstacleDetector] = None
        self.counter_crnn = None
        self._crnn_img_size: Tuple[int, int] = (32, 128)
        self.yolo_panel_detector = None  # 数字面板 YOLOv8s
        self.counter_smoother = CounterTemporalSmoother(max_jump=15, hold_frames=3)
        self._distance_smooth: Dict[str, float] = {}
        self._panel_smooth: Optional[Tuple[int, int, int, int]] = None
        self._panel_alpha = 0.2
        self._steer_smooth = 0.0
        self._speed_smooth = 1.0
        self._initialized = False

    @staticmethod
    def _select_device(pref: str) -> torch.device:
        if pref == 'cuda' and not torch.cuda.is_available():
            logger.warning("配置要求 cuda 但不可用，回退到 cpu")
            pref = 'cpu'
        if pref not in ('cpu', 'cuda'):
            pref = 'cuda' if torch.cuda.is_available() else 'cpu'
        return torch.device(pref)

    def init(self) -> bool:
        """加载障碍物 YOLO + 数字面板 YOLO + CRNN，全部失败才返回 False"""
        if self._initialized:
            return True
        any_loaded = False

        # 障碍物检测器
        if self.obstacle_model_path:
            self.obstacle_detector = ObstacleDetector(
                model_path=self.obstacle_model_path,
                device=str(self.device),
                conf_thresh=self.obstacle_conf,
            )
            if self.obstacle_detector.init():
                any_loaded = True
            else:
                logger.warning("障碍物检测器加载失败，障碍物检测功能不可用")
                self.obstacle_detector = None

        # 数字面板 YOLO（可选；缺失则回退到 HSV 红色定位）
        if self.digit_panel_model_path:
            try:
                import os as _os
                if _os.path.exists(self.digit_panel_model_path):
                    from ultralytics import YOLO
                    self.yolo_panel_detector = YOLO(self.digit_panel_model_path)
                    self.yolo_panel_detector.to(self.device)
                    logger.info(f"数字面板 YOLO 已加载: {self.digit_panel_model_path}")
                    any_loaded = True
                else:
                    logger.warning(f"数字面板 YOLO 模型不存在: {self.digit_panel_model_path}，将使用 HSV 兜底")
            except Exception as e:
                logger.warning(f"数字面板 YOLO 加载失败: {e}")

        # CRNN
        if self.crnn_model_path:
            import os as _os
            if _os.path.exists(self.crnn_model_path):
                self.counter_crnn, self._crnn_img_size = load_crnn_from_checkpoint(
                    self.crnn_model_path, self.device
                )
                if self.counter_crnn is not None:
                    any_loaded = True
            else:
                logger.warning(f"CRNN 模型不存在: {self.crnn_model_path}")

        self._initialized = any_loaded
        if any_loaded:
            logger.info("ImageAnalyzer 初始化完成")
        else:
            logger.error("ImageAnalyzer 全部模型加载失败")
        return any_loaded

    # ============ 障碍物检测 ============

    def detect_obstacles_from_frame(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """直接接收 numpy BGR 帧，返回 (obstacles, annotated_bgr)"""
        if self.obstacle_detector is None:
            return [], frame
        obstacles, annotated = self.obstacle_detector.detect_obstacles(frame)
        # EMA 距离平滑
        alpha = 0.35
        for obs in obstacles:
            cls = obs['class']
            raw = obs.get('distance')
            if raw is None:
                continue
            prev = self._distance_smooth.get(cls)
            smoothed = raw if prev is None else alpha * raw + (1 - alpha) * prev
            self._distance_smooth[cls] = smoothed
            obs['distance'] = smoothed
        return obstacles, annotated

    def detect_obstacles(self, base64_image: str) -> Tuple[List[Dict], Optional[str]]:
        """base64 入口 (兼容外部 POST 视觉数据)，返回 (obstacles, annotated_base64)"""
        try:
            img_bytes = base64.b64decode(base64_image)
            arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                logger.error("base64 图像解码失败")
                return [], None
        except Exception as e:
            logger.error(f"base64 解码异常: {e}")
            return [], None

        obstacles, annotated_frame = self.detect_obstacles_from_frame(frame)
        try:
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            annotated_b64 = base64.b64encode(buffer).decode('utf-8')
        except Exception:
            annotated_b64 = None
        return obstacles, annotated_b64

    # ============ 计数器识别 ============

    def _locate_counter_panel(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """红色数码管面板 HSV 定位 + EMA 平滑 + 内缩到纯数字区域（YOLO 失败时的兜底）"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([15, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([155, 60, 60]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(mask1, mask2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return self._panel_smooth

        best = max(contours, key=cv2.contourArea)
        if cv2.contourArea(best) < 200:
            return self._panel_smooth

        raw = cv2.boundingRect(best)
        if self._panel_smooth is not None:
            rx, ry, rw, rh = raw
            sx, sy, sw, sh = self._panel_smooth
            px = int(self._panel_alpha * rx + (1 - self._panel_alpha) * sx)
            py = int(self._panel_alpha * ry + (1 - self._panel_alpha) * sy)
            pw = int(self._panel_alpha * rw + (1 - self._panel_alpha) * sw)
            ph = int(self._panel_alpha * rh + (1 - self._panel_alpha) * sh)
        else:
            px, py, pw, ph = raw

        h, w = img.shape[:2]
        px = max(0, min(px, w - 1))
        py = max(0, min(py, h - 1))
        pw = min(pw, w - px)
        ph = min(ph, h - py)

        # 内缩去外壳/标签，聚焦纯数字区
        st, sb, sl, sr = 0.22, 0.18, 0.08, 0.08
        cx = px + int(pw * sl)
        cy = py + int(ph * st)
        cw = int(pw * (1 - sl - sr))
        ch = int(ph * (1 - st - sb))
        cx = max(0, min(cx, w - 1))
        cy = max(0, min(cy, h - 1))
        cw = max(10, min(cw, w - cx))
        ch = max(10, min(ch, h - cy))
        panel = (cx, cy, cw, ch)
        self._panel_smooth = panel
        return panel

    def recognize_counter(self, frame: np.ndarray,
                          conf_thresh: Optional[float] = None,
                          use_temporal: bool = True
                          ) -> Tuple[str, np.ndarray, Dict]:
        """计数器端到端识别。

        Returns:
            (display_str, annotated_frame, meta)
            meta 包含 raw / smooth_status / panel_bbox 等元信息
        """
        meta: Dict = {'raw': '', 'smooth_status': '', 'panel_bbox': None}
        if conf_thresh is None:
            conf_thresh = self.counter_conf
        if self.counter_crnn is None:
            return "模型未加载", frame, meta

        annotated = frame.copy()
        try:
            # 1) 定位数字面板
            px, py, pw, ph = 0, 0, 0, 0
            if self.yolo_panel_detector is not None:
                results = self.yolo_panel_detector(frame, verbose=False, device=self.device)
                best_box, best_conf = None, 0.0
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
                    px, py, pw, ph = int(x1), int(y1), int(x2 - x1), int(y2 - y1)
                else:
                    panel = self._locate_counter_panel(frame)
                    if panel is None:
                        return "未检测到面板", annotated, meta
                    px, py, pw, ph = panel
            else:
                panel = self._locate_counter_panel(frame)
                if panel is None:
                    return "未检测到面板", annotated, meta
                px, py, pw, ph = panel

            roi = frame[py:py + ph, px:px + pw]
            if roi.size == 0:
                return "未检测到面板", annotated, meta
            meta['panel_bbox'] = [int(px), int(py), int(px + pw), int(py + ph)]

            # 2) CRNN 推理
            arr = preprocess_for_crnn(roi, img_size=self._crnn_img_size)
            tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0).to(self.device)
            with torch.no_grad():
                outputs = self.counter_crnn(tensor)
                preds = outputs.argmax(dim=2).cpu().numpy()
                pred_texts = ctc_decode(preds)
                raw_str = pred_texts[0] if pred_texts else ""
            if not raw_str:
                raw_str = "未检测到数字"
            meta['raw'] = raw_str

            cv2.rectangle(annotated, (px, py), (px + pw, py + ph), (0, 255, 0), 2)

            # 3) 时序平滑
            if use_temporal:
                try:
                    smoothed_str, status = self.counter_smoother.update(raw_str)
                    meta['smooth_status'] = status
                    cv2.putText(annotated, f"Raw: {raw_str}", (px, max(py - 35, 15)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 255, 255), 1)
                    cv2.putText(annotated, f"Count: {smoothed_str}", (px, max(py - 10, 15)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    return smoothed_str, annotated, meta
                except Exception as e:
                    logger.warning(f"时序平滑失败: {e}，回退原始值")
            cv2.putText(annotated, f"Count: {raw_str}", (px, max(py - 10, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            return raw_str, annotated, meta
        except Exception as e:
            logger.error(f"计数器识别异常: {e}")
            return f"识别错误: {e}", frame, meta

    # ============ APF 避障参数 ============

    def compute_apf_avoidance(self, obstacles: List[Dict],
                              frame_width: int = 320,
                              frame_height: int = 240) -> Dict:
        """基于人工势场法计算避障参数（保留 EMA 平滑状态）"""
        params: Dict = {
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
            'force_vectors': {'att': (0.0, 0.0), 'rep': [], 'total': (0.0, 0.0)},
            'robot_pos': (frame_width // 2, frame_height),
        }
        if not obstacles:
            return params

        F_att_max = 100.0
        k_rep = 500.0
        d_influence = 5.0
        d_stop = 0.5
        d_max = 3.0
        eps = 0.1

        robot_x = frame_width / 2.0
        robot_y = float(frame_height)

        f_att_x = 0.0
        f_att_y = -F_att_max
        f_rep_x_total = 0.0
        f_rep_y_total = 0.0
        rep_vectors = []

        for obs in obstacles:
            x1, y1, x2, y2 = obs['bbox']
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            rel_x = cx / frame_width
            if rel_x < 0.33:
                position = '左侧'
            elif rel_x > 0.67:
                position = '右侧'
            else:
                position = '正前方'

            params['obstacles'].append({
                'class': obs['class'],
                'distance': obs.get('distance'),
                'confidence': obs.get('confidence'),
                'center_x': int(cx),
                'center_y': int(cy),
                'bbox': obs['bbox'],
                'position': position,
                'relative_x': round(rel_x, 2),
                'dangerous': obs.get('dangerous', False),
            })

            dist = obs.get('distance')
            if dist is not None and dist < d_influence:
                dx = robot_x - cx
                dy = robot_y - cy
                norm = math.sqrt(dx * dx + dy * dy) + eps
                ux, uy = dx / norm, dy / norm
                force = k_rep / ((dist + eps) ** 2)
                frx, fry = force * ux, force * uy
                f_rep_x_total += frx
                f_rep_y_total += fry
                rep_vectors.append((frx, fry))

        f_total_x = f_att_x + f_rep_x_total
        f_total_y = f_att_y + f_rep_y_total
        steer_angle = math.degrees(math.atan2(f_total_x, -f_total_y))

        sorted_by_dist = sorted(
            [o for o in params['obstacles'] if o.get('distance')],
            key=lambda x: x['distance']
        )
        if sorted_by_dist:
            nearest = sorted_by_dist[0]
            params['nearest_distance'] = nearest['distance']
            params['nearest_class'] = nearest['class']
            params['nearest_position'] = nearest['position']
            d_nearest = nearest['distance']
            speed_ratio = max(0.0, min(1.0, (d_nearest - d_stop) / (d_max - d_stop)))
            if d_nearest < d_stop and nearest['position'] == '正前方':
                steer_angle = 0.0
                speed_ratio = 0.0
        else:
            speed_ratio = 1.0

        # EMA 平滑
        alpha = 0.35
        self._steer_smooth = alpha * steer_angle + (1 - alpha) * self._steer_smooth
        self._speed_smooth = alpha * speed_ratio + (1 - alpha) * self._speed_smooth

        params['steer_angle'] = round(self._steer_smooth, 1)
        params['speed_ratio'] = round(self._speed_smooth, 2)
        params['target_heading'] = round(self._steer_smooth, 1)

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

        params['force_vectors'] = {
            'att': (f_att_x, f_att_y),
            'rep': rep_vectors,
            'total': (f_total_x, f_total_y),
        }
        params['robot_pos'] = (int(robot_x), int(robot_y))
        return params

    # ============ 文本报告 ============

    @staticmethod
    def analyze_obstacles_text(obstacles: List[Dict]) -> str:
        """生成中文障碍物分析报告"""
        if not obstacles:
            return "未检测到障碍物，前方道路安全。"

        sorted_obs = sorted(
            [o for o in obstacles if o.get('distance')],
            key=lambda x: x['distance']
        )
        total = len(obstacles)
        close_count = sum(1 for o in obstacles if o.get('distance') and o['distance'] < 3)
        dangerous_count = sum(1 for o in obstacles if o.get('dangerous'))
        lines = [f"检测到 {total} 个障碍物"]
        if close_count > 0:
            lines.append(f"其中 {close_count} 个在 3 米以内")
        if dangerous_count > 0:
            lines.append(f"警告：{dangerous_count} 个危险障碍物")
        lines.append("")

        name_map = {
            'person': '人', 'child': '小孩', 'baby': '婴儿',
            'dog': '狗', 'cat': '猫',
            'car': '汽车', 'truck': '卡车', 'bus': '公交车',
            'bicycle': '自行车', 'motorcycle': '摩托车',
            'chair': '椅子', 'table': '桌子',
            'cup': '杯子', 'bottle': '瓶子', 'bag': '包',
            'box': '箱子',
        }
        for i, obs in enumerate(sorted_obs, 1):
            chinese = name_map.get(obs['class'], obs['class'])
            conf_str = f"{obs.get('confidence', 0):.0%}"
            distance = obs.get('distance')
            if distance:
                lines.append(f"{i}. {chinese}，距离约{distance:.1f}米，置信度{conf_str}")
            else:
                lines.append(f"{i}. {chinese}，置信度{conf_str}")
            if obs.get('dangerous'):
                lines[-1] += " 【注意】"

        if sorted_obs:
            nearest = sorted_obs[0]
            type_name = {'person': '行人', 'dog': '宠物', 'car': '车辆'}.get(nearest['class'], '障碍物')
            lines.append("")
            if nearest.get('distance'):
                lines.append(f"最近{type_name}约{nearest['distance']:.1f}米，请注意避让。")
            else:
                lines.append(f"最近障碍物距离未知，请注意避让。")
        return "\n".join(lines)
