import cv2
import numpy as np
import json
import os

# 可配置参数：ROI扩展比例
# 1.0 表示不扩展，1.2 表示向四个方向各扩展20%，以此类推
ROI_EXPANSION_RATIO = 1.1

class TubePlateProcessor:
    def __init__(self, template_file="template.json"):
        """
        初始化处理器
        :param template_file: 模板文件路径
        """
        self.template_file = template_file
        self.positions = None
        self.rows = 12  # 默认行数
        self.cols = 8   # 默认列数
        self.labels = self._generate_labels()
        
        # 如果模板文件存在，加载模板
        if os.path.exists(template_file):
            self.load_template()
    
    def _generate_labels(self):
        """生成孔位标签 (A1, A2, ..., Z20)"""
        labels = []
        for row in range(self.rows):  # 行数
            for col in range(self.cols):  # 列数
                label = f"{chr(65 + row)}{col + 1}"
                labels.append(label)
        return labels
    
    def save_template(self):
        """保存模板到文件"""
        try:
            template_data = {
                "positions": self.positions,
                "labels": self.labels,
                "rows": self.rows,
                "cols": self.cols
            }
            
            with open(self.template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            print(f"已保存模板: {self.template_file}")
            print(f"孔版布局: {self.rows}行 x {self.cols}列")
            return True
        except Exception as e:
            print(f"保存模板失败: {e}")
            return False
    
    def load_template(self):
        """从文件加载模板"""
        try:
            with open(self.template_file, 'r') as f:
                template_data = json.load(f)
            
            self.positions = template_data.get('positions', [])
            
            # 加载孔版行列数信息，如果不存在则使用默认值
            self.rows = template_data.get('rows', 12)
            self.cols = template_data.get('cols', 8)
            
            # 重新生成标签
            self.labels = self._generate_labels()
            
            print(f"已加载模板: {self.template_file}")
            print(f"孔版布局: {self.rows}行 x {self.cols}列")
            return True
        except Exception as e:
            print(f"加载模板失败: {e}")
            return False
    
    def cut_image(self, image_path):
        """
        切割图像为多个小图像
        :param image_path: 图像文件路径
        :return: 切割后的图像列表，每个元素为 (label, roi)
        """
        if self.positions is None:
            print("没有可用的模板，请先加载或创建模板")
            return []
        
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"无法读取图像: {image_path}")
            return []
        
        # 获取图像尺寸
        img_height = image.shape[0]
        img_width = image.shape[1]
        print(f"处理图片尺寸: {img_width}x{img_height}")
        
        # 将相对坐标转换为绝对坐标
        absolute_positions = []
        for corner_points in self.positions:
            absolute_corner_points = []
            for relative_x, relative_y in corner_points:
                absolute_x = int(relative_x * img_width)
                absolute_y = int(relative_y * img_height)
                absolute_corner_points.append((absolute_x, absolute_y))
            absolute_positions.append(absolute_corner_points)
        
        # 切割图像
        results = []
        for i, corner_points in enumerate(absolute_positions):
            if i >= len(self.labels):
                print(f"警告: 位置数量({len(absolute_positions)})大于标签数量({len(self.labels)})")
                break
                
            # 使用_extract_roi方法提取ROI
            roi = self._extract_roi(image, corner_points)
            if roi is None:
                print(f"警告: 无法提取位置 {self.labels[i]} 的ROI")
                continue
            
            # 添加到结果列表
            results.append((self.labels[i], roi))
        
        print(f"已切割图像: {len(results)} 个区域")
        return results
    
    def _extract_roi(self, img, corner_points):
        """
        提取孔的ROI区域
        :param img: 输入图片
        :param corner_points: 孔的四个角点坐标 [左上, 右上, 左下, 右下]
        :return: ROI区域
        """
        # 获取四个角点坐标
        top_left, top_right, bottom_left, bottom_right = corner_points
        
        # 确保坐标是整数
        top_left = (int(top_left[0]), int(top_left[1]))
        top_right = (int(top_right[0]), int(top_right[1]))
        bottom_left = (int(bottom_left[0]), int(bottom_left[1]))
        bottom_right = (int(bottom_right[0]), int(bottom_right[1]))
        
        # 计算原始宽度和高度
        width = top_right[0] - top_left[0]
        height = bottom_left[1] - top_left[1]
        
        # 应用ROI扩展比例
        expansion = ROI_EXPANSION_RATIO - 1.0  # 计算扩展比例（例如1.2-1.0=0.2，表示扩展20%）
        expand_x = int(width * expansion)
        expand_y = int(height * expansion)
        
        # 计算扩展后的坐标
        x1 = max(0, top_left[0] - expand_x)
        y1 = max(0, top_left[1] - expand_y)
        x2 = min(img.shape[1], bottom_right[0] + expand_x)
        y2 = min(img.shape[0], bottom_right[1] + expand_y)
        
        # 确保包含边界线：如果扩展比例为1.0，则向右和向下扩展1个像素，包含边界线
        if ROI_EXPANSION_RATIO == 1.0:
            x2 = min(img.shape[1], x2 + 1)  # 向右扩展1个像素，包含右边界线
            y2 = min(img.shape[0], y2 + 1)  # 向下扩展1个像素，包含下边界线
        
        # 如果ROI区域太小，可能是因为位置在图片边缘
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            print(f"警告：位置 {top_left} 的ROI区域太小: {x2-x1}x{y2-y1}")
            return None
        
        roi = img[y1:y2, x1:x2]
        
        # 检查ROI是否为空
        if roi.size == 0:
            print(f"警告：位置 {top_left} 的ROI为空")
            return None
            
        return roi


if __name__ == "__main__":
    # 创建处理器
    processor = TubePlateProcessor()
    
    # 如果没有模板文件，进行标定
    if not os.path.exists(processor.template_file):
        print("没有找到模板文件，请先运行line_calibrate.py进行标定")
        exit(1)
    
    # 加载模板并切割图片
    processor.load_template()
    results = processor.cut_image("IMG_11.jpg")
    
    # 打印结果
    print("\n切割结果:")
    for label, path in results:
        print(f"位置 {label}: {path}")
    
    print("切割完成！")