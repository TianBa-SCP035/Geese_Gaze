import os
import sys
import json
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from PIL import Image, ImageTk
import requests
import cv2
import platform
import random
import string

# 导入我们的模块
from cut import TubePlateProcessor
from QR import process_qr_codes
from DM import process_dm_codes

# 资源路径处理函数
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe
    application_path = os.path.dirname(sys.executable)
    def get_resource_path(relative_path):
        """获取打包后的资源路径"""
        try:
            # PyInstaller创建一个临时文件夹，并将路径存储在_MEIPASS中
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
else:
    # 如果是脚本运行
    application_path = os.path.dirname(os.path.abspath(__file__))
    def get_resource_path(relative_path):
        """获取开发环境下的资源路径"""
        return os.path.join(application_path, relative_path)

class GeeseUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Geese Gaze 监控系统")
        self.root.geometry("1100x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 初始化变量
        self.monitoring = True
        self.auto_send = True  # 自动发送开关
        self.qr_results = {}
        self.server_url = "http://172.16.1.141:10511/apiEntitySample/GetSampleScanData.json"  # 默认后端接口地址
        self.watch_dir = "picture"  # 默认监控文件夹路径
        self.processing_lock = threading.Lock()  # 图片处理互斥锁
        self.code_mode = "DM"  # 识别模式：QR或DM
        
        # 孔版行列数
        self.rows = 9
        self.cols = 9
        self.machine_code = 1
        
        # 图标引用（防止被垃圾回收）
        self._icon_photo = None
        
        # 设置窗口图标（在创建UI组件之前设置，确保图标稳定显示）
        self.set_window_icon()
        
        # 初始化处理器为None，稍后创建
        self.processor = None
        
        # 创建UI组件（包含log_text）
        self.create_widgets()
        
        # 加载配置
        self.load_config()
        
        # 创建处理器
        self._reset_processor_with_template(self.get_template_path())
        
        # 检查模板是否存在
        self.check_template()
        
        # 如果监控状态为True，则启动监控线程
        if self.monitoring:
            self.log("启动监控...")
            monitor_thread = threading.Thread(target=self.monitor_directory)
            monitor_thread.daemon = True
            monitor_thread.start()
    
    def get_template_path(self):
        """根据当前行列数生成模板文件名"""
        return f"template_{self.rows}x{self.cols}.json"
    
    def _reset_processor_with_template(self, template_path):
        """重置处理器并同步行列数和标签"""
        self.processor = TubePlateProcessor(template_path)
        self.processor.rows = self.rows
        self.processor.cols = self.cols
        if hasattr(self.processor, "_generate_labels"):
            self.processor.labels = self.processor._generate_labels()
        
    def create_widgets(self):
        """创建UI组件"""
        # 创建主内容区域（左右两列）
        main_content = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧：模板控制、日志、孔版大小、统计信息
        left_frame = ttk.Frame(main_content)
        main_content.add(left_frame, weight=1)
        
        # 模板相关按钮
        template_frame = ttk.LabelFrame(left_frame, text="模板控制", padding="10")
        template_frame.pack(fill=tk.X, pady=5)
        
        self.template_status_var = tk.StringVar(value="检查模板中...")
        ttk.Label(template_frame, textvariable=self.template_status_var).pack(side=tk.LEFT, padx=5)
        
        self.recalibrate_btn = ttk.Button(template_frame, text="重新画模板", command=self.recalibrate_template)
        self.recalibrate_btn.pack(side=tk.LEFT, padx=5)
        
        # 处理单张图片按钮
        self.process_single_btn = ttk.Button(template_frame, text="处理单张图片", command=self.process_single_image)
        self.process_single_btn.pack(side=tk.LEFT, padx=5)
        
        # 接口地址按钮
        self.server_url_btn = ttk.Button(template_frame, text="接口地址", command=self.change_server_url)
        self.server_url_btn.pack(side=tk.LEFT, padx=5)
        
        # 机器码按钮
        self.machine_code_btn = ttk.Button(template_frame, text="机器码", command=self.change_machine_code)
        self.machine_code_btn.pack(side=tk.LEFT, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(left_frame, text="执行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=18)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 孔版大小选择
        size_frame = ttk.LabelFrame(left_frame, text="孔版大小", padding="10")
        size_frame.pack(fill=tk.X, pady=5)
        
        # 行数选择
        size_inner_frame = ttk.Frame(size_frame)
        size_inner_frame.pack(fill=tk.X, expand=True)
        
        ttk.Label(size_inner_frame, text="行数:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.rows_var = tk.IntVar(value=self.rows)
        rows_spinbox = ttk.Spinbox(size_inner_frame, from_=1, to=20, textvariable=self.rows_var, width=10, state="readonly")
        rows_spinbox.grid(row=0, column=1, padx=5, pady=2)
        
        # 列数选择
        ttk.Label(size_inner_frame, text="列数:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.cols_var = tk.IntVar(value=self.cols)
        cols_spinbox = ttk.Spinbox(size_inner_frame, from_=1, to=20, textvariable=self.cols_var, width=10, state="readonly")
        cols_spinbox.grid(row=0, column=3, padx=5, pady=2)
        
        # 应用按钮
        apply_button = ttk.Button(size_inner_frame, text="应用", command=self.apply_plate_size)
        apply_button.grid(row=0, column=4, padx=5, pady=2)
        
        # QR/DM切换按钮
        self.code_mode_btn = ttk.Button(size_inner_frame, text="DM码", command=self.toggle_code_mode)
        self.code_mode_btn.grid(row=0, column=5, padx=5, pady=2)
        
        # 统计信息区域
        stats_frame = ttk.LabelFrame(left_frame, text="统计信息", padding="10")
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 添加手动发送按钮
        send_frame = ttk.Frame(stats_frame)
        send_frame.pack(fill=tk.X, pady=5)
        
        self.send_btn = ttk.Button(send_frame, text="发送结果", command=self.send_results)
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        self.send_status_var = tk.StringVar(value="未发送")
        ttk.Label(send_frame, textvariable=self.send_status_var).pack(side=tk.LEFT, padx=5)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, wrap=tk.WORD, height=18)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：监控控制、二维码映射、可视化
        right_frame = ttk.Frame(main_content)
        main_content.add(right_frame, weight=1)
        
        # 监控控制按钮
        monitor_frame = ttk.LabelFrame(right_frame, text="监控控制", padding="10")
        monitor_frame.pack(fill=tk.X, pady=5)
        
        self.monitor_btn = ttk.Button(monitor_frame, text="停止监控", command=self.toggle_monitoring)
        self.monitor_btn.pack(side=tk.LEFT, padx=5)
        
        # 重新选择监控文件夹按钮
        self.select_dir_btn = ttk.Button(monitor_frame, text="选择监控文件夹", command=self.select_monitor_directory)
        self.select_dir_btn.pack(side=tk.LEFT, padx=5)
        
        # 自动发送按钮
        self.auto_send_btn = ttk.Button(monitor_frame, text="禁用自动发送", command=self.toggle_auto_send)
        self.auto_send_btn.pack(side=tk.LEFT, padx=5)
        
        # 显示当前监控文件夹路径
        self.monitor_dir_label = ttk.Label(monitor_frame, text=f"监控文件夹: {self.watch_dir}")
        self.monitor_dir_label.pack(side=tk.LEFT, padx=5)
        
        # 二维码映射区域
        map_frame = ttk.LabelFrame(right_frame, text="二维码映射", padding="10")
        map_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.map_text = scrolledtext.ScrolledText(map_frame, wrap=tk.WORD, height=18)
        self.map_text.pack(fill=tk.BOTH, expand=True)
        
        # 可视化区域
        viz_frame = ttk.LabelFrame(right_frame, text="结果可视化", padding="10")
        viz_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建matplotlib图形
        self.fig, self.ax = plt.subplots(figsize=(3.6, 3.6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="监控运行中...")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def ensure_watch_dir_exists(self):
        """确保监控文件夹存在，如果不存在则创建"""
        if not os.path.exists(self.watch_dir):
            os.makedirs(self.watch_dir)
            self.log(f"已创建监控文件夹: {self.watch_dir}")
    
    def load_config(self):
        """从config.json加载配置"""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
                
                # 加载接口地址
                if "server_url" in config:
                    self.server_url = config["server_url"]
                    self.log(f"已加载接口地址: {self.server_url}")
                
                # 加载监控文件夹路径
                if "watch_dir" in config:
                    self.watch_dir = config["watch_dir"]
                    self.monitor_dir_label.config(text=f"监控文件夹: {self.watch_dir}")
                    self.log(f"已加载监控文件夹: {self.watch_dir}")
                    
                    # 确保监控文件夹存在
                    self.ensure_watch_dir_exists()
                
                # 加载孔版行列数
                self.rows = config.get('rows', 9)
                self.cols = config.get('cols', 9)
                
                # 加载机器码
                self.machine_code = config.get('machine_code', 1)
                
                # 更新UI控件的值
                self.rows_var.set(self.rows)
                self.cols_var.set(self.cols)
                
                self.log(f"孔版布局: {self.rows}行 x {self.cols}列")
                self.log(f"机器码: {self.machine_code}")
            else:
                # 使用默认配置
                self.rows = 9
                self.cols = 9
                self.machine_code = 1
                
                # 更新UI控件的值
                self.rows_var.set(self.rows)
                self.cols_var.set(self.cols)
                
                self.log("使用默认配置")
                self.log(f"孔版布局: {self.rows}行 x {self.cols}列")
                self.log(f"机器码: {self.machine_code}")
        except Exception as e:
            self.log(f"加载配置失败: {e}")
            # 使用默认配置
            self.rows = 9
            self.cols = 9
            self.machine_code = 1
            
            # 更新UI控件的值
            self.rows_var.set(self.rows)
            self.cols_var.set(self.cols)
            
            self.log("使用默认配置")
            self.log(f"孔版布局: {self.rows}行 x {self.cols}列")
            self.log(f"机器码: {self.machine_code}")
    
    def save_config(self):
        """保存配置到config.json"""
        try:
            # 读取现有的config.json
            config = {}
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
            
            # 更新配置
            config["server_url"] = self.server_url
            config["watch_dir"] = self.watch_dir
            config["rows"] = self.rows
            config["cols"] = self.cols
            config["machine_code"] = self.machine_code
            
            # 保存配置
            with open("config.json", "w") as f:
                json.dump(config, f, indent=2)
                
            self.log("配置已保存")
        except Exception as e:
            self.log(f"保存配置失败: {e}")
    
    def change_server_url(self):
        """修改后端接口地址"""
        # 创建一个对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("设置接口地址")
        dialog.geometry("500x170")
        dialog.resizable(False, False)
        
        # 使对话框模态
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 创建界面元素
        ttk.Label(dialog, text="后端接口地址:").pack(pady=10, padx=10, anchor=tk.W)
        
        url_frame = ttk.Frame(dialog)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        
        url_var = tk.StringVar(value=self.server_url)
        url_entry = ttk.Entry(url_frame, textvariable=url_var, width=50)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        url_entry.select_range(0, tk.END)  # 选中文本
        
        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_url():
            new_url = url_var.get().strip()
            if new_url:
                self.server_url = new_url
                self.log(f"接口地址已更新为: {new_url}")
                # 保存配置
                self.save_config()
                dialog.destroy()
            else:
                messagebox.showwarning("警告", "接口地址不能为空")
        
        ttk.Button(button_frame, text="保存", command=save_url).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 聚焦到输入框
        url_entry.focus_set()
        
        # 等待对话框关闭
        self.root.wait_window(dialog)
    
    def change_machine_code(self):
        """修改机器码"""
        # 创建一个对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("设置机器码")
        dialog.geometry("350x170")
        dialog.resizable(False, False)
     
        # 使对话框模态
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 创建界面元素
        ttk.Label(dialog, text="机器码:").pack(pady=10, padx=10, anchor=tk.W)
        
        # 机器码选择框架
        code_frame = ttk.Frame(dialog)
        code_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 减号按钮
        def decrease_code():
            try:
                current = int(machine_code_var.get())
                if current > 1:  # 限制最小值为1
                    machine_code_var.set(str(current - 1))
            except ValueError:
                # 如果当前值不是有效数字，设为1
                machine_code_var.set("1")
        
        minus_btn = ttk.Button(code_frame, text="-", command=decrease_code, width=3)
        minus_btn.pack(side=tk.LEFT, padx=5)
        
        # 机器码值显示 - 修改为可编辑状态，限制只能输入数字且不超过10位
        machine_code_var = tk.StringVar(value=str(self.machine_code))
        code_entry = ttk.Entry(code_frame, textvariable=machine_code_var, width=10, justify='center')
        code_entry.pack(side=tk.LEFT, padx=5)
        
        # 验证输入，确保只能输入数字且不超过10位
        def validate_input(new_text):
            # 如果为空，返回True（允许删除所有内容）
            if not new_text:
                return True
            
            # 检查是否全为数字
            if not new_text.isdigit():
                return False
                
            # 检查长度不超过10位
            if len(new_text) > 10:
                return False
                
            return True
        
        # 注册验证函数
        vcmd = (dialog.register(validate_input), '%P')
        code_entry.config(validate="key", validatecommand=vcmd)
        
        # 加号按钮
        def increase_code():
            try:
                current = int(machine_code_var.get())
                machine_code_var.set(str(current + 1))
            except ValueError:
                # 如果当前值不是有效数字，设为1
                machine_code_var.set("1")
        
        plus_btn = ttk.Button(code_frame, text="+", command=increase_code, width=3)
        plus_btn.pack(side=tk.LEFT, padx=5)
        
        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_machine_code():
            new_code_str = machine_code_var.get().strip()
            if not new_code_str:
                messagebox.showwarning("警告", "机器码不能为空")
                return
                
            try:
                new_code = int(new_code_str)
                if new_code < 1:
                    messagebox.showwarning("警告", "机器码必须大于0")
                    return
                    
                self.machine_code = new_code
                self.log(f"机器码已更新为: {new_code}")
                # 保存配置
                self.save_config()
                dialog.destroy()
            except ValueError:
                messagebox.showwarning("警告", "请输入有效的数字")
        
        ttk.Button(button_frame, text="保存", command=save_machine_code).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 聚焦到输入框
        code_entry.focus_set()
        code_entry.select_range(0, tk.END)  # 选中文本
        
        # 等待对话框关闭
        self.root.wait_window(dialog)
    
    def check_template(self):
        """检查模板是否存在"""
        template_file = self.get_template_path()
        if os.path.exists(template_file):
            self.template_status_var.set("模板已加载")
            self.log(f"模板已从 {template_file} 加载")
            
            # 确保处理器使用正确的模板文件
            if self.processor:
                self.processor.template_file = template_file
                # 不再重复加载模板，因为TubePlateProcessor构造函数已经处理了
                # self.processor.load_template()
        else:
            self.template_status_var.set("模板不存在，请先画模板")
            self.log(f"警告：模板文件 {template_file} 不存在，请先点击'重新画模板'按钮")
    
    def log(self, message):
        """添加日志消息（线程安全）"""
        def _update_log():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            self.log_text.insert(tk.END, log_message)
            self.log_text.see(tk.END)
            self.root.update_idletasks()
        
        # 检查是否在主线程中
        if threading.current_thread() == threading.main_thread():
            _update_log()
        else:
            # 在子线程中，使用after调度到主线程执行
            self.root.after(0, _update_log)
    
    def update_stats(self):
        """更新统计信息"""
        self.stats_text.delete(1.0, tk.END)
        
        if not self.qr_results:
            self.stats_text.insert(tk.END, "暂无二维码识别结果\n")
            return
        
        # 基本统计 - 使用实际应用的行列数
        total_positions = self.rows * self.cols
        detected_count = len(self.qr_results)
        detection_rate = (detected_count / total_positions) * 100 if total_positions > 0 else 0
        
        stats = f"总位置数: {total_positions}\n"
        stats += f"已识别二维码: {detected_count}\n"
        stats += f"识别率: {detection_rate:.2f}%\n\n"
        
        # 按行统计
        rows = {}
        for pos, value in self.qr_results.items():
            row = pos[0]
            if row not in rows:
                rows[row] = {"count": 0, "positions": []}
            rows[row]["count"] += 1
            rows[row]["positions"].append(pos)
        
        stats += "按行统计:\n"
        for row in sorted(rows.keys()):
            # 创建一个包含所有可能位置的列表（1到self.cols）
            all_positions = [f"{row}{col}" for col in range(1, self.cols + 1)]
            detected_positions = rows[row]["positions"]
            
            # 构建对齐的显示格式
            aligned_positions = []
            for pos in all_positions:
                if pos in detected_positions:
                    aligned_positions.append(pos)
                else:
                    # 根据位置序号的位数调整空格数量
                    if len(pos) == 2:  # 如A1、B2等
                        aligned_positions.append("  ")  # 用三个空格表示未识别的单数字位置
                    else:  # 如A11、B12等
                        aligned_positions.append("   ")  # 用四个空格表示未识别的双数字位置
            
            # 将位置列表转换为字符串
            positions_str = ", ".join(aligned_positions)
            stats += f"  {row}行: {rows[row]['count']}个 ({positions_str})\n"
        
        self.stats_text.insert(tk.END, stats)
    
    def toggle_auto_send(self):
        """切换自动发送状态"""
        self.auto_send = not self.auto_send  # 切换状态
        if self.auto_send:
            self.auto_send_btn.config(text="禁用自动发送")
            self.log("自动发送已启用")
        else:
            self.auto_send_btn.config(text="启用自动发送")
            self.log("自动发送已禁用")
    
    def toggle_code_mode(self):
        """切换QR/DM识别模式"""
        if self.code_mode == "QR":
            self.code_mode = "DM"
            self.code_mode_btn.config(text="DM码")
            self.log("已切换到DM码识别模式")
        else:
            self.code_mode = "QR"
            self.code_mode_btn.config(text="QR码")
            self.log("已切换到QR码识别模式")
    
    def generate_data_id(self):
        """生成15位随机数字作为data_id"""
        return ''.join(random.choices(string.digits, k=15))
    
    def send_results(self, auto_send=False):
        """发送结果到后端"""
        if not self.qr_results:
            self.log("没有可发送的二维码识别结果")
            self.send_status_var.set("无数据")
            return
        
        try:
            # 计算总位置数 - 使用实际应用的行列数
            total_positions = self.rows * self.cols
            
            # 生成15位随机数字作为data_id
            data_id = self.generate_data_id()
            
            # 准备发送的数据
            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_positions": total_positions,
                "detected_count": len(self.qr_results),
                "data_id": data_id,
                "machine_id": self.machine_code,
                "results": self.qr_results
            }
            
            # 发送POST请求
            if auto_send:
                self.log("正在自动发送结果到服务器...")
            else:
                self.log("正在发送结果到服务器...")
            
            response = requests.post(self.server_url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    # 验证返回的data_id是否与发送的一致
                    returned_data_id = result.get('data_id')
                    if returned_data_id == data_id:
                        if auto_send:
                            self.log(f"结果自动发送成功，数据ID验证一致: {returned_data_id}")
                            self.send_status_var.set("已自动发送成功")
                        else:
                            self.log(f"结果发送成功，数据ID验证一致: {returned_data_id}")
                            self.send_status_var.set("发送成功")
                        
                        # 提取后端返回的negative和loc_err字段
                        negative_positions = result.get('negative', [])
                        loc_err_positions = result.get('loc_err', [])
                        
                        # 更新可视化，显示negative和loc_err区域
                        self.update_visualization(negative_positions, loc_err_positions)
                    else:
                        # data_id不一致，提示数据返回错误
                        self.log(f"数据返回错误：发送的data_id({data_id})与返回的data_id({returned_data_id})不一致")
                        self.send_status_var.set("数据返回错误")
                        messagebox.showerror("数据返回错误", 
                                           f"发送的data_id({data_id})与返回的data_id({returned_data_id})不一致")
                else:
                    self.log(f"发送失败: {result.get('message', '未知错误')}")
                    self.send_status_var.set("发送失败")
            else:
                self.log(f"发送失败，HTTP状态码: {response.status_code}")
                self.send_status_var.set("发送失败")
                
        except requests.exceptions.RequestException as e:
            self.log(f"发送请求时出错: {e}")
            self.send_status_var.set("连接错误")
        except Exception as e:
            self.log(f"发送结果时出错: {e}")
            self.send_status_var.set("发送错误")
    
    def check_and_send_auto(self):
        """检查是否满足自动发送条件并发送结果"""
        if not self.auto_send:
            return
        
        # 计算总位置数 - 使用实际应用的行列数
        total_positions = self.rows * self.cols
        
        # 检查是否识别了100%的结果
        if len(self.qr_results) == total_positions:
            self.log("检测到100%识别率，自动发送结果...")
            self.send_results(auto_send=True)
    
    def update_map(self):
        """更新二维码映射"""
        self.map_text.delete(1.0, tk.END)
        
        if not self.qr_results:
            self.map_text.insert(tk.END, "暂无二维码识别结果\n")
            return
        
        # 自定义排序函数：先按字母排序，再按数字排序
        def sort_key(pos):
            # 提取字母部分和数字部分
            letter = pos[0]
            number = int(pos[1:])
            return (letter, number)
        
        # 按位置排序显示
        sorted_positions = sorted(self.qr_results.keys(), key=sort_key)
        for pos in sorted_positions:
            value = self.qr_results[pos]
            # 检查位置序号的数字部分是否为个位数
            if len(pos) == 2:  # 如A1、B2等
                self.map_text.insert(tk.END, f"{pos} : {value}\n")  # 冒号前添加空格
            else:  # 如A11、B12等
                self.map_text.insert(tk.END, f"{pos}: {value}\n")    # 冒号前不添加空格
    
    def update_visualization(self, negative_positions=None, loc_err_positions=None):
        """更新可视化图表"""
        self.ax.clear()
        
        if not self.qr_results:
            self.ax.text(0.5, 0.5, "No Data", horizontalalignment='center', verticalalignment='center', transform=self.ax.transAxes)
        else:
            # 创建一个动态大小的网格表示行和列
            grid = np.zeros((self.rows, self.cols))
            
            # 填充网格
            for pos, value in self.qr_results.items():
                row = ord(pos[0]) - ord('A')  # A=0, B=1, ..., Z=25
                col = int(pos[1:]) - 1  # 1=0, 2=1, ..., 20=19
                if 0 <= row < self.rows and 0 <= col < self.cols:
                    grid[row, col] = 1
            
            # 如果提供了negative和loc_err位置，更新网格
            if negative_positions is not None and loc_err_positions is not None:
                # 标记negative位置为2（黄色）
                for pos in negative_positions:
                    row = ord(pos[0]) - ord('A')
                    col = int(pos[1:]) - 1
                    if 0 <= row < self.rows and 0 <= col < self.cols:
                        grid[row, col] = 2
                
                # 标记loc_err位置为3（红色），优先级高于negative
                for pos in loc_err_positions:
                    row = ord(pos[0]) - ord('A')
                    col = int(pos[1:]) - 1
                    if 0 <= row < self.rows and 0 <= col < self.cols:
                        grid[row, col] = 3
                
                # 使用四种颜色：未识别(灰色)、成功(绿色)、negative(黄色)、loc_err(红色)
                cmap = plt.cm.colors.ListedColormap(['lightgray', 'green', 'yellow', 'red'])
                bounds = [-0.5, 0.5, 1.5, 2.5, 3.5]
                norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)
            else:
                # 使用两种颜色：未识别(灰色)、成功(绿色)
                cmap = plt.cm.colors.ListedColormap(['lightgray', 'green'])
                bounds = [-0.5, 0.5, 1.5]
                norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)
            
            self.ax.imshow(grid, cmap=cmap, norm=norm, interpolation='nearest')
            
            # 添加标签
            row_labels = [chr(ord('A') + i) for i in range(self.rows)]
            col_labels = [str(i + 1) for i in range(self.cols)]
            
            self.ax.set_xticks(np.arange(self.cols))
            self.ax.set_yticks(np.arange(self.rows))
            self.ax.set_xticklabels(col_labels)
            self.ax.set_yticklabels(row_labels)
            
            self.ax.set_title("QR Code Recognition Results")
            
            # 在方块中心添加位置序号
            for row in range(self.rows):
                for col in range(self.cols):
                    # 未识别成功的位置或标记为negative/loc_err的位置
                    if grid[row, col] == 0 or grid[row, col] == 2 or grid[row, col] == 3:
                        pos_label = f"{chr(ord('A') + row)}{col + 1}"
                        # 根据状态选择文字颜色
                        if grid[row, col] == 0:  # 灰色
                            text_color = 'white'
                        elif grid[row, col] == 2:  # 黄色
                            text_color = 'black'
                        else:  # 红色
                            text_color = 'white'
                        
                        self.ax.text(col, row, pos_label, 
                                   ha='center', va='center', 
                                   color=text_color, fontsize=10, weight='bold')
            
            # 不添加颜色条
        
        self.canvas.draw()
    
    def recalibrate_template(self, original_rows=None, original_cols=None, was_monitoring=None, was_auto_send=None):
        """重新绘制模板"""
        # 如果没有传入状态，则使用当前状态
        if was_monitoring is None:
            was_monitoring = self.monitoring
        if was_auto_send is None:
            was_auto_send = self.auto_send
        
        # 停止监控（如果正在运行）
        if was_monitoring:
            self.toggle_monitoring()
        
        # 查找监控文件夹中的最新图片文件
        image_path = None
        if os.path.exists(self.watch_dir):
            image_files = []
            for file in os.listdir(self.watch_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(self.watch_dir, file)
                    # 获取文件修改时间
                    mod_time = os.path.getmtime(file_path)
                    image_files.append((file_path, mod_time))
            
            # 按修改时间排序，选择最新的图片
            if image_files:
                image_files.sort(key=lambda x: x[1], reverse=True)
                image_path = image_files[0][0]
        
        if not image_path:
            self.log(f"错误：未找到图片文件，请将图片文件放入{self.watch_dir}文件夹")
            messagebox.showerror("错误", f"未找到图片文件，请将图片文件放入{self.watch_dir}文件夹")
            # 恢复监控和自动发送状态
            self._restore_monitoring_and_auto_send(was_monitoring, was_auto_send)
            return
        
        # 在单独的线程中运行标定，避免阻塞主UI
        def run_calibration():
            try:
                # 导入并调用line_calibrate的cli_main函数
                from line_calibrate import cli_main
                template_path = self.get_template_path()
                result = cli_main(image_path, template_path, self.rows, self.cols)
                
                # 检查标定是否成功
                if result is not None:
                    # 标定完成后更新UI
                    self.root.after(0, lambda: self.log(f"模板重绘完成，重新加载模板 {template_path}..."))
                    
                    # 重新加载模板
                    if os.path.exists(template_path):
                        # 重新创建处理器以确保使用正确的模板文件
                        self.root.after(0, lambda: self._reset_processor_with_template(template_path))
                        self.root.after(0, lambda: self.template_status_var.set("模板已重新加载"))
                        self.root.after(0, lambda: self.log(f"模板 {template_path} 已成功重新加载"))
                        self.root.after(0, lambda: self.log(f"新模板已应用，孔版布局: {self.rows}行 x {self.cols}列"))
                        self.root.after(0, lambda: messagebox.showinfo("成功", f"模板已重新加载\n孔版布局: {self.rows}行 x {self.cols}列"))
                        # 标定成功，保存配置
                        self.root.after(0, lambda: self.save_config())
                        
                        # 恢复监控和自动发送状态
                        self.root.after(0, lambda: self._restore_monitoring_and_auto_send(was_monitoring, was_auto_send))
                    else:
                        self.root.after(0, lambda: self.template_status_var.set("模板文件不存在"))
                        self.root.after(0, lambda: self.log(f"错误：模板文件 {template_path} 不存在"))
                        self.root.after(0, lambda: messagebox.showerror("错误", "模板文件不存在，请重新运行标定程序"))
                        
                        # 恢复监控和自动发送状态
                        self.root.after(0, lambda: self._restore_monitoring_and_auto_send(was_monitoring, was_auto_send))
                else:
                    # 标定失败，恢复原始行列数
                    if original_rows is not None and original_cols is not None:
                        self.root.after(0, lambda: self._restore_original_plate_size(original_rows, original_cols))
                    
                    # 标定失败，不更新模板
                    self.root.after(0, lambda: self.log("模板标定失败：未完成标定或线条数量不足"))
                    self.root.after(0, lambda: self.template_status_var.set("模板标定失败"))
                    self.root.after(0, lambda: messagebox.showwarning("警告", "模板标定失败：未完成标定或线条数量不足"))
                    
                    # 恢复监控和自动发送状态
                    self.root.after(0, lambda: self._restore_monitoring_and_auto_send(was_monitoring, was_auto_send))
                    
            except Exception as e:
                # 发生异常，恢复原始行列数
                if original_rows is not None and original_cols is not None:
                    self.root.after(0, lambda: self._restore_original_plate_size(original_rows, original_cols))
                
                self.root.after(0, lambda: self.log(f"模板重绘程序执行失败: {e}"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"模板重绘程序执行失败: {e}"))
                
                # 恢复监控和自动发送状态
                self.root.after(0, lambda: self._restore_monitoring_and_auto_send(was_monitoring, was_auto_send))
        
        # 显示提示信息
        info_msg = (f"模板标定指南：\n\n"
                   f"1. 按'v'键：竖线模式，标记两条竖线——左右边界\n\n"
                   f"2. 按'a'键：自动填充{self.cols+1}条等间距竖线\n\n"
                   f"3. 按'h'键：横线模式，标记两条横线——上下边界\n\n"
                   f"4. 按'a'键：自动填充{self.rows+1}条等间距横线\n\n"
                   f"5. 完成标定后：按's'键保存模板，再按'esc'键应用并退出\n\n\n"
                   f"注：请先切换为英文输入法，'d'键删除上一条线，'c'键清除所有线\n\n"
                   f"目标孔版布局： {self.rows}行 x {self.cols}列")
        
        messagebox.showinfo("模板标定指南", info_msg)
        
        # 启动标定线程
        self.log("正在启动line_calibrate，请完成标定...")
        threading.Thread(target=run_calibration, daemon=True).start()
    
    def _restore_original_plate_size(self, original_rows, original_cols):
        """恢复原始孔版大小"""
        self.rows = original_rows
        self.cols = original_cols
        
        # 更新UI控件的值
        self.rows_var.set(self.rows)
        self.cols_var.set(self.cols)
        
        # 更新处理器的行列数
        self.processor.rows = self.rows
        self.processor.cols = self.cols
        
        # 重新生成标签（检查方法是否存在）
        if hasattr(self.processor, "_generate_labels"):
            self.processor.labels = self.processor._generate_labels()
        
        self.log(f"已恢复原始孔版大小: {self.rows}行 x {self.cols}列")
    
    def _restore_auto_send(self, was_auto_send):
        """恢复自动发送状态"""
        self.auto_send = was_auto_send
        if self.auto_send:
            self.auto_send_btn.config(text="禁用自动发送")
        else:
            self.auto_send_btn.config(text="启用自动发送")
    
    def _restore_monitoring_and_auto_send(self, was_monitoring, was_auto_send):
        """恢复监控和自动发送状态"""
        # 恢复监控状态
        if was_monitoring:
            self.toggle_monitoring()
        
        # 恢复自动发送状态
        self._restore_auto_send(was_auto_send)
    
    def select_monitor_directory(self):
        """选择监控文件夹"""
        # 保存当前监控和自动发送状态
        was_monitoring = self.monitoring
        was_auto_send = self.auto_send
        
        # 如果正在监控，先停止监控
        if was_monitoring:
            self.toggle_monitoring()
        
        # 打开文件夹选择对话框
        selected_dir = filedialog.askdirectory(
            title="选择监控文件夹",
            initialdir=self.watch_dir
        )
        
        if selected_dir:
            self.watch_dir = selected_dir
            self.log(f"监控文件夹已更改为: {self.watch_dir}")
            # 更新显示的监控文件夹路径
            self.monitor_dir_label.config(text=f"监控文件夹: {self.watch_dir}")
            # 保存配置到config.json
            self.save_config()
            
            # 恢复监控和自动发送状态
            self._restore_monitoring_and_auto_send(was_monitoring, was_auto_send)
        else:
            self.log("未选择新的监控文件夹")
            
            # 恢复监控状态
            if was_monitoring:
                self.toggle_monitoring()
    
    def toggle_monitoring(self):
        """切换监控状态"""
        if self.monitoring:
            # 停止监控
            self.monitoring = False
            self.monitor_btn.config(text="开始监控")
            self.status_var.set("监控已停止")
            self.log("监控已停止")
        else:
            # 开始监控
            self.monitoring = True
            self.monitor_btn.config(text="停止监控")
            self.status_var.set("监控运行中...")
            self.log(f"开始监控 {self.watch_dir} 文件夹...")
            
            # 在新线程中运行监控
            monitor_thread = threading.Thread(target=self.monitor_directory)
            monitor_thread.daemon = True
            monitor_thread.start()
    
    def monitor_directory(self):
        """监控目录"""
        # 确保监控目录存在
        if not os.path.exists(self.watch_dir):
            os.makedirs(self.watch_dir)
            self.log(f"创建监控目录: {self.watch_dir}")
        
        # 获取当前文件列表，但不处理已有文件
        current_files = set(os.listdir(self.watch_dir))
        
        while self.monitoring:
            try:
                # 获取当前所有文件
                all_files = set(os.listdir(self.watch_dir))
                # 检查新文件
                new_files = all_files - current_files
                
                for file_name in new_files:
                    file_path = os.path.join(self.watch_dir, file_name)
                    
                    # 跳过目录
                    if os.path.isdir(file_path):
                        continue
                    
                    # 检查文件扩展名
                    if not (file_name.lower().endswith('.jpg') or file_name.lower().endswith('.png') or 
                            file_name.lower().endswith('.jpeg') or file_name.lower().endswith('.bmp')):
                        continue
                    
                    self.log(f"检测到新图片: {file_name}")
                    # 在单独的线程中处理图片，避免阻塞监控线程
                    process_thread = threading.Thread(target=self.process_image, args=(file_path,))
                    process_thread.daemon = True
                    process_thread.start()
                
                # 关键：更新current_files，避免重复处理
                current_files = all_files
                
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                self.log(f"监控过程中出错: {e}")
                time.sleep(5)  # 出错后等待5秒再继续
    
    def process_single_image(self):
        """处理单张图片"""
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        self.log(f"处理单张图片: {file_path}")
        # 在单独的线程中处理图片，避免阻塞主线程
        process_thread = threading.Thread(target=self.process_image, args=(file_path,))
        process_thread.daemon = True
        process_thread.start()
    
    def process_image(self, image_path):
        """处理图片：切割和识别二维码"""
        # 使用互斥锁确保图片处理是串行的
        with self.processing_lock:
            try:
                file_name = os.path.basename(image_path)
                
                # 检查文件是否可读
                if not os.path.exists(image_path):
                    self.log(f"文件不存在: {image_path}")
                    return
                
                # 检查模板是否存在
                template_file = self.get_template_path()
                if not os.path.exists(template_file):
                    self.log(f"模板文件 {template_file} 不存在，请先画模板")
                    # 在主线程中显示警告对话框
                    self.root.after(0, lambda: messagebox.showwarning("警告", f"模板文件 {template_file} 不存在，请先点击'重新画模板'按钮"))
                    return
                
                # 1. 切割图片
                self.log("步骤1: 切割图片...")
                try:
                    # 确保cut_results目录存在
                    if not os.path.exists("cut_results"):
                        os.makedirs("cut_results")
                        self.log("创建cut_results目录")
                    else:
                        # 清空cut_results目录，删除所有文件
                        for old_name in os.listdir("cut_results"):
                            old_path = os.path.join("cut_results", old_name)
                            try:
                                if os.path.isfile(old_path):
                                    os.remove(old_path)
                            except Exception as e:
                                self.log(f"删除文件 {old_name} 失败: {e}")
                        self.log("已清空cut_results目录")
                    
                    # 获取切割结果
                    results = self.processor.cut_image(image_path)
                    if not results:
                        self.log("切割失败，跳过二维码识别")
                        return
                    
                    # 保存切割结果到cut_results目录
                    for label, roi in results:
                        output_path = os.path.join("cut_results", f"{label}.png")
                        cv2.imwrite(output_path, roi)
                    
                    self.log(f"切割完成，共生成 {len(results)} 个子图片")
                except Exception as e:
                    self.log(f"切割过程中出错: {e}")
                    return
                
                # 2. 识别二维码
                self.log("步骤2: 识别二维码...")
                try:
                    # 确保Result目录存在
                    if not os.path.exists("Result"):
                        os.makedirs("Result")
                        self.log("创建Result目录")
                    
                    # 为每个图片创建唯一的输出文件
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = os.path.join("Result", f"qr_results_{timestamp}_{os.path.splitext(file_name)[0]}.json")
                    
                    # 根据当前模式调用对应的识别函数
                    if self.code_mode == "QR":
                        qr_results = process_qr_codes("cut_results", output_file)
                        self.log(f"二维码识别完成，共识别 {len(qr_results)} 个二维码")
                    else:
                        qr_results = process_dm_codes("cut_results", output_file)
                        self.log(f"DM码识别完成，共识别 {len(qr_results)} 个DM码")
                    
                    # 更新当前二维码结果
                    self.qr_results = qr_results
                    
                    # 重置发送状态为"未发送"
                    self.send_status_var.set("未发送")
                    
                    # 更新UI（使用after调度到主线程执行）
                    self.root.after(0, self.update_stats)
                    self.root.after(0, self.update_map)
                    self.root.after(0, lambda: self.update_visualization())
                    
                    # 检查是否需要自动发送
                    self.root.after(0, self.check_and_send_auto)
                    
                except Exception as e:
                    self.log(f"二维码识别过程中出错: {e}")
                    return
                
                self.log(f"图片处理完成: {file_name}")
                
            except Exception as e:
                self.log(f"处理图片时发生错误: {e}")
    
    def apply_plate_size(self):
        """应用孔版大小设置"""
        try:
            # 获取新的行列数
            new_rows = self.rows_var.get()
            new_cols = self.cols_var.get()
            
            # 限制行列数不超过20
            if new_rows > 20:
                new_rows = 20
                self.rows_var.set(new_rows)
                self.log("行数超过最大值20，已自动重置为20")
            
            if new_cols > 20:
                new_cols = 20
                self.cols_var.set(new_cols)
                self.log("列数超过最大值20，已自动重置为20")
            
            # 检查是否发生变化
            if new_rows == self.rows and new_cols == self.cols:
                self.log("孔版大小未发生变化")
                return
            
            # 保存原始行列数，以便在标定失败时恢复
            original_rows = self.rows
            original_cols = self.cols
            
            # 更新当前行列数
            self.rows = new_rows
            self.cols = new_cols
            
            # 更新UI显示
            self.rows_var.set(self.rows)
            self.cols_var.set(self.cols)
            
            # 计算新模板文件名
            template_file = self.get_template_path()
            
            self.log(f"正在更新孔版大小: {self.rows}行 x {self.cols}列")
            
            # 检查模板文件是否存在
            if os.path.exists(template_file):
                # 模板已存在，直接加载
                self.log(f"检测到已存在模板 {template_file}，直接加载")
                
                # 使用新的方法重置处理器并同步行列数
                self._reset_processor_with_template(template_file)
                
                # 保存配置
                self.save_config()
                
                # 更新可视化
                self.update_visualization()
                
                self.log(f"已成功切换到 {self.rows}x{self.cols} 模板")
                messagebox.showinfo("成功", f"已成功切换到 {self.rows}x{self.cols} 模板")
            else:
                # 模板不存在，需要重新标定
                self.log(f"未找到模板 {template_file}，需要重新标定")
                
                # 触发标定
                self.recalibrate_template(original_rows, original_cols, self.monitoring, self.auto_send)
                
        except Exception as e:
            self.log(f"应用孔版大小失败: {e}")
            messagebox.showerror("错误", f"应用孔版大小失败: {e}")
    
    def on_close(self):
        """关闭窗口时的处理"""
        self.log("正在关闭程序...")
        
        # 停止监控
        if self.monitoring:
            self.monitoring = False
            self.log("监控已停止")
        
        # 关闭Matplotlib图形和清理资源
        try:
            if hasattr(self, 'fig') and self.fig is not None:
                plt.close(self.fig)
                self.fig = None
            if hasattr(self, 'canvas') and self.canvas is not None:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None
            self.log("Matplotlib资源已清理")
        except Exception as e:
            self.log(f"清理Matplotlib资源时出错: {e}")
        
        # 手动调用清理函数（因为os._exit不会触发atexit注册的函数）
        try:
            import runtime_hook
            runtime_hook.cleanup_processes()
            self.log("已调用全局进程清理函数")
        except Exception as e:
            self.log(f"调用全局进程清理函数时出错: {e}")
        
        self.log("程序已关闭")
        self.root.destroy()
    
    def set_window_icon(self):
        """设置窗口图标和任务栏图标"""
        try:
            # 使用iconbitmap设置窗口图标（Windows原生方式）
            # 这会同时设置窗口左上角图标和任务栏图标
            try:
                icon_path = get_resource_path("geese32.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(default=icon_path)
                    # 检查log_text是否已创建
                    if hasattr(self, 'log_text') and self.log_text:
                        self.log("已使用iconbitmap设置窗口图标（geese32.ico）")
            except Exception as e:
                # 检查log_text是否已创建
                if hasattr(self, 'log_text') and self.log_text:
                    self.log(f"使用iconbitmap设置图标失败: {e}")
                
            # 检查log_text是否已创建
            if hasattr(self, 'log_text') and self.log_text:
                self.log("窗口图标设置完成")
        except Exception as e:
            # 检查log_text是否已创建
            if hasattr(self, 'log_text') and self.log_text:
                self.log(f"设置窗口图标失败: {e}")

if __name__ == "__main__":
    # 在创建Tk窗口之前设置AppUserModelID，确保任务栏图标正确显示
    if platform.system() == "Windows":
        try:
            import ctypes
            # 使用新的AppUserModelID来绕过缓存
            app_id = "Geese.Gaze.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception as e:
            print(f"设置AppUserModelID失败: {e}")
    
    root = tk.Tk()
    app = GeeseUI(root)
    root.mainloop()