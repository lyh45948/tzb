"""
工业计数器识别引擎

CRNN(CNN+BiLSTM) + CTC 端到端数字序列识别 + 时序平滑。
从 sjsb/vision_only/src/utils/VL.py 提取，模型结构与超参与原训练保持一致。
"""
import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class CRNN(nn.Module):
    """CRNN + CTC 端到端数字序列识别"""

    def __init__(self, num_classes: int = 11, hidden_size: int = 256):
        super().__init__()
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
        x, _ = self.rnn(x)
        x = self.fc(x)
        return x


def preprocess_for_crnn(roi_bgr: np.ndarray,
                        img_size: Tuple[int, int] = (32, 128)) -> np.ndarray:
    """将 BGR ROI 转 CRNN 输入：灰度 → 等比 resize → 左对齐 pad → 归一化到 [-1, 1]"""
    target_h, target_w = img_size
    if roi_bgr.ndim == 3:
        roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    else:
        roi = roi_bgr
    rh = target_h / max(roi.shape[0], 1)
    new_w = max(1, int(roi.shape[1] * rh))
    if new_w > target_w:
        new_w = target_w
    roi = cv2.resize(roi, (new_w, target_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    canvas[:, :new_w] = roi.astype(np.float32)
    canvas = (canvas / 255.0 - 0.5) / 0.5
    return canvas


def ctc_decode(preds: np.ndarray, blank: int = 10) -> List[str]:
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
    3. 单帧噪声不会连续出现，自然被过滤
    """

    def __init__(self, max_jump: int = 15, hold_frames: int = 3):
        self.confirmed_value: Optional[int] = None
        self.max_jump = max_jump
        self.hold_frames = hold_frames
        self.pending_value: Optional[int] = None
        self.pending_count = 0

    def _parse_value(self, s: str) -> Optional[int]:
        if not s or s in ('未检测到面板', '未检测到数字', '模型未加载', '识别错误'):
            return None
        try:
            val = int(s)
            if val < 0 or val > 999999:
                return None
            return val
        except (ValueError, TypeError):
            return None

    def update(self, raw_str: str) -> Tuple[str, str]:
        """输入当前帧原始识别字符串，返回 (平滑后字符串, 状态描述)"""
        raw_val = self._parse_value(raw_str)
        if raw_val is None:
            confirmed_str = str(self.confirmed_value) if self.confirmed_value is not None else raw_str
            return confirmed_str, "frame_invalid"

        if self.confirmed_value is None:
            self.confirmed_value = raw_val
            self.pending_value = None
            self.pending_count = 0
            return str(raw_val), "init"

        diff = abs(raw_val - self.confirmed_value)
        if diff <= self.max_jump:
            self.confirmed_value = raw_val
            self.pending_value = None
            self.pending_count = 0
            return str(raw_val), "confirmed"

        # 跳跃过大：连续 hold_frames 帧一致才接受
        if self.pending_value == raw_val:
            self.pending_count += 1
            if self.pending_count >= self.hold_frames:
                self.confirmed_value = raw_val
                self.pending_value = None
                self.pending_count = 0
                return str(raw_val), "jump_accepted"
            return str(self.confirmed_value), f"hold({raw_val},{self.pending_count})"
        else:
            self.pending_value = raw_val
            self.pending_count = 1
            return str(self.confirmed_value), f"hold({raw_val},1)"

    def reset(self):
        self.confirmed_value = None
        self.pending_value = None
        self.pending_count = 0


def load_crnn_from_checkpoint(ckpt_path: str, device: torch.device
                              ) -> Tuple[Optional[CRNN], Tuple[int, int]]:
    """从 checkpoint 加载 CRNN 模型，返回 (model, img_size)。失败返回 (None, (32,128))"""
    img_size = (32, 128)
    try:
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
        saved_args = ckpt.get('args', {}) if isinstance(ckpt, dict) else {}
        hidden_size = saved_args.get('hidden_size', 256)
        img_size = (saved_args.get('img_h', 32), saved_args.get('img_w', 128))
        model = CRNN(num_classes=11, hidden_size=hidden_size)
        model.load_state_dict(ckpt['model_state_dict'])
        model.to(device)
        model.eval()
        logger.info(f"CRNN 已加载: {ckpt_path} img_size={img_size}")
        return model, img_size
    except Exception as e:
        logger.warning(f"CRNN 加载失败 {ckpt_path}: {e}")
        return None, img_size
