import os
import hashlib
from PyQt5.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

class FileScanner(QThread):
    progress_updated = pyqtSignal(int)
    scan_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, directory, extensions, db_manager):
        super().__init__()
        self.directory = directory
        self.extensions = extensions
        self.db_manager = db_manager
        
    def get_file_md5(self, filepath):
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            print(f"计算MD5出错 {filepath}: {str(e)}")
            return None
        
    def scan_directory(self):
        all_files = []
        try:
            for root, _, files in os.walk(self.directory):
                for file in files:
                    try:
                        if any(file.lower().endswith(ext) for ext in self.extensions):
                            full_path = os.path.join(root, file)
                            # 检查文件是否可访问
                            if os.path.exists(full_path) and os.access(full_path, os.R_OK):
                                all_files.append(full_path)
                    except Exception as e:
                        print(f"处理文件出错 {file}: {str(e)}")
                        continue
        except Exception as e:
            self.error_occurred.emit(f"扫描目录出错: {str(e)}")
            return []
        return all_files
        
    def process_file(self, filepath):
        try:
            file_size = os.path.getsize(filepath)
            md5 = self.get_file_md5(filepath)
            return filepath, file_size, md5
        except Exception as e:
            print(f"处理文件失败 {filepath}: {str(e)}")
            return None
        
    def run(self):
        try:
            files_dict = {}
            total_size = 0
            duplicate_size = 0
            
            # 获取所有符合条件的文件
            all_files = self.scan_directory()
            if not all_files:
                self.error_occurred.emit("未找到符合条件的文件")
                return
                
            total_files = len(all_files)
            processed_files = 0
            
            # 使用线程池计算MD5
            with ThreadPoolExecutor(max_workers=4) as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(self.process_file, filepath): filepath 
                    for filepath in all_files
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_file):
                    processed_files += 1
                    self.progress_updated.emit(int(processed_files * 100 / total_files))
                    
                    result = future.result()
                    if result is None:
                        continue
                        
                    filepath, file_size, md5 = result
                    if md5 is None:
                        continue
                        
                    if md5 in files_dict:
                        files_dict[md5].append(filepath)
                        duplicate_size += file_size
                    else:
                        files_dict[md5] = [filepath]
                        total_size += file_size
                
            # 将结果保存到数据库
            self.db_manager.save_scan_results(files_dict)
            
            # 生成统计信息
            duplicate_count = sum(len(files) - 1 for files in files_dict.values() if len(files) > 1)
            stats = f'''扫描完成！
总文件数：{total_files}
重复文件数：{duplicate_count}
总文件大小：{total_size / 1024 / 1024:.2f} MB
可节省空间：{duplicate_size / 1024 / 1024:.2f} MB'''
            
            self.scan_completed.emit(stats)
            
        except Exception as e:
            error_msg = f"扫描过程出错: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
        finally:
            # 关闭当前线程的数据库连接
            self.db_manager.close_connection() 