import os
import json
import glob
import re
from datetime import datetime

def parse_log_file(log_path):
    """Parse log file and extract rectangle annotation information"""
    annotations = []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract all rectangle annotations
        rectangle_pattern = r'\[Rectangle (\d+) Annotation\].*?\nPhysical coordinates: (\[\[.*?\]\])'
        matches = re.findall(rectangle_pattern, content, re.DOTALL)
        
        if not matches:
            # Try another format matching
            rectangle_pattern = r'\[Rectangle (\d+) Annotation\] (\d+:\d+:\d+)\nPhysical coordinates: (\[\[.*?\]\])'
            matches = re.findall(rectangle_pattern, content, re.DOTALL)
            if matches:
                # Convert to the same structure as before
                matches = [(rect_id, coords) for rect_id, _, coords in matches]
        
        for rect_id, coords in matches:
            # Create unique rectangle_id
            log_basename = os.path.basename(log_path)
            rectangle_id = f"rect_{rect_id}"
            
            # Extract coordinate string
            coords_str = coords.strip()
            
            annotations.append({
                "rectangle_id": rectangle_id,
                "coordinate": coords_str,
                "note": f"from {log_basename}"
            })
    except Exception as e:
        print(f"Error parsing log file {log_path}: {e}")
    
    return annotations

def generate_results_json():
    """
    Generate results.json file containing rectangle annotation information from all log.txt files
    """
    # Project root directory and data directory
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    recorded_materials_dir = os.path.join(project_dir, 'recorded_materials')
    output_file = os.path.join(recorded_materials_dir, 'results.json')
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Find all log files
    results = []
    log_files = glob.glob(os.path.join(recorded_materials_dir, '*_log.txt'))
    
    for log_file in log_files:
        # Extract image ID from filename
        image_id = os.path.basename(log_file).replace('_log.txt', '')
        
        # Parse log file
        annotations = parse_log_file(log_file)
        
        if annotations:
            for annotation in annotations:
                # Create entry
                entry = {
                    "id": image_id,
                    "image_source": [
                        f"/data/{image_id}.nii.gz"
                    ],
                    "rectangle_id": annotation["rectangle_id"],
                    "coordinate": annotation["coordinate"],
                    "annotation": annotation["note"]
                }
                results.append(entry)
    
    # Write JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
    
    print(f"Generated results.json file with {len(results)} entries")
    print(f"File saved at: {output_file}")

if __name__ == "__main__":
    generate_results_json()