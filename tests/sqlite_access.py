# -*- coding: utf-8 -*-
"""
Una base SQLite que entiende lo justo del dialecto de Access que usan los
modulos, para que las pruebas ejecuten su SQL de verdad y no contra un doble
que lo acepta todo.
"""

import re
import sqlite3


class DBAccessEnSqlite:

    def __init__(self):
        self.cn = sqlite3.connect(':memory:')
        self.cn.row_factory = sqlite3.Row
        # Funciones de Access que usa el SQL de los modulos
        self.cn.create_function('YEAR', 1, lambda v: int(str(v)[:4]) if v else None)

    @staticmethod
    def _traducir(sql):
        sql = re.sub(r'COUNTER PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql)
        sql = re.sub(r'AUTOINCREMENT PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql)
        sql = re.sub(r'TEXT\(\d+\)', 'TEXT', sql)
        sql = re.sub(r'#(\d\d)/(\d\d)/(\d{4}) ([\d:]+)#', r"'\3-\1-\2 \4'", sql)
        sql = re.sub(r'#(\d\d)/(\d\d)/(\d{4})#', r"'\3-\1-\2'", sql)
        sql = re.sub(r'\bTrue\b', '1', sql)
        sql = re.sub(r'\bFalse\b', '0', sql)
        top = re.search(r'SELECT TOP (\d+) ', sql)
        if top:
            sql = sql.replace(top.group(0), 'SELECT ', 1) + ' LIMIT %s' % top.group(1)
        return sql

    def execute(self, sql):
        cur = self.cn.execute(self._traducir(sql))
        self.cn.commit()
        return cur

    def query(self, sql):
        return [dict(r) for r in self.cn.execute(self._traducir(sql)).fetchall()]

    def query_one(self, sql):
        filas = self.query(sql)
        return filas[0] if filas else None

    def insert(self, tabla, datos):
        """Como Database.insert de ANgesLAB.pyw: arma el INSERT con los valores."""
        from modulos.compras import _sql
        cols = ', '.join('[%s]' % k for k in datos)
        vals = ', '.join(_sql(v) for v in datos.values())
        self.execute('INSERT INTO [%s] (%s) VALUES (%s)' % (tabla, cols, vals))
