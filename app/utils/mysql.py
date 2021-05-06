import logging
import pymysql
import time
from dbutils.pooled_db import PooledDB

logger = logging.getLogger(__name__)

class MysqlPool():
    def __init__(self,host,port,user,password,db):
        self.POOL=PooledDB(
            creator=pymysql,
            maxconnections=10,
            mincached=3,
            maxcached=5,
            blocking=True,
            host=host,
            port=port,
            user=user,
            password=password,
            database=db,
            charset='utf8'
        )
    
    
    def connect(self):
        """
        启动连接
        """
        conn=self.POOL.connection()
        cursor=conn.cursor(cursor=pymysql.cursors.DictCursor)
        return conn,cursor
    
    def closeConn(self,conn,cursor):
        cursor.close()
        conn.close()
    
    def fetchOne(self,sqlStr,args):
        """
        查询一条
        """
        logger.info("%s,args:%s",sqlStr,args)
        result=None
        try:
            conn,cursor=self.connect()
            cursor.execute(sqlStr,args)
            result=cursor.fetchone()
        except Exception as e:
            logger.error("fetchOne error",exc_info=True)
        finally:
            self.closeConn(conn,cursor)
            return result
    
    def fetchAll(self,sqlStr,args):
        """
        查询所有数据
        """
        logger.info("%s,args:%s",sqlStr,args)
        result=None
        try:
            conn,cursor=self.connect()
            cursor.execute(sqlStr,args)
            result=cursor.fetchall()
        except Exception as e:
            logger.error("fetchAll error",exc_info=True)
        finally:
            self.closeConn(conn,cursor)
            return result
    
    def insert(self,sqlStr,args):
        """
        插入数据
        """
        logger.info("%s,args:%s",sqlStr,args)
        row=0
        try:
            conn, cursor = self.connect()
            row = cursor.execute(sqlStr, args)
            logger.info("insert %s records!",row)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("insert error",exc_info=True)
        finally:
            self.closeConn(conn, cursor)
            return row
        