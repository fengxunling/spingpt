import os
import json
import glob
import re
from datetime import datetime

def extract_id_from_log_filename(log_filename):
    """从日志文件名中提取图像ID"""
    # 示例: 20250415_1630_26_sub-01_ses-01_T2w.nii_log.txt
    # 提取 sub-01_ses-01_T2w.nii 部分
    match = re.search(r'(\d+_\d+_\d+_)(.+?)(_log\.txt)', log_filename)
    if match:
        return match.group(2)  # 返回中间部分
    return None

def parse_log_file(log_path):
    """解析日志文件，提取矩形标注信息"""
    annotations = []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 提取所有矩形标注
        rectangle_pattern = r'\[Rectangle Annotation\].*?\nPhysical coordinates: \[(.*?)\]'
        matches = re.findall(rectangle_pattern, content, re.DOTALL)
        
        for i, match in enumerate(matches):
            # 提取坐标
            coords = match.strip()
            if coords:
                # 创建唯一的rectangle_id
                rectangle_id = f"rect_{os.path.basename(log_path)}_{i+1}"
                annotations.append({
                    "rectangle_id": rectangle_id,
                    "coordinate": coords
                })
    except Exception as e:
        print(f"解析日志文件 {log_path} 时出错: {e}")
    
    return annotations

def generate_results_json():
    """
    生成 results.json 文件，包含 data 目录中所有 .nii.gz 文件的条目
    并从日志文件中提取矩形标注信息
    """
    # 项目根目录和数据目录
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_dir = os.path.join(project_dir, 'data')
    logs_dir = os.path.join(project_dir, 'recorded_materials')
    output_file = os.path.join(logs_dir, 'results.json')
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 查找所有日志文件
    log_files = {}
    for log_file in glob.glob(os.path.join(logs_dir, '*_log.txt')):
        image_id = extract_id_from_log_filename(os.path.basename(log_file))
        if image_id:
            if image_id not in log_files:
                log_files[image_id] = []
            log_files[image_id].append(log_file)
    
    # 查找所有 .nii.gz 文件
    results = []
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith('.nii.gz'):
                # 获取文件的完整路径
                file_path = os.path.join(root, file)
                
                # 计算相对于项目根目录的路径
                rel_path = os.path.relpath(file_path, project_dir)
                # 转换为 Unix 风格路径（使用正斜杠）
                rel_path = rel_path.replace('\\', '/')
                
                # 创建 ID（将路径中的 / 替换为 _）
                file_id = rel_path.replace('/', '_')
                
                # 检查是否有对应的日志文件
                matching_logs = []
                # 尝试直接匹配文件名
                if file in log_files:
                    matching_logs = log_files[file]
                # 尝试匹配不带扩展名的文件名
                elif os.path.splitext(file)[0] in log_files:
                    matching_logs = log_files[os.path.splitext(file)[0]]
                
                if matching_logs:
                    # 如果有对应的日志文件，为每个矩形标注创建一个条目
                    for log_path in matching_logs:
                        annotations = parse_log_file(log_path)
                        
                        if annotations:
                            for annotation in annotations:
                                # 创建条目
                                entry = {
                                    "id": file_id,
                                    "image_source": [
                                        f"/{rel_path}"
                                    ],
                                    "rectangle_id": annotation["rectangle_id"],
                                    "coordinate": annotation["coordinate"],
                                    "annotation": f"/recorded_materials/{file_id}_transcription.txt",
                                }
                                results.append(entry)
                        else:
                            # 如果没有提取到标注，创建一个默认条目
                            entry = {
                                "id": file_id,
                                "image_source": [
                                    f"/{rel_path}"
                                ],
                                "rectangle_id": "",
                                "coordinate": "(92,69), (107,96)",
                                "annotation": f"/recorded_materials/{file_id}_transcription.txt",
                            }
                            results.append(entry)
                else:
                    # 如果没有对应的日志文件，创建一个默认条目
                    entry = {
                        "id": file_id,
                        "image_source": [
                            f"/{rel_path}"
                        ],
                        "rectangle_id": "",
                        "coordinate": "(92,69), (107,96)",
                        "annotation": f"/recorded_materials/{file_id}_transcription.txt",
                    }
                    results.append(entry)
    
    # 写入 JSON 文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
    
    print(f"已生成 results.json 文件，包含 {len(results)} 个条目")
    print(f"文件保存在: {output_file}")

if __name__ == "__main__":
    generate_results_json()