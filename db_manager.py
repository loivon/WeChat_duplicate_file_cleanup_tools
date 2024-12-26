import sqlite3
import os
import threading

class DatabaseManager:
    def __init__(self):
        self.db_path = 'wechat_files.db'
        self.thread_local = threading.local()
        # 在主线程创建表
        self._get_conn().close()
        
    def _get_conn(self):
        # 创建新的连接
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            md5 TEXT,
            filepath TEXT,
            is_duplicate BOOLEAN
        )
        ''')
        conn.commit()
        return conn
        
    def get_connection(self):
        # 为每个线程获取独立的数据库连接
        if not hasattr(self.thread_local, 'connection'):
            self.thread_local.connection = self._get_conn()
        return self.thread_local.connection
        
    def save_scan_results(self, files_dict):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM files')  # 清空旧数据
            
            for md5, filepaths in files_dict.items():
                # 第一个文件保留，其余标记为重复
                cursor.execute('INSERT INTO files (md5, filepath, is_duplicate) VALUES (?, ?, ?)',
                             (md5, filepaths[0], False))
                
                for filepath in filepaths[1:]:
                    cursor.execute('INSERT INTO files (md5, filepath, is_duplicate) VALUES (?, ?, ?)',
                                 (md5, filepath, True))
                    
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        
    def delete_duplicates(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT filepath FROM files WHERE is_duplicate = 1')
            
            for (filepath,) in cursor.fetchall():
                try:
                    os.remove(filepath)
                except OSError as e:
                    print(f"无法删除文件: {filepath}: {str(e)}")
                    
            cursor.execute('DELETE FROM files WHERE is_duplicate = 1')
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        
    def close_connection(self):
        if hasattr(self.thread_local, 'connection'):
            self.thread_local.connection.close()
            del self.thread_local.connection 