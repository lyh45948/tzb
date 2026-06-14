"""
数字孪生大屏 SSE 推送服务

用法：
    stream = DashboardStreamService(dashboard_service, interval=1.0, heartbeat=15)
    stream.start()
    ...
    # 路由层
    q = stream.subscribe()
    return Response(stream.event_stream(q), mimetype='text/event-stream')

设计要点：
- 后台单线程定时调 DashboardService.get_snapshot()，把结果广播给所有订阅队列。
- 每个 HTTP 长连接对应一个 queue.Queue，放入 (event_name, payload) 元组；
  生成器侧按 SSE 文本格式输出，连接断开时由路由层调用 unsubscribe() 清理。
- 心跳：超过 heartbeat 秒没有产生新快照（或客户端长时间无消息），主动发 ping，
  防止反向代理或浏览器把空闲连接当成超时。
"""
import json
import queue
import threading
import time

from app.utils.logger import get_logger

logger = get_logger('dashboard_stream')


class DashboardStreamService:
    """通过 SSE 周期性广播 dashboard 快照"""

    def __init__(self, dashboard_service, interval=1.0, heartbeat=15):
        self.dashboard_service = dashboard_service
        self.interval = max(0.2, float(interval))
        self.heartbeat = max(5, int(heartbeat))
        self._subscribers = set()
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    # ─── 生命周期 ───
    def start(self):
        if self._running:
            return
        if self.dashboard_service is None:
            logger.warning('DashboardService 未注入，SSE 推送不会启动')
            return
        self._running = True
        self._thread = threading.Thread(target=self._broadcast_loop,
                                        name='dashboard_stream', daemon=True)
        self._thread.start()
        logger.info(f'Dashboard SSE 服务已启动 (interval={self.interval}s, heartbeat={self.heartbeat}s)')

    def stop(self):
        self._running = False
        # 给所有订阅者投个 None，让生成器尽快退出
        with self._lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(None)
                except Exception:
                    pass
            self._subscribers.clear()

    # ─── 订阅管理 ───
    def subscribe(self):
        """注册一个新订阅者，返回其消息队列"""
        q = queue.Queue(maxsize=8)
        with self._lock:
            self._subscribers.add(q)
        logger.debug(f'SSE 新订阅者，当前 {len(self._subscribers)} 个')
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subscribers.discard(q)
        logger.debug(f'SSE 订阅者断开，剩余 {len(self._subscribers)} 个')

    # ─── 后台广播线程 ───
    def _broadcast_loop(self):
        next_tick = time.time()
        while self._running:
            try:
                snapshot = self.dashboard_service.get_snapshot()
                payload = ('snapshot', snapshot)
                self._fanout(payload)
            except Exception as e:
                logger.warning(f'生成快照失败: {e}')

            # 等待到下一个 tick；用 sleep 累计避免漂移
            next_tick += self.interval
            sleep_for = next_tick - time.time()
            if sleep_for < 0:
                # 落后了，直接对齐到现在
                next_tick = time.time()
                sleep_for = 0
            time.sleep(sleep_for)

    def _fanout(self, payload):
        """把消息投递给所有订阅队列；满了就丢这一帧"""
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(payload)
            except queue.Full:
                # 客户端消费跟不上，丢一帧总比阻塞整条链路好
                pass

    # ─── 给路由层的 SSE 生成器 ───
    def event_stream(self, q):
        """供 Flask Response 使用的生成器，输出 SSE 文本帧"""
        # 连接建立时先发一帧当前快照，避免前端空白等待 interval
        try:
            snapshot = self.dashboard_service.get_snapshot()
            yield self._format_event('snapshot', snapshot)
        except Exception as e:
            logger.debug(f'初始快照生成失败: {e}')

        last_send = time.time()
        try:
            while True:
                try:
                    item = q.get(timeout=self.heartbeat)
                except queue.Empty:
                    # 心跳防止代理/浏览器关闭空闲连接
                    yield self._format_event('ping', {'t': int(time.time() * 1000)})
                    last_send = time.time()
                    continue

                if item is None:
                    # 服务停止信号
                    break
                event_name, data = item
                yield self._format_event(event_name, data)
                last_send = time.time()
        finally:
            self.unsubscribe(q)

    @staticmethod
    def _format_event(event, data):
        try:
            payload = json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            payload = '{}'
        return f'event: {event}\ndata: {payload}\n\n'
