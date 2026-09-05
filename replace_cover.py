import zipfile
import os
import shutil
from PIL import Image

def replace_epub_cover(epub_path, new_cover_path, output_epub_path):
    temp_dir = "temp_epub_build"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    # 解壓 EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        
    # 將新圖片轉為標準 JPEG 格式，完全保留原始尺寸與比例
    processed_cover = "cover_original.jpg"
    with Image.open(new_cover_path) as img:
        img = img.convert("RGB")
        img.save(processed_cover, "JPEG", quality=95)
    
    # 直接覆蓋 EPUB 內原本的所有封面圖片
    replaced_count = 0
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_lower = file.lower()
            if "cover" in file_lower and file_lower.endswith(('.jpg', '.jpeg', '.png')):
                target_path = os.path.join(root, file)
                shutil.copy(processed_cover, target_path)
                replaced_count += 1
                
    print(f"成功將原始圖片替換至 {replaced_count} 個封面資源中！")

    # 重新打包，輸出檔名與原檔名完全一致
    os.makedirs(os.path.dirname(output_epub_path), exist_ok=True)
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
    if os.path.exists(processed_cover):
        os.remove(processed_cover)
    print(f"處理完成！已輸出檔名：{output_epub_path}")

if __name__ == "__main__":
    # 自動尋找資料夾內的 EPUB 與圖片
    epub_files = [f for f in os.listdir('.') if f.endswith('.epub')]
    image_files = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    if epub_files and image_files:
        original_epub_name = epub_files[0]
        input_image = image_files[0]
        
        # 輸出到 output_dir 資料夾內，維持原始檔名
        output_epub_path = os.path.join("output_dir", original_epub_name)
        
        print(f"正在處理電子書: {original_epub_name}，使用封面: {input_image}")
        replace_epub_cover(original_epub_name, input_image, output_epub_path)
    else:
        print("未尋找到 .epub 檔案或圖片檔案！")
