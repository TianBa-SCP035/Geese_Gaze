import os
import json
import cv2
import zxingcpp
from pylibdmtx.pylibdmtx import decode as dmtx_decode

# ---------- 解码逻辑 ----------
def _decode_with_backoffs(img):
    """多模式DM码识别，针对Data Matrix码优化
    
    策略说明：
        - 模式一：pylibdmtx（原图+2倍放大，专业DM码库，优先）
        - 模式二：ZXing（原图+2倍灰度图，后备方案）
    
    Args:
        img: 输入图像
        
    Returns:
        tuple: (识别方法标签, 识别结果) 或 (None, None)
    """
    # 预处理：计算2倍放大图像，使用INTER_NEAREST插值避免边缘伪影
    img2x = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
    
    # 模式一：pylibdmtx专门识别DM码（优先使用）
    dmtx_results = dmtx_decode(img, timeout=500, max_count=1)
    if dmtx_results:
        best_result = max(dmtx_results, key=lambda r: len(r.data))
        return "M1-pylibdmtx", best_result.data.decode("utf-8", errors="strict")
    
    # 2倍放大图识别DM码
    dmtx_results = dmtx_decode(img2x, timeout=500, max_count=1)
    if dmtx_results:
        best_result = max(dmtx_results, key=lambda r: len(r.data))
        return "M1-pylibdmtx-2x", best_result.data.decode("utf-8", errors="strict")
    
    # 模式二：ZXing识别（后备方案）
    results = zxingcpp.read_barcodes(img)
    if results:
        return "M2-ZXing-DM", results[0].text
    
    # 2倍放大灰度图
    img2x_gray = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
    img2x_gray = cv2.cvtColor(img2x_gray, cv2.COLOR_BGR2GRAY)
        
    results = zxingcpp.read_barcodes(img2x_gray)
    if results:
        return "M2-ZXing-DM-2x-灰度", results[0].text

    return None, None

def decode_dm_code(image_path):
    """识别单个图像中的DM码"""
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
def process_dm_codes(cut_results_dir="cut_results", output_file="dm_results.json"):
    """批量处理目录中的PNG图像，识别其中的DM码"""
    if not os.path.exists(cut_results_dir):
        print(f"目录不存在: {cut_results_dir}")
        return {}

    png_files = sorted([f for f in os.listdir(cut_results_dir) if f.lower().endswith('.png')])
    if not png_files:
        print(f"目录中没有 PNG 文件: {cut_results_dir}")
        return {}

    print(f"找到 {len(png_files)} 个 PNG 文件，开始识别DM码...")
    results = {}

    for png_file in png_files:
        label = os.path.splitext(png_file)[0]
        image_path = os.path.join(cut_results_dir, png_file)
        dm_data = decode_dm_code(image_path)
        if dm_data:
            results[label] = dm_data
            print(f"识别成功: {label} -> {dm_data}")
        else:
            print(f"未识别到DM码: {label}")

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
        dm_data = decode_dm_code(image_path)
        if dm_data:
            print(f"\n识别成功: {dm_data}")
        else:
            print("\n未识别到DM码")
    else:
        # 批量处理
        results = process_dm_codes()
        print("\n识别结果 (Map):")
        for label, dm_data in results.items():
            print(f"'{label}': '{dm_data}'")
        print(f"\n总共识别了 {len(results)} 个DM码")
