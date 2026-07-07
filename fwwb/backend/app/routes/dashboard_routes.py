"""
数字孪生大屏聚合接口
"""
from flask import Response, jsonify, request, stream_with_context

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


@api_bp.route('/dashboard/stream', methods=['GET'])
def dashboard_stream():
    """SSE 长连接，周期性推送 dashboard 快照（event: snapshot）+ 心跳（event: ping）"""
    stream_service = get_service('dashboard_stream_service')
    if stream_service is None:
        return _error('SSE 推送服务未启用', 503)

    q = stream_service.subscribe()
    response = Response(
        stream_with_context(stream_service.event_stream(q)),
        mimetype='text/event-stream',
    )
    # 关键 header：禁缓存 + 关闭代理缓冲 + 保持长连接
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response
