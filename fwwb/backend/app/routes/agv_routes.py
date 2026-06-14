"""
AGV任务调度与路径规划占位接口
"""
import re

from flask import jsonify, request

from app.routes import api_bp
from app.services.registry import get_service
from app.utils.logger import get_logger

logger = get_logger('agv_routes')


# 简单 IPv4 正则：4 段 0-255 数字。不支持 IPv6/域名。
_IPV4_RE = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d?\d)$'
)


def _service():
    service = get_service('agv_task_service')
    if not service:
        raise RuntimeError('AGV任务服务未初始化')
    return service


def _udp_car_service():
    svc = get_service('udp_car_service')
    if not svc:
        raise RuntimeError('UDP小车服务未初始化')
    return svc


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


@api_bp.route('/agv/cars/connect', methods=['POST'])
def connect_agv_car():
    """连接一辆小车（通过 UDP）。请求体: { carIp, carPort?, deviceId? }"""
    try:
        body = _json_body()
        car_ip = (body.get('carIp') or '').strip()
        if not car_ip:
            return _error('缺少 carIp 参数', 400)
        if not _IPV4_RE.match(car_ip):
            return _error(f'carIp 格式不合法: {car_ip}', 400)

        # 端口校验
        try:
            car_port = int(body.get('carPort') or 7788)
        except (TypeError, ValueError):
            return _error('carPort 必须是整数', 400)
        if not (1 <= car_port <= 65535):
            return _error('carPort 必须在 1-65535', 400)

        # device_id 缺省时按 WebSocket 同样的规则生成，避免后续 status/disconnect 找不到
        device_id = (body.get('deviceId') or '').strip() or f"car_{car_ip.replace('.', '_')}"

        udp = _udp_car_service()
        success, msg = udp.connect_to_car(car_ip, car_port, device_id)
        if not success:
            return _error(msg or '连接失败', 400, {'deviceId': device_id, 'carIp': car_ip, 'carPort': car_port})

        status = udp.get_car_status(device_id)
        return _ok(
            {
                'deviceId': device_id,
                'carIp': car_ip,
                'carPort': car_port,
                'status': status,
            },
            msg or f'已连接到小车 {car_ip}:{car_port}',
        )
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'连接小车失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/cars/<device_id>', methods=['DELETE'])
def disconnect_agv_car(device_id):
    """断开指定小车"""
    try:
        udp = _udp_car_service()
        success, msg = udp.disconnect_car(device_id)
        if not success:
            # 找不到/已断开都算 404 比较直观
            return _error(msg or '断开失败', 404, {'deviceId': device_id})
        return _ok({'deviceId': device_id}, msg or f'已断开小车 {device_id}')
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'断开小车失败: {device_id} {e}')
        return _error(str(e), 500)


@api_bp.route('/agv/cars', methods=['DELETE'])
def disconnect_all_agv_cars():
    """断开所有小车"""
    try:
        udp = _udp_car_service()
        success, msg = udp.disconnect_car(None)  # device_id=None → 全部断开
        if not success:
            return _error(msg or '断开失败', 400)
        return _ok({}, msg or '已断开所有小车')
    except RuntimeError as e:
        return _error(str(e), 503)
    except Exception as e:
        logger.error(f'断开所有小车失败: {e}')
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
