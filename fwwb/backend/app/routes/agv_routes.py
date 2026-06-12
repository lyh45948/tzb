"""
AGV任务调度与路径规划占位接口
"""
from flask import jsonify, request

from app.routes import api_bp
from app.services.registry import get_service
from app.utils.logger import get_logger

logger = get_logger('agv_routes')


def _service():
    service = get_service('agv_task_service')
    if not service:
        raise RuntimeError('AGV任务服务未初始化')
    return service


def _json_body():
    return request.get_json(silent=True) or {}


def _ok(data=None, message='ok'):
    return jsonify({
        'code': 0,
        'data': data,
        'message': message,
    })


def _error(message, status=400, data=None):
    return jsonify({
        'code': 1,
        'data': data,
        'message': message,
    }), status


@api_bp.route('/agv/points', methods=['GET'])
def list_agv_points():
    """获取AGV演示点位"""
    try:
        return _ok(_service().list_points())
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'获取AGV点位失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/cars', methods=['GET'])
def list_agv_cars():
    """获取AGV小车状态列表"""
    try:
        return _ok(_service().get_agv_status_list())
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'获取AGV状态列表失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/cars/<device_id>', methods=['GET'])
def get_agv_car(device_id):
    """获取单辆AGV状态"""
    try:
        data = _service().get_agv_status(device_id)
        if not data:
            return _error('小车未连接且无任务记录', 404)
        return _ok(data)
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'获取AGV状态失败: {device_id} {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/fleet', methods=['GET'])
def get_agv_fleet():
    """获取数字孪生友好的AGV车队快照"""
    try:
        return _ok(_service().get_dashboard_fleet())
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'获取AGV车队快照失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/tasks/preview', methods=['POST'])
def preview_agv_task():
    """预览AGV占位路径，不落库、不下发"""
    try:
        body = _json_body()
        data = _service().preview_task(
            start_point=body.get('start_point'),
            end_point=body.get('end_point'),
            device_id=body.get('device_id'),
            task_type=body.get('task_type', 'materialTransfer'),
            template_id=body.get('template_id'),
            title=body.get('title'),
            description=body.get('description'),
            priority=body.get('priority', 0),
            source=body.get('source', 'api'),
        )
        return _ok(data)
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        logger.error(f'预览AGV任务失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/tasks/dispatch', methods=['POST'])
def create_and_dispatch_agv_task():
    """创建并立即下发AGV任务"""
    try:
        body = _json_body()
        result = _service().create_and_dispatch_task(
            device_id=body.get('device_id'),
            start_point=body.get('start_point'),
            end_point=body.get('end_point'),
            force=bool(body.get('force', False)),
            priority=body.get('priority', 0),
            task_type=body.get('task_type', 'materialTransfer'),
            template_id=body.get('template_id'),
            title=body.get('title'),
            description=body.get('description'),
            source=body.get('source', 'api'),
        )
        status = 200 if result.get('sent') else 400
        return _ok(result, result.get('message', '任务已创建并下发')) if result.get('sent') else _error(result.get('message', '下发失败'), status, result)
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        logger.error(f'创建并下发AGV任务失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/tasks', methods=['POST'])
def create_agv_task():
    """创建AGV任务"""
    try:
        body = _json_body()
        task = _service().create_task(
            device_id=body.get('device_id'),
            start_point=body.get('start_point'),
            end_point=body.get('end_point'),
            priority=body.get('priority', 0),
            task_type=body.get('task_type', 'materialTransfer'),
            template_id=body.get('template_id'),
            title=body.get('title'),
            description=body.get('description'),
            source=body.get('source', 'api'),
        )
        return _ok(task, '任务已创建')
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        logger.error(f'创建AGV任务失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/tasks', methods=['GET'])
def list_agv_tasks():
    """查询AGV任务列表"""
    try:
        tasks = _service().list_tasks(
            device_id=request.args.get('device_id'),
            status=request.args.get('status'),
            limit=request.args.get('limit', 100),
        )
        return _ok(tasks)
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'查询AGV任务列表失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/tasks/<task_id>', methods=['GET'])
def get_agv_task(task_id):
    """查询AGV任务详情"""
    try:
        task = _service().get_task(task_id)
        if not task:
            return _error('任务不存在', 404)
        return _ok(task)
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'查询AGV任务失败: {task_id} {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/tasks/<task_id>/dispatch', methods=['POST'])
def dispatch_agv_task(task_id):
    """下发AGV任务"""
    try:
        body = _json_body()
        result = _service().dispatch_task(task_id, force=bool(body.get('force', False)))
        if not result.get('sent'):
            return _error(result.get('message', '下发失败'), 400, result)
        return _ok(result, result.get('message', '任务已下发'))
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        logger.error(f'下发AGV任务失败: {task_id} {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/tasks/<task_id>/status', methods=['PATCH'])
def update_agv_task_status(task_id):
    """手动更新AGV任务状态"""
    try:
        body = _json_body()
        status = body.get('status')
        if not status:
            return _error('缺少 status', 400)
        task = _service().update_task_status(task_id, status, body.get('error_message'))
        return _ok(task, '任务状态已更新')
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        logger.error(f'更新AGV任务状态失败: {task_id} {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/demo/tasks/templates', methods=['GET'])
def list_demo_task_templates():
    """获取AGV演示任务模板"""
    try:
        return _ok(_service().list_demo_task_templates())
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'获取AGV演示任务模板失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/demo/tasks/generate', methods=['POST'])
def generate_demo_tasks():
    """按场景生成AGV演示任务"""
    try:
        body = _json_body()
        result = _service().generate_demo_tasks(
            scenario=body.get('scenario', 'factory_shift'),
            count=body.get('count'),
            device_id=body.get('device_id'),
            auto_dispatch=bool(body.get('auto_dispatch', False)),
        )
        return _ok(result, '演示任务已生成')
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        logger.error(f'生成AGV演示任务失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/demo/tasks/<template_id>/dispatch', methods=['POST'])
def dispatch_demo_task_template(template_id):
    """按演示模板创建并下发任务"""
    try:
        body = _json_body()
        result = _service().dispatch_demo_template(
            template_id=template_id,
            device_id=body.get('device_id'),
            force=bool(body.get('force', False)),
        )
        if not result.get('sent'):
            return _error(result.get('message', '下发失败'), 400, result)
        return _ok(result, '演示任务已创建并下发')
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        logger.error(f'下发AGV演示任务失败: {template_id} {e}')
        return _error(str(e), 500)
