from contextlib import contextmanager
from rest_framework.exceptions import ParseError
from functools import wraps
from django.db import transaction

@contextmanager
def lock_model_record(model_class, pk):
    """
    Locks a model instance and returns it.
    """
    try:
        instance = model_class.objects.select_for_update().get(pk=pk)
        yield instance
    except model_class.DoesNotExist:
        raise ParseError("该记录不存在或已被删除")

def lock_model_record_d_func(model_class, pk_attr='id'):
    """
    通用模型锁装饰器（内置事务），用于装饰函数
    """
    def decorator(func):
        @wraps(func)
        @transaction.atomic
        def wrapper(old_instance, *args, **kwargs):
            try:
                # 获取新鲜记录
                fresh_record = model_class.objects.select_for_update().get(pk=getattr(old_instance, pk_attr))
                # 调用原函数，但传入新鲜记录
                return func(fresh_record, *args, **kwargs)
            except model_class.DoesNotExist:
                raise ParseError('记录不存在或已被删除')
        return wrapper
    return decorator

def lock_model_record_d_method(model_class, pk_attr='id'):
    """
    通用模型锁装饰器（内置事务）, 用于装饰类方法
    """
    def decorator(func):
        @wraps(func)
        @transaction.atomic
        def wrapper(self, old_instance, *args, **kwargs):
            try:
                # 获取新鲜记录
                fresh_record = model_class.objects.select_for_update().get(pk=getattr(old_instance, pk_attr))
                # 调用原函数，但传入新鲜记录
                return func(self, fresh_record, *args, **kwargs)
            except model_class.DoesNotExist:
                raise ParseError('记录不存在或已被删除')
        return wrapper
    return decorator