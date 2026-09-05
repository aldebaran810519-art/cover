import zipfile
import os
import shutil
import xml.etree.ElementTree as ET
from PIL import Image

# ---------------------------------------------------------
# 1. Kobo 专属图片处理：强制补边至 3:4 比例，防止休眠强行拉伸
# ---------------------------------------------------------
def pad_image_for_kobo(image_path, output_path, target_ratio=(3, 4), bg_color=(255, 255, 255)):
    """
    Kobo 屏幕标准比例大部分为 3:4。
    此函数在封面四周补白/黑边，让整体图片变成 3:4，从物理层面杜绝 Kobo 休眠屏的拉伸变型。
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img_w, img_h = img.size
        
        target_w_ratio, target_h_ratio = target_ratio
        current_ratio = img_w / img_h
        target_aspect = target_w_ratio / target_h_ratio
        
        if current_ratio > target_aspect:
            # 图片偏宽，上下补边
            new_w = img_w
            new_h = int(img_w / target_aspect)
        else:
            # 图片偏高，左右补边
            new_h = img_h
            new_w = int(img_h * target_aspect)
            
        # 创建 3:4 比例底板并置中粘贴原图
        new_img = Image.new("RGB", (new_w, new_h), bg_color)
        paste_x = (new_w - img_w) // 2
        paste_y = (new_h - img_h) // 2
        new_img.paste(img, (paste_x, paste_y))
        new_img.save(output_path, "JPEG", quality=95)
        return new_w, new_h

# ---------------------------------------------------------
# 2. Kobo 专属内页 HTML：SVG preserveAspectRatio 完美居中
# ---------------------------------------------------------
def generate_kobo_cover_html(image_filename, width, height):
    """
    利用 SVG 保障 Kobo 打开书籍第一页时，绝对等比例居中，不超出屏幕也不变型。
    """
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Cover</title>
    <style type="text/css">
        @page {{ margin: 0; padding: 0; }}
        html, body {{
            margin: 0 !important;
            padding: 0 !important;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: #FFFFFF;
        }}
        div.cover-frame {{
            width: 100%;
            height: 100%;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="cover-frame">
        <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
             version="1.1" width="100%" height="100%" viewBox="0 0 {width} {height}" 
             preserveAspectRatio="xMidYMid meet">
            <image width="{width}" height="{height}" xlink:href="{image_filename}"/>
        </svg>
    </div>
</body>
</html>
'''

# ---------------------------------------------------------
# 3. 核心替换与 Kobo 适配
# ---------------------------------------------------------
def replace_epub_cover(epub_path, new_cover_path, output_epub_path):
    temp_dir = "temp_epub_build"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        
    # 处理成 Kobo 专属 3:4 填充封面 (若需黑边，可将 bg_color 改为 (0,0,0))
    img_w, img_h = pad_image_for_kobo(new_cover_path, "cover_kobo.jpg", target_ratio=(3, 4), bg_color=(255, 255, 255))
    
    # 递归查找原 EPUB 中所有的 cover 图片并直接覆盖，确保 Kobo 提取缓存时能直接抓取到新封面
    replaced_count = 0
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_lower = file.lower()
            if "cover" in file_lower and file_lower.endswith(('.jpg', '.jpeg', '.png')):
                target_path = os.path.join(root, file)
                shutil.copy("cover_kobo.jpg", target_path)
                replaced_count += 1
                
    print(f"成功覆盖了 {replaced_count} 个内部封面相关图片资源！")

    # 重新压缩成标准 EPUB 格式
    with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        mimetype_path = os.path.join(temp_dir, "mimetype")
        if os.path.exists(mimetype_path):
            zip_out.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            
        for root_dir, dirs, files in os.walk(temp_dir):
            for file in files:
                full_path = os.path.join(root_dir, file)
                rel_path = os.path.relpath(full_path, temp_dir)
                if rel_path == "mimetype":
                    continue
                zip_out.write(full_path, rel_path)
                
    shutil.rmtree(temp_dir)
    if os.path.exists("cover_kobo.jpg"):
        os.remove("cover_kobo.jpg")
    print("Kobo 专属 EPUB 封面替换完成！")

if __name__ == "__main__":
    if os.path.exists("input.epub") and (os.path.exists("cover.jpg") or os.path.exists("cover.png")):
        cover_file = "cover.jpg" if os.path.exists("cover.jpg") else "cover.png"
        replace_epub_cover("input.epub", cover_file, "output.epub")
