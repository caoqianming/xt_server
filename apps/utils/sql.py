from django.db import connection
from django.utils import timezone
from datetime import datetime

def execute_raw_sql(sql: str, params=None, timeout=30):
    """执行原始sql并返回rows, columns数据

    Args:
        sql (str): 查询语句
        params (_type_, optional): 参数列表. Defaults to None.
    """
    with connection.cursor() as cursor:
        cursor.execute(f"SET statement_timeout TO '{int(timeout*1000)}ms';")
        if params:
            cursor.execute(sql, params=params)
        else:
            cursor.execute(sql)
        if cursor.description:
            columns  = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return columns, rows
        return [], []
    
def format_sqldata(columns, rows):
    return [columns] + rows, [dict(zip(columns, row)) for row in rows]


def query_all_dict(sql, params=None, with_time_format=False):
    '''
    查询所有结果返回字典类型数据
    :param sql:
    :param params:
    :return:
    '''
    with connection.cursor() as cursor:
        if params:
            cursor.execute(sql, params=params)
        else:
            cursor.execute(sql)
        columns  = [desc[0] for desc in cursor.description]
        if with_time_format:
            results = []
            for row in cursor.fetchall():
                row_dict = {}
                for col, val in zip(columns, row):
                    if isinstance(val, datetime):
                        val = timezone.make_naive(val).strftime("%Y-%m-%d %H:%M:%S")
                    row_dict[col] = val
                results.append(row_dict)
            return results
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def query_one_dict(sql, params=None, with_time_format=False):
    """
    查询一个结果返回字典类型数据
    :param sql:
    :param params:
    :return:
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or ())  # 更简洁的参数处理
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        if with_time_format:
            row_dict = {}
            for col, val in zip(columns, row):
                if isinstance(val, datetime):
                    val = timezone.make_naive(val).strftime("%Y-%m-%d %H:%M:%S")
                row_dict[col] = val
            return row_dict
        return dict(zip(columns, row)) if row else None  # 安全处理None情况
    
import pymysql
import psycopg2

class DbConnection:
    def __init__(self, host, user, password, database, dbtype='mysql'):
        if dbtype not in ['mysql', 'pg']:
            raise ValueError('dbtype must be mysql or pg')
        self.dbtype = dbtype
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None

    def _connect(self):
        if self.dbtype == 'mysql':
            return pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
        elif self.dbtype == 'pg':
            return psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
            )

    def __enter__(self):
        self.conn = self._connect()
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
