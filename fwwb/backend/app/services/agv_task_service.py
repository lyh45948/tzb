"""
AGV任务调度与路径规划占位服务
"""
from datetime import datetime
from math import atan2, degrees

from app import db
from app.models.agv_task import AGVTask
from app.utils.logger import get_logger

logger = get_logger('agv_task_service')


class AGVTaskService:
    """AGV任务服务 - 提供占位调度、路径规划和数字孪生数据适配"""

    ACTIVE_STATUSES = ('created', 'dispatched', 'running')
    VALID_STATUSES = ('created', 'dispatched', 'running', 'completed', 'failed', 'cancelled')
    PLANNER_VERSION = 'placeholder-v1'
    POINT_UNIT = 'cm'

    ROBOT_NAMES = ['AGV-01', '巡检车-01', '物料车-01', '安防巡检-02']
    ROBOT_DEVICE_IDS = ['demo_car_001', 'demo_car_002', 'demo_car_003', 'demo_car_004']

    POINTS = {
        'A': {
            'x': 0, 'y': 0, 'name': '工位A', 'type': 'workstation',
            'description': '基础演示起点A', 'scene_position': {'x': -11, 'z': -7}
        },
        'B': {
            'x': 100, 'y': 0, 'name': '工位B', 'type': 'workstation',
            'description': '基础演示终点B', 'scene_position': {'x': 11, 'z': -7}
        },
        'C': {
            'x': 100, 'y': 100, 'name': '工位C', 'type': 'workstation',
            'description': '基础演示点C', 'scene_position': {'x': 11, 'z': 7}
        },
        'D': {
            'x': 0, 'y': 100, 'name': '工位D', 'type': 'workstation',
            'description': '基础演示点D', 'scene_position': {'x': -11, 'z': 7}
        },
        'RAW_MATERIAL': {
            'x': 0, 'y': 0, 'name': '原料区', 'type': 'material',
            'description': 'AGV物料转运起点', 'scene_position': {'x': -11, 'z': -7}
        },
        'PRODUCTION_LINE': {
            'x': 100, 'y': 0, 'name': '产线工位', 'type': 'production',
            'description': '生产线收料/出料工位', 'scene_position': {'x': 11, 'z': -7}
        },
        'WAREHOUSE': {
            'x': 100, 'y': 100, 'name': '仓储区', 'type': 'warehouse',
            'description': '成品/物料仓储区域', 'scene_position': {'x': 11, 'z': 7}
        },
        'INSPECTION': {
            'x': 0, 'y': 100, 'name': '巡检点', 'type': 'inspection',
            'description': 'AGV安全巡检起点', 'scene_position': {'x': -11, 'z': 7}
        },
        'GAS_ZONE': {
            'x': 50, 'y': 100, 'name': '危气监测区', 'type': 'safety',
            'description': '危气/火焰监测重点区域', 'scene_position': {'x': 0, 'z': 7}
        },
        'CHARGING': {
            'x': 0, 'y': 50, 'name': '充电区', 'type': 'charging',
            'description': 'AGV回充停靠区', 'scene_position': {'x': -11, 'z': 0}
        },
    }

    DEMO_TASK_TEMPLATES = {
        'material_transfer': {
            'template_id': 'material_transfer',
            'title': '物料转运：原料区 → 产线工位',
            'description': '模拟AGV将原料从原料区配送至产线工位',
            'task_type': 'materialTransfer',
            'dashboard_task': 'materialTransfer',
            'start_point': 'RAW_MATERIAL',
            'end_point': 'PRODUCTION_LINE',
            'priority': 5,
        },
        'warehouse_delivery': {
            'template_id': 'warehouse_delivery',
            'title': '成品入库：产线工位 → 仓储区',
            'description': '模拟AGV将产线成品转运至仓储区',
            'task_type': 'materialTransfer',
            'dashboard_task': 'materialTransfer',
            'start_point': 'PRODUCTION_LINE',
            'end_point': 'WAREHOUSE',
            'priority': 4,
        },
        'safety_patrol': {
            'template_id': 'safety_patrol',
            'title': '安全巡检：巡检点 → 危气监测区',
            'description': '模拟AGV执行危气区域安全巡检任务',
            'task_type': 'gasMonitor',
            'dashboard_task': 'gasMonitor',
            'start_point': 'INSPECTION',
            'end_point': 'GAS_ZONE',
            'priority': 8,
        },
        'goods_count_route': {
            'template_id': 'goods_count_route',
            'title': '货物计数巡检：仓储区 → 巡检点',
            'description': '模拟AGV巡检仓储区并联动货物计数模块',
            'task_type': 'goodsCount',
            'dashboard_task': 'goodsCount',
            'start_point': 'WAREHOUSE',
            'end_point': 'INSPECTION',
            'priority': 3,
        },
        'return_to_charge': {
            'template_id': 'return_to_charge',
            'title': '低电量回充：工位A → 充电区',
            'description': '模拟AGV低电量时返回充电区',
            'task_type': 'charging',
            'dashboard_task': 'idle',
            'start_point': 'A',
            'end_point': 'CHARGING',
            'priority': 9,
        },
    }

    SCENARIOS = {
        'factory_shift': ['material_transfer', 'warehouse_delivery', 'safety_patrol', 'goods_count_route'],
        'safety_demo': ['safety_patrol', 'return_to_charge'],
        'logistics_demo': ['material_transfer', 'warehouse_delivery', 'goods_count_route'],
    }

    def __init__(self, app, data_service=None, udp_car_service=None):
        self.app = app
        self.data_service = data_service
        self.udp_car_service = udp_car_service

    def list_points(self):
        return {
            'unit': self.POINT_UNIT,
            'planner_version': self.PLANNER_VERSION,
            'points': self.POINTS,
        }

    def list_demo_task_templates(self):
        return list(self.DEMO_TASK_TEMPLATES.values())

    def preview_task(self, start_point, end_point, device_id=None, task_type='materialTransfer',
                     template_id=None, title=None, description=None, priority=0, source='api'):
        plan = self.generate_placeholder_path(start_point, end_point)
        return {
            'device_id': device_id,
            'task_type': task_type,
            'template_id': template_id,
            'title': title,
            'description': description,
            'source': source,
            'start_point': start_point,
            'end_point': end_point,
            'priority': priority,
            'unit': self.POINT_UNIT,
            'planner_version': self.PLANNER_VERSION,
            **plan,
        }

    def create_task(self, device_id, start_point, end_point, priority=0, task_type='materialTransfer',
                    template_id=None, title=None, description=None, source='api'):
        if not device_id:
            raise ValueError('缺少 device_id')

        preview = self.preview_task(
            start_point=start_point,
            end_point=end_point,
            device_id=device_id,
            task_type=task_type,
            template_id=template_id,
            title=title,
            description=description,
            priority=priority,
            source=source,
        )

        with self.app.app_context():
            task = AGVTask(
                task_no=self._generate_task_no(),
                device_id=device_id,
                task_type=task_type,
                template_id=template_id,
                title=title or self._default_task_title(start_point, end_point),
                description=description,
                source=source,
                start_point=start_point,
                end_point=end_point,
                status='created',
                priority=priority,
                path_waypoints=preview['path_waypoints'],
                path_commands=preview['path_commands'],
                command_payload=preview['command_payload'],
                planner_version=self.PLANNER_VERSION,
            )
            db.session.add(task)
            db.session.commit()
            logger.info(f"AGV任务已创建: {task.task_no} {device_id} {start_point}->{end_point}")
            return task.to_dict()

    def list_tasks(self, device_id=None, status=None, limit=100):
        with self.app.app_context():
            query = AGVTask.query
            if device_id:
                query = query.filter(AGVTask.device_id == device_id)
            if status:
                query = query.filter(AGVTask.status == status)
            limit = self._safe_limit(limit)
            tasks = query.order_by(AGVTask.created_at.desc()).limit(limit).all()
            return [task.to_dict() for task in tasks]

    def get_task(self, task_id):
        with self.app.app_context():
            task = self._query_task(task_id)
            return task.to_dict() if task else None

    def dispatch_task(self, task_id, force=False):
        with self.app.app_context():
            task = self._query_task(task_id)
            if not task:
                raise ValueError('任务不存在')
            if task.status not in ('created', 'failed'):
                raise ValueError(f'任务状态不允许下发: {task.status}')

            if not self._is_car_connected(task.device_id):
                task.error_message = '小车未连接，无法下发任务'
                db.session.commit()
                return {
                    'sent': False,
                    'task': task.to_dict(),
                    'message': task.error_message,
                }

            warning = None
            current = self._get_current_task(task.device_id, exclude_task_id=task.id)
            if current and not force:
                raise ValueError(f"小车正在执行任务 {current.task_no}，请完成或取消后再下发")
            if current and force:
                warning = f"强制下发：小车已有未完成任务 {current.task_no}"

            sent = self.udp_car_service.send_command(task.command_payload, task.device_id) if self.udp_car_service else False
            if sent:
                task.status = 'dispatched'
                task.dispatched_at = datetime.now()
                task.error_message = None
                db.session.commit()
                if self.data_service:
                    self.data_service.save_control_command(
                        task.device_id,
                        'agv_task_dispatch',
                        {
                            'task_id': task.id,
                            'task_no': task.task_no,
                            'template_id': task.template_id,
                            'task_type': task.task_type,
                            'command': task.command_payload,
                        },
                        source='agv_api',
                        is_simulated=False,
                    )
                return {
                    'sent': True,
                    'task': task.to_dict(),
                    'command_payload': task.command_payload,
                    'warning': warning,
                    'message': '任务已下发',
                }

            task.status = 'failed'
            task.error_message = '命令发送失败'
            db.session.commit()
            return {
                'sent': False,
                'task': task.to_dict(),
                'message': task.error_message,
            }

    def create_and_dispatch_task(self, device_id, start_point, end_point, force=False, **kwargs):
        task = self.create_task(device_id, start_point, end_point, **kwargs)
        return self.dispatch_task(task['id'], force=force)

    def update_task_status(self, task_id, status, error_message=None):
        if status not in self.VALID_STATUSES:
            raise ValueError(f'非法任务状态: {status}')
        with self.app.app_context():
            task = self._query_task(task_id)
            if not task:
                raise ValueError('任务不存在')
            task.status = status
            task.error_message = error_message
            if status in ('completed', 'cancelled', 'failed'):
                task.completed_at = datetime.now()
            db.session.commit()
            return task.to_dict()

    def generate_demo_tasks(self, scenario='factory_shift', count=None, device_id=None, auto_dispatch=False):
        template_ids = self.SCENARIOS.get(scenario)
        if not template_ids:
            raise ValueError(f'未知演示场景: {scenario}')
        if count:
            template_ids = template_ids[:self._safe_limit(count, default=len(template_ids), maximum=len(template_ids))]

        created = []
        dispatched = []
        skipped = []
        for index, template_id in enumerate(template_ids):
            template = self.DEMO_TASK_TEMPLATES[template_id]
            assigned_device = device_id or self.assign_device_for_demo_task(index)
            task = self.create_task(
                device_id=assigned_device,
                start_point=template['start_point'],
                end_point=template['end_point'],
                priority=template.get('priority', 0),
                task_type=template['task_type'],
                template_id=template_id,
                title=template['title'],
                description=template['description'],
                source='demo_generator',
            )
            created.append(task)

            if auto_dispatch:
                if self._is_car_connected(assigned_device):
                    try:
                        result = self.dispatch_task(task['id'], force=False)
                        if result.get('sent'):
                            dispatched.append(result)
                        else:
                            skipped.append({
                                'task': task,
                                'reason': result.get('message', '下发失败'),
                            })
                    except ValueError as e:
                        skipped.append({
                            'task': task,
                            'reason': str(e),
                        })
                else:
                    skipped.append({
                        'task': task,
                        'reason': '小车未连接，已创建但未下发',
                    })

        return {
            'scenario': scenario,
            'created': created,
            'dispatched': dispatched,
            'skipped': skipped,
        }

    def dispatch_demo_template(self, template_id, device_id=None, force=False):
        template = self.DEMO_TASK_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f'未知演示任务模板: {template_id}')
        assigned_device = device_id or self.assign_device_for_demo_task(0)
        task = self.create_task(
            device_id=assigned_device,
            start_point=template['start_point'],
            end_point=template['end_point'],
            priority=template.get('priority', 0),
            task_type=template['task_type'],
            template_id=template_id,
            title=template['title'],
            description=template['description'],
            source='demo_generator',
        )
        result = self.dispatch_task(task['id'], force=force)
        result['template'] = template
        return result

    def assign_device_for_demo_task(self, index=0):
        idle_cars = []
        for car in self._get_connected_car_infos():
            device_id = car.get('device_id')
            if not self._get_current_task_dict(device_id):
                idle_cars.append(device_id)
        if idle_cars:
            return idle_cars[index % len(idle_cars)]
        return self.ROBOT_DEVICE_IDS[index % len(self.ROBOT_DEVICE_IDS)]

    def get_agv_status_list(self):
        statuses = []
        seen = set()
        for car in self._get_connected_car_infos():
            device_id = car['device_id']
            statuses.append(self._build_agv_status(device_id, car))
            seen.add(device_id)

        for task in self._list_active_tasks():
            if task['device_id'] not in seen:
                statuses.append(self._build_agv_status(task['device_id'], None, task))
                seen.add(task['device_id'])
        return statuses

    def get_agv_status(self, device_id):
        car_info = None
        for car in self._get_connected_car_infos():
            if car.get('device_id') == device_id:
                car_info = car
                break
        task = self._get_current_task_dict(device_id)
        if not car_info and not task:
            return None
        return self._build_agv_status(device_id, car_info, task)

    def get_dashboard_fleet(self):
        statuses = self.get_agv_status_list()
        if not statuses:
            statuses = [self._build_placeholder_status(i) for i in range(4)]
        elif len(statuses) < 4:
            used = {item['device_id'] for item in statuses}
            for index in range(4):
                if self.ROBOT_DEVICE_IDS[index] not in used:
                    statuses.append(self._build_placeholder_status(index))
                if len(statuses) >= 4:
                    break

        fleet = []
        for index, status in enumerate(statuses[:4]):
            fleet.append(self._to_dashboard_robot(status, index))
        return {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'fleet': fleet,
        }

    def generate_placeholder_path(self, start_point, end_point):
        start = self._get_point(start_point)
        end = self._get_point(end_point)
        if start_point == end_point:
            raise ValueError('起点和终点不能相同')

        waypoints = [self._format_waypoint(start_point, start)]
        if start['x'] != end['x'] and start['y'] != end['y']:
            via = {'x': end['x'], 'y': start['y']}
            waypoints.append(self._format_waypoint('__via_1', via))
        waypoints.append(self._format_waypoint(end_point, end))

        commands = []
        for idx in range(len(waypoints) - 1):
            current = waypoints[idx]
            nxt = waypoints[idx + 1]
            dx = nxt['x'] - current['x']
            dy = nxt['y'] - current['y']
            distance = int(round((dx ** 2 + dy ** 2) ** 0.5))
            if distance <= 0:
                continue
            angle = int(round(degrees(atan2(dy, dx))))
            if angle < 0:
                angle += 360
            commands.append({'d': distance, 'a': angle})

        command_payload = {'carMode': 'path', 'path': commands}
        return {
            'path_waypoints': waypoints,
            'path_commands': commands,
            'command_payload': command_payload,
            'metrics': {
                'distance': sum(item['d'] for item in commands),
                'turn_count': max(0, len(commands) - 1),
                'estimated_time': round(sum(item['d'] for item in commands) / 30.0, 1),
            },
        }

    def _build_agv_status(self, device_id, car_info=None, task=None):
        latest_data = self._get_car_latest_data(device_id) or {}
        current_task = task or self._get_current_task_dict(device_id)
        position = self._extract_position(latest_data, current_task)
        last_receive_time = car_info.get('last_receive_time') if car_info else None
        stale_seconds = self._calc_stale_seconds(last_receive_time)
        return {
            'device_id': device_id,
            'car_ip': car_info.get('car_ip') if car_info else None,
            'car_port': car_info.get('car_port') if car_info else None,
            'connected': bool(car_info and car_info.get('connected')),
            'online': bool(car_info and car_info.get('connected')),
            'last_receive_time': last_receive_time,
            'stale': stale_seconds is not None and stale_seconds > 10,
            'stale_seconds': stale_seconds,
            'work_status': 'busy' if current_task else 'idle',
            'position': position,
            'current_task': self._task_summary(current_task) if current_task else None,
            'task_path': {
                'waypoints': current_task.get('path_waypoints', []) if current_task else [],
                'commands': current_task.get('path_commands', []) if current_task else [],
            } if current_task else None,
            'latest_data': self._latest_data_summary(latest_data),
        }

    def _build_placeholder_status(self, index):
        device_id = self.ROBOT_DEVICE_IDS[index]
        task = self._get_current_task_dict(device_id)
        return self._build_agv_status(device_id, None, task)

    def _to_dashboard_robot(self, status, index):
        latest = status.get('latest_data') or {}
        task = status.get('current_task')
        device_id = status['device_id']
        battery_raw = latest.get('carPower')
        battery_percent, battery_voltage = self._battery_values(battery_raw)
        distance_cm, distance_mm = self._distance_values(latest.get('distance'))
        left_speed = self._to_int(latest.get('L_spd'), 0)
        right_speed = self._to_int(latest.get('R_spd'), 0)
        speed = int(round((abs(left_speed) + abs(right_speed)) / 2))
        car_mode = latest.get('carMode') or ('path' if task else 'manual')
        car_status = latest.get('carStatus') or ('run' if task else 'stop')
        alert_level = self._alert_level(distance_cm, latest)
        position = status.get('position') or {}
        scene = position.get('scene_position') or {'x': 0, 'z': 0}

        return {
            'id': f'robot_{index + 1}',
            'device_id': device_id,
            'name': self.ROBOT_NAMES[index] if index < len(self.ROBOT_NAMES) else device_id,
            'online': status.get('online', False),
            'connected': status.get('connected', False),
            'last_receive_time': status.get('last_receive_time'),
            'status': self._dashboard_status(task, car_mode, car_status, status.get('online', False), alert_level),
            'task': self._dashboard_task(task),
            'mode': car_mode,
            'carMode': car_mode,
            'carStatus': car_status,
            'carSpeed': 'middle',
            'L_spd': left_speed,
            'R_spd': right_speed,
            'speed': speed,
            'battery': battery_percent,
            'batteryPercent': battery_percent,
            'batteryVoltage': battery_voltage,
            'carPowerRaw': battery_raw,
            'distance': distance_cm,
            'distanceCm': distance_cm,
            'distanceMm': distance_mm,
            'goodsCount': 0,
            'alertLevel': alert_level,
            'position': scene,
            'rotation': 0,
            'currentTask': task,
            'path': status.get('task_path'),
        }

    def _dashboard_status(self, task, car_mode, car_status, online, alert_level):
        if alert_level in ('danger', 'critical'):
            return 'warning'
        if not online and not task:
            return 'offline'
        if task and task.get('task_type') == 'charging':
            return 'charging'
        if task:
            return 'pathExecuting'
        if car_mode == 'avoid':
            return 'avoiding'
        if car_mode == 'line':
            return 'lineTracking'
        if car_status == 'run':
            return 'patrolling'
        return 'idle'

    def _dashboard_task(self, task):
        if not task:
            return 'idle'
        task_type = task.get('task_type') or 'materialTransfer'
        if task_type in ('materialTransfer', 'gasMonitor', 'goodsCount', 'smartLighting', 'patrol'):
            return task_type
        if task_type == 'charging':
            return 'idle'
        return 'materialTransfer'

    def _extract_position(self, latest_data, current_task=None):
        for key in ('position', 'pose'):
            pos = latest_data.get(key) if isinstance(latest_data, dict) else None
            if isinstance(pos, dict):
                x = pos.get('x')
                y = pos.get('y', pos.get('z'))
                if x is not None and y is not None:
                    return {
                        'source': key,
                        'x': x,
                        'y': y,
                        'scene_position': {'x': float(x), 'z': float(y)},
                    }

        agv = latest_data.get('agv', {}) if isinstance(latest_data, dict) else {}
        if isinstance(agv, dict) and agv.get('x') is not None and agv.get('y') is not None:
            return {
                'source': 'agv',
                'x': agv.get('x'),
                'y': agv.get('y'),
                'scene_position': self._map_to_scene(agv.get('x'), agv.get('y')),
            }

        if isinstance(latest_data, dict) and latest_data.get('x') is not None and latest_data.get('y') is not None:
            return {
                'source': 'car_xy',
                'x': latest_data.get('x'),
                'y': latest_data.get('y'),
                'scene_position': self._map_to_scene(latest_data.get('x'), latest_data.get('y')),
            }

        if current_task:
            point_id = current_task.get('start_point')
            point = self.POINTS.get(point_id)
            if point:
                return {
                    'source': 'task_start_placeholder',
                    'point': point_id,
                    'x': point['x'],
                    'y': point['y'],
                    'scene_position': point['scene_position'],
                }

        return {
            'source': 'unknown',
            'point': None,
            'x': None,
            'y': None,
            'scene_position': {'x': 0, 'z': 0},
        }

    def _get_connected_car_infos(self):
        if not self.udp_car_service:
            return []
        try:
            return self.udp_car_service.get_connected_cars() or []
        except Exception as e:
            logger.warning(f'获取连接小车列表失败: {e}')
            return []

    def _get_car_latest_data(self, device_id):
        if not self.udp_car_service or not hasattr(self.udp_car_service, 'cars'):
            return None
        try:
            with self.udp_car_service.cars_lock:
                car = self.udp_car_service.cars.get(device_id)
                return dict(car.latest_data) if car and isinstance(car.latest_data, dict) else None
        except Exception as e:
            logger.warning(f'获取小车最新数据失败: {device_id} {e}')
            return None

    def _is_car_connected(self, device_id):
        if not self.udp_car_service or not hasattr(self.udp_car_service, 'cars'):
            return False
        try:
            with self.udp_car_service.cars_lock:
                car = self.udp_car_service.cars.get(device_id)
                return bool(car and car.connected)
        except Exception:
            return False

    def _get_current_task(self, device_id, exclude_task_id=None):
        query = AGVTask.query.filter(
            AGVTask.device_id == device_id,
            AGVTask.status.in_(self.ACTIVE_STATUSES)
        )
        if exclude_task_id:
            query = query.filter(AGVTask.id != exclude_task_id)
        return query.order_by(AGVTask.created_at.desc()).first()

    def _get_current_task_dict(self, device_id):
        with self.app.app_context():
            task = self._get_current_task(device_id)
            return task.to_dict() if task else None

    def _list_active_tasks(self):
        with self.app.app_context():
            tasks = AGVTask.query.filter(AGVTask.status.in_(self.ACTIVE_STATUSES)) \
                .order_by(AGVTask.created_at.desc()).all()
            return [task.to_dict() for task in tasks]

    def _query_task(self, task_id):
        if isinstance(task_id, str) and not task_id.isdigit():
            return AGVTask.query.filter(AGVTask.task_no == task_id).first()
        return AGVTask.query.get(int(task_id))

    def _get_point(self, point_id):
        point = self.POINTS.get(point_id)
        if not point:
            raise ValueError(f'未知点位: {point_id}')
        return point

    def _format_waypoint(self, point_id, point):
        waypoint = {
            'point': point_id,
            'x': point['x'],
            'y': point['y'],
            'unit': self.POINT_UNIT,
            'scene_position': point.get('scene_position') or self._map_to_scene(point['x'], point['y']),
        }
        if point_id in self.POINTS:
            waypoint['name'] = self.POINTS[point_id].get('name')
            waypoint['type'] = self.POINTS[point_id].get('type')
        return waypoint

    def _map_to_scene(self, x, y):
        try:
            return {
                'x': round(-11 + float(x) / 100.0 * 22, 2),
                'z': round(-7 + float(y) / 100.0 * 14, 2),
            }
        except Exception:
            return {'x': 0, 'z': 0}

    def _latest_data_summary(self, data):
        if not data:
            return {}
        keys = ('carStatus', 'carMode', 'L_spd', 'R_spd', 'carPower', 'distance', 'timestamp')
        return {key: data.get(key) for key in keys if key in data}

    def _task_summary(self, task):
        if not task:
            return None
        return {
            'id': task.get('id'),
            'task_no': task.get('task_no'),
            'device_id': task.get('device_id'),
            'task_type': task.get('task_type'),
            'template_id': task.get('template_id'),
            'title': task.get('title'),
            'description': task.get('description'),
            'source': task.get('source'),
            'start_point': task.get('start_point'),
            'end_point': task.get('end_point'),
            'status': task.get('status'),
            'priority': task.get('priority'),
            'created_at': task.get('created_at'),
            'dispatched_at': task.get('dispatched_at'),
        }

    def _battery_values(self, raw):
        if raw is None:
            return 80, None
        raw_int = self._to_int(raw, 80)
        if 0 <= raw_int <= 100:
            return raw_int, raw_int
        percent = int(round((raw_int - 6500) / 1900 * 100))
        percent = max(0, min(100, percent))
        return percent, raw_int

    def _distance_values(self, raw):
        if raw is None:
            return 60, 600
        raw_int = self._to_int(raw, 60)
        if raw_int > 200:
            return int(round(raw_int / 10)), raw_int
        return raw_int, raw_int * 10

    def _alert_level(self, distance_cm, latest):
        if latest.get('gasStatus') == 1:
            return 'danger'
        if distance_cm is not None and distance_cm <= 15:
            return 'danger'
        if distance_cm is not None and distance_cm <= 30:
            return 'warning'
        return 'normal'

    def _calc_stale_seconds(self, last_receive_time):
        if not last_receive_time:
            return None
        try:
            ts = datetime.fromisoformat(last_receive_time)
            return int((datetime.now() - ts).total_seconds())
        except Exception:
            return None

    def _default_task_title(self, start_point, end_point):
        start_name = self.POINTS.get(start_point, {}).get('name', start_point)
        end_name = self.POINTS.get(end_point, {}).get('name', end_point)
        return f'AGV任务：{start_name} → {end_name}'

    def _generate_task_no(self):
        return 'AGV' + datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]

    def _safe_limit(self, value, default=100, maximum=500):
        try:
            limit = int(value)
        except Exception:
            limit = default
        return max(1, min(maximum, limit))

    def _to_int(self, value, default=0):
        try:
            return int(float(value))
        except Exception:
            return default
