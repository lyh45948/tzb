"""
数字孪生大屏聚合接口
"""
from flask import jsonify, request

from app.routes import api_bp
from app.services.registry import get_service
from app.utils.logger import get_logger

logger = get_logger('dashboard_routes')


def _service():
    service = get_service('dashboard_service')
    if not service:
        raise RuntimeError('数字孪生大屏服务未初始化')
    return service


def _ok(data=None, message='ok'):
    return jsonify({
        'code': 0,
        'data': data,
        'message': message,
    })


def _error(message, status=400):
    return jsonify({
        'code': 1,
        'message': message,
    }), status


@api_bp.route('/dashboard/snapshot', methods=['GET'])
def get_dashboard_snapshot():
    """获取数字孪生大屏当前快照"""
    try:
        return _ok(_service().get_snapshot())
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'获取数字孪生快照失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/dashboard/current', methods=['GET'])
def get_dashboard_current():
    """获取数字孪生大屏当前快照别名"""
    return get_dashboard_snapshot()


@api_bp.route('/dashboard/history', methods=['GET'])
def get_dashboard_history():
    """获取数字孪生历史曲线占位数据"""
    try:
        limit = request.args.get('limit', 60)
        return _ok(_service().get_history(limit=limit))
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'获取数字孪生历史数据失败: {e}')
        return _error(str(e), 500)
