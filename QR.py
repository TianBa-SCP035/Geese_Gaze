import os
import json
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
import zxingcpp
from qreader import QReader

# ---------- 解码逻辑 ----------
def _decode_with_backoffs(img):
    """多模式QR码识别，针对不完整QR码优化
    
    策略说明：
        - 模式一：Pyzbar和OpenCV（原图+2倍放大）
        - 模式二：QReader（原图+2倍放大）
        - 模式三：ZXing（原图+2倍灰度图）
    
    Args:
        img: 输入图像
        
    Returns:
        tuple: (识别方法标签, 识别结果) 或 (None, None)
    """
    # 预处理：计算2倍放大图像，使用INTER_NEAREST插值避免边缘伪影
    img2x = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
    
    # 模式一：Pyzbar识别和OpenCV识别（原图和2倍放大图）
    try:
        codes = decode(img, symbols=[ZBarSymbol.QRCODE])
        if codes:
            return "M1-Pyzbar", codes[0].data.decode("utf-8", errors="ignore")
        
        codes = decode(img2x, symbols=[ZBarSymbol.QRCODE])
        if codes:
            return "M1-Pyzbar-2x", codes[0].data.decode("utf-8", errors="ignore")
    except Exception:
        pass

    try:
        qrd = cv2.QRCodeDetector()
        data, _, _ = qrd.detectAndDecode(img)
        if data:
            return "M1-OpenCV", data
        
        data, _, _ = qrd.detectAndDecode(img2x)
        if data:
            return "M1-OpenCV-2x", data
    except Exception:
        pass
    
    # 模式二：QReader识别（对不完整QR码效果最好）
    try:
        qreader = QReader()
        result = qreader.detect_and_decode(image=img)
        if result and result[0]:
            return "M2-QReader", result[0]
        
    except Exception:
        pass
    
    # 模式三：ZXing识别
    try:
        results = zxingcpp.read_barcodes(img)
        if results:
            return "M3-ZXing", results[0].text
        
        # 2倍放大灰度图
        img2x_gray = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
        img2x_gray = cv2.cvtColor(img2x_gray, cv2.COLOR_BGR2GRAY)
            
        results = zxingcpp.read_barcodes(img2x_gray)
        if results:
            return "M3-ZXing-2x-灰度", results[0].text
            
    except Exception:
        pass

    return None, None

def decode_qr_code(image_path):
    """识别单个图像中的二维码"""
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        print(f"无法读取图片: {image_path}")
        return None

    method, data = _decode_with_backoffs(img)
    if data:
        print(f"{os.path.basename(image_path)} 使用 {method} 识别成功")
        return data
    return None

# ---------- 批量处理 ----------
def process_qr_codes(cut_results_dir="cut_results", output_file="qr_results.json"):
    """批量处理目录中的PNG图像，识别其中的二维码"""
    if not os.path.exists(cut_results_dir):
        print(f"目录不存在: {cut_results_dir}")
        return {}

    png_files = sorted([f for f in os.listdir(cut_results_dir) if f.lower().endswith('.png')])
    if not png_files:
        print(f"目录中没有 PNG 文件: {cut_results_dir}")
        return {}

    print(f"找到 {len(png_files)} 个 PNG 文件，开始识别二维码...")
    results = {}

    for png_file in png_files:
        label = os.path.splitext(png_file)[0]
        image_path = os.path.join(cut_results_dir, png_file)
        qr_data = decode_qr_code(image_path)
        if qr_data:
            results[label] = qr_data
            print(f"识别成功: {label} -> {qr_data}")
        else:
            print(f"未识别到二维码: {label}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"识别结果已保存到: {output_file}")
    return results

# ---------- 主入口 ----------
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 单个图片处理
        image_path = sys.argv[1]
        qr_data = decode_qr_code(image_path)
        if qr_data:
            print(f"\n识别成功: {qr_data}")
        else:
            print("\n未识别到二维码")
    else:
        # 批量处理
        results = process_qr_codes()
        print("\n识别结果 (Map):")
        for label, qr_data in results.items():
            print(f"'{label}': '{qr_data}'")
        print(f"\n总共识别了 {len(results)} 个二维码")
