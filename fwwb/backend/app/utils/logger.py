"""
日志工具模块
"""
import logging
import sys
from datetime import datetime


def setup_logger(level=logging.INFO):
    """设置全局日志配置"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_logger(name):
    """获取日志记录器"""
    return logging.getLogger(name)


# 模块级日志记录器
logger = get_logger('smart_car')
