import cv2
import numpy as np
import json
import os

class LineCalibrator:
    def __init__(self, image_path=None, output_file="template.json", rows=12, cols=8):
        """
        初始化标定器
        :param image_path: 图片路径
        :param output_file: 输出文件路径
        :param rows: 孔版行数
        :param cols: 孔版列数
        """
        self.image_path = image_path
        self.output_file = output_file
        self.rows = rows  # 孔版行数
        self.cols = cols  # 孔版列数
        self.vertical_lines = []  # 竖线列表
        self.horizontal_lines = []  # 横线列表
        self.line_type = 'vertical'  # 当前画线类型：'vertical' 或 'horizontal'
        self.drawing = False  # 是否正在画线
        self.current_line = None  # 当前正在画的线
        self.scale_factor = 1.0  # 缩放因子
        self.img_copy = None
        
        # 如果提供了图片路径，则进行初始化
        if image_path is not None:
            self._initialize_from_image(image_path)
        
    def _initialize_from_image(self, image_path):
        """
        从图片初始化标定器
        :param image_path: 图片路径
        """
        # 检查图片路径是否存在
        if not os.path.exists(image_path):
            raise ValueError(f"图片文件不存在: {image_path}")
        
        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        print(f"成功读取图片: {image_path}, 尺寸: {img.shape[1]}x{img.shape[0]}")
        
        # 存储原始图片尺寸
        self.original_width = img.shape[1]
        self.original_height = img.shape[0]
        
        # 创建窗口
        cv2.namedWindow("Line Calibration", cv2.WINDOW_NORMAL)
        
        # 计算缩放比例，保持图片比例
        height, width = img.shape[:2]
        max_display_size = 800  # 最大显示尺寸
        
        print(f"原始图片尺寸: {width}x{height}, 最大显示尺寸: {max_display_size}x{max_display_size}")
        
        # 计算缩放因子，保持图片比例
        self.scale_factor = min(max_display_size / width, max_display_size / height)
        
        target_width = int(width * self.scale_factor)
        target_height = int(height * self.scale_factor)
        
        # 调整窗口大小并缩放图片
        cv2.resizeWindow("Line Calibration", target_width, target_height)
        self.img_copy = cv2.resize(img, (target_width, target_height))
        
        print(f"调整窗口大小为: {target_width}x{target_height}, 缩放因子: {self.scale_factor:.4f}")
        
        # 设置鼠标回调
        cv2.setMouseCallback("Line Calibration", self._mouse_callback)
    
    def calibrate(self, image_path=None, output_file=None):
        """
        通过画线标定试管板
        :param image_path: 标定图片路径（可选，如果初始化时已提供）
        :param output_file: 输出文件路径（可选，如果初始化时已提供）
        """
        # 如果提供了参数，则使用它们
        if image_path is not None:
            self.image_path = image_path
        if output_file is not None:
            self.output_file = output_file
            
        # 如果尚未初始化或图片路径不同，则重新初始化
        if self.img_copy is None or (image_path is not None and self.image_path != image_path):
            self._initialize_from_image(self.image_path)
        
        # 确保输出文件路径不为None
        if self.output_file is None:
            self.output_file = "template.json"
            print(f"警告：输出文件路径未指定，使用默认路径: {self.output_file}")
        
        print("画线标定说明：")
        print("1. 按 'v' 键切换到画竖线模式")
        print("2. 按 'h' 键切换到画横线模式")
        print("3. 按住鼠标左键拖动画线")
        print("4. 按 'c' 键清除所有线")
        print("5. 按 'ESC' 键完成标定")
        print("6. 按 's' 键保存当前标定并继续")
        print("7. 按 'a' 键自动添加等间距线（基于已画的两条线，适用于任意行列数）")
        print("8. 按 'd' 键删除最后一条线")
        print(f"当前模式: 画{'竖' if self.line_type == 'vertical' else '横'}线")
        print(f"已画竖线: {len(self.vertical_lines)} 条 (需要{self.cols + 1}条)")
        print(f"已画横线: {len(self.horizontal_lines)} 条 (需要{self.rows + 1}条)")
        print(f"注意：这将形成{self.cols}列×{self.rows}行的孔位布局")
        
        # 检查是否为8*12孔版，以决定是否启用自动划线功能
        is_standard_layout = (self.rows == 12 and self.cols == 8)
        
        while True:
            # 显示图片
            display_img = self.img_copy.copy()
            
            # 绘制所有竖线
            for line in self.vertical_lines:
                cv2.line(display_img, (line, 0), (line, display_img.shape[0]), (0, 255, 0), 1)
            
            # 绘制所有横线
            for line in self.horizontal_lines:
                cv2.line(display_img, (0, line), (display_img.shape[1], line), (0, 255, 0), 1)
            
            # 绘制当前正在画的线
            if self.drawing and self.current_line is not None:
                if self.line_type == 'vertical':
                    cv2.line(display_img, (self.current_line, 0), (self.current_line, display_img.shape[0]), (0, 0, 255), 1)
                else:
                    cv2.line(display_img, (0, self.current_line), (display_img.shape[1], self.current_line), (0, 0, 255), 1)
            
            # 显示状态信息
            status = f"Mode: {'Vertical' if self.line_type == 'vertical' else 'Horizontal'} | Vertical: {len(self.vertical_lines)}/{self.cols + 1} | Horizontal: {len(self.horizontal_lines)}/{self.rows + 1} | Layout: {self.cols}x{self.rows} Grid"
            cv2.putText(display_img, status, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 显示操作提示
            auto_line_hint = " a:Auto"  # 移除对8*12孔版的限制
            cv2.putText(display_img, f"v:Vertical h:Horizontal c:Clear s:Save{auto_line_hint} d:Delete ESC:Complete", (10, display_img.shape[0] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 显示图片
            cv2.imshow("Line Calibration", display_img)
            
            # 等待按键
            key = cv2.waitKey(1) & 0xFF
            
            # ESC键退出
            if key == 27:
                break
            
            # 'v'键切换到竖线模式
            elif key == ord('v'):
                self.line_type = 'vertical'
                print(f"切换到画竖线模式")
            
            # 'h'键切换到横线模式
            elif key == ord('h'):
                self.line_type = 'horizontal'
                print(f"切换到画横线模式")
            
            # 'c'键清除所有线
            elif key == ord('c'):
                self.vertical_lines = []
                self.horizontal_lines = []
                print("清除所有线")
            
            # 's'键保存当前标定
            elif key == ord('s'):
                if self._validate_lines():
                    positions = self._calculate_positions()
                    success = self._save_results(positions, self.output_file)
                    if success:
                        print(f"标定结果已保存到: {self.output_file}")
                    else:
                        print("保存标定结果失败")
                else:
                    print("线条数量不足，无法保存")
            
            # 'a'键自动添加等间距线（适用于任意行列数）
            elif key == ord('a'):
                self._auto_add_lines()
            
            # 'd'键删除最后一条线
            elif key == ord('d'):
                self._delete_last_line()
        
        # 关闭所有OpenCV窗口
        cv2.destroyAllWindows()
        
        # 检查线条数量是否足够
        if self._validate_lines():
            # 计算孔位位置
            positions = self._calculate_positions()
            
            # 保存标定结果
            success = self._save_results(positions, self.output_file)
            
            if success:
                print(f"标定完成，共计算了 {len(positions)} 个位置")
                print(f"结果已保存到: {self.output_file}")
                return positions
            else:
                print("保存标定结果失败")
                return None
        else:
            print("标定失败：线条数量不足")
            print(f"需要{self.cols + 1}条竖线和{self.rows + 1}条横线，当前有{len(self.vertical_lines)}条竖线和{len(self.horizontal_lines)}条横线")
            return None
    
    def _mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.current_line = x if self.line_type == 'vertical' else y
        
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.current_line = x if self.line_type == 'vertical' else y
        
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            if self.current_line is not None:
                lines = self.vertical_lines if self.line_type == 'vertical' else self.horizontal_lines
                max_count = self.cols + 1 if self.line_type == 'vertical' else self.rows + 1
                
                if len(lines) < max_count:
                    lines.append(self.current_line)
                    lines.sort()
                    original_coord = int(self.current_line / self.scale_factor)
                    print(f"添加{'竖线' if self.line_type == 'vertical' else '横线'}: {'x' if self.line_type == 'vertical' else 'y'}={original_coord} (显示坐标: {'x' if self.line_type == 'vertical' else 'y'}={self.current_line})")
                else:
                    print(f"已达到最大{'竖线' if self.line_type == 'vertical' else '横线'}数量({max_count}条)")
                
                self.current_line = None
                print(f"当前状态: 竖线 {len(self.vertical_lines)}/{self.cols + 1}, 横线 {len(self.horizontal_lines)}/{self.rows + 1}")
    
    def _delete_last_line(self):
        """删除最后添加的线"""
        lines = self.vertical_lines if self.line_type == 'vertical' else self.horizontal_lines
        
        if lines:
            lines.pop()
            print(f"删除{'竖线' if self.line_type == 'vertical' else '横线'}")
        else:
            print(f"没有{'竖线' if self.line_type == 'vertical' else '横线'}可删除")
        
        print(f"当前状态: 竖线 {len(self.vertical_lines)}/{self.cols + 1}, 横线 {len(self.horizontal_lines)}/{self.rows + 1}")
    
    def _auto_add_lines(self):
        """自动添加等间距线"""
        lines = self.vertical_lines if self.line_type == 'vertical' else self.horizontal_lines
        # 根据当前行列数计算需要的线条数量
        line_count = self.cols + 1 if self.line_type == 'vertical' else self.rows + 1
        spacing_count = line_count - 1
        
        if len(lines) >= 2:
            # 取边界线
            min_line = min(lines)
            max_line = max(lines)
            
            # 计算间距并添加等间距的线
            spacing = (max_line - min_line) / spacing_count
            new_lines = [int(min_line + i * spacing) for i in range(line_count)]
            new_lines.sort()
            
            if self.line_type == 'vertical':
                self.vertical_lines = new_lines
            else:
                self.horizontal_lines = new_lines
                
            print(f"已自动添加{line_count}条等间距{'竖线' if self.line_type == 'vertical' else '横线'}")
        else:
            print(f"需要至少2条{'竖线' if self.line_type == 'vertical' else '横线'}才能自动添加等间距线")
    
    def _validate_lines(self):
        """验证线条数量是否足够"""
        return len(self.vertical_lines) >= self.cols + 1 and len(self.horizontal_lines) >= self.rows + 1
    
    def _calculate_positions(self):
        """计算每个孔的四个角点坐标（使用相对坐标）"""
        positions = []

        # 只取需要的线条数量
        v_lines = self.vertical_lines[:self.cols + 1]
        h_lines = self.horizontal_lines[:self.rows + 1]

        # 确保我们有足够的线条
        if len(v_lines) < self.cols + 1 or len(h_lines) < self.rows + 1:
            print(f"错误：需要{self.cols + 1}条竖线和{self.rows + 1}条横线，当前有{len(v_lines)}条竖线和{len(h_lines)}条横线")
            return positions

        print(f"原始图片尺寸: {self.original_width}x{self.original_height}")

        # 计算每个格子的四个角点坐标（使用线条作为边界）
        for row in range(self.rows):  # 行数
            for col in range(self.cols):  # 列数
                # 计算相对坐标（分数）
                relative_left_x = (v_lines[col] / self.scale_factor) / self.original_width
                relative_right_x = (v_lines[col + 1] / self.scale_factor) / self.original_width
                relative_top_y = (h_lines[row] / self.scale_factor) / self.original_height
                relative_bottom_y = (h_lines[row + 1] / self.scale_factor) / self.original_height
                
                # 存储四个角点的相对坐标：左上、右上、左下、右下
                positions.append([
                    (relative_left_x, relative_top_y),      # 左上
                    (relative_right_x, relative_top_y),     # 右上
                    (relative_left_x, relative_bottom_y),   # 左下
                    (relative_right_x, relative_bottom_y)   # 右下
                ])

        return positions
    
    def _save_results(self, positions, output_file):
        """保存标定结果"""
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(os.path.abspath(output_file))
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"创建输出目录: {output_dir}")
            
            template_data = {
                "rows": self.rows,
                "cols": self.cols,
                "positions": positions,
                "labels": self._generate_labels()
            }
            
            print(f"准备保存标定结果到: {output_file}")
            print(f"孔版布局: {self.cols}列 x {self.rows}行")
            print(f"位置数据数量: {len(positions)}")
            print(f"标签数据数量: {len(template_data['labels'])}")
            
            with open(output_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            print(f"标定结果已成功保存到: {output_file}")
            return True
        except Exception as e:
            print(f"保存标定结果时出错: {str(e)}")
            return False
    
    def _generate_labels(self):
        """生成孔位标签 (A1, A2, ..., Z20)"""
        return [f"{chr(65 + row)}{col + 1}" for row in range(self.rows) for col in range(self.cols)]


def cli_main(image_path, output_file, rows=12, cols=8):
    """既可被导入调用，也可供 __main__ 使用的统一入口"""
    calibrator = LineCalibrator(image_path, output_file, rows, cols)
    return calibrator.calibrate()

if __name__ == "__main__":
    import sys
    # 从命令行参数获取图片路径、输出文件路径和孔版大小
    image_path = sys.argv[1] if len(sys.argv) > 1 else "IMG_11.jpg"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "template.json"
    rows = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    cols = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    
    # 不再限制最大行列数，使用用户设置的值
    cli_main(image_path, output_file, rows, cols)