import sys
import os
import psutil
import subprocess

def cleanup_processes():
    """全局进程清理函数，只清理当前进程的直接子进程"""
    try:
        # 获取当前进程ID
        current_pid = os.getpid()
        
        # 只终止当前进程的直接子进程
        terminated_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'ppid']):
            try:
                # 只终止当前进程的直接子进程
                if proc.info['ppid'] == current_pid:
                    proc_pid = proc.info['pid']
                    try:
                        proc.terminate()
                        proc.wait(timeout=2)
                        terminated_count += 1
                    except psutil.TimeoutExpired:
                        proc.kill()
                        terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # 不再终止所有Eagle相关的exe进程，避免过于激进的清理
    except Exception:
        # 静默处理异常，避免在退出时显示错误
        pass

# 注册全局退出处理函数
import atexit
atexit.register(cleanup_processes)