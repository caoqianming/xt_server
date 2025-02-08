import psutil
from server.celery import celery_inspect
from django_redis import get_redis_connection

class ServerService:
    @classmethod
    def get_memory_dict(cls):
        ret = {}
        memory = psutil.virtual_memory()
        ret['total'] = round(memory.total/1024/1024/1024, 2)
        ret['used'] = round(memory.used/1024/1024/1024, 2)
        ret['percent'] = memory.percent
        return ret

    @classmethod
    def get_cpu_dict(cls):
        ret = {}
        ret['lcount'] = psutil.cpu_count()
        ret['count'] = psutil.cpu_count(logical=False)
        ret['percent'] = psutil.cpu_percent(interval=1)
        return ret
    
    @classmethod
    def get_disk_dict(cls):
        ret = {}
        disk = psutil.disk_usage('/')
        ret['total'] = round(disk.total/1024/1024/1024, 2)
        ret['used'] = round(disk.used/1024/1024/1024, 2)
        ret['percent'] = disk.percent
        return ret

    @classmethod
    def get_full(cls):
        return {'cpu': cls.get_cpu_dict(), 'memory': cls.get_memory_dict(), 'disk': cls.get_disk_dict()}


class CeleryMonitor:
    @classmethod
    def get_info(cls):
        count_active_task = 0
        count_scheduled_task = 0
        count_registered_task = 0
        active_tasks = celery_inspect.active()
        if active_tasks:
            _, first_value = active_tasks.popitem()
            count_active_task = len(first_value)
        scheduled_tasks = celery_inspect.scheduled()
        if scheduled_tasks:
            _, first_value = scheduled_tasks.popitem()
            count_scheduled_task = len(first_value)
        registered_tasks = celery_inspect.registered()
        if registered_tasks:
            _, first_value = registered_tasks.popitem()
            count_registered_task = len(first_value)
        return {
            'count_active_task': count_active_task,
            'count_scheduled_task': count_scheduled_task,
            'count_registered_task': count_registered_task,
        }

class RedisMonitor:
    @classmethod
    def get_info(cls):
        conn = get_redis_connection()
        return conn.info()