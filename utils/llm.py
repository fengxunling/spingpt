import ollama
import re
import os
import sys

file_path = os.path.dirname(os.path.realpath(__file__))


def generate_napari_code(prompt):
    """Generate executable napari code"""
    
    # 新增意图判断prompt
    intent_response = ollama.chat(
        model='deepseek-r1:7b',
        messages=[{
            'role': 'user',
            'content': f"Determine if user intent is to adjust slice coordinates or other requests. Only return 'intent: adjust_slice' or 'intent: other', don't add other content. Input: {prompt}"
        }]
    )
    intent = intent_response['message']['content'].strip().lower()
    print(f'==intent={intent}')
    intent_match = re.search(r'(.*\W)?intent:\s*(\w+)(?!.*intent:\s*\w+)', 
                           intent, re.IGNORECASE | re.DOTALL)
    if intent_match:
        intent = intent_match.group(2).lower()  # 提取第二个分组
        print(f'==最后匹配到的意图: {intent}')
    else:
        intent = raw_response.lower()
        print('==未找到intent字段==')

    if 'adjust_slice' in intent:
        print(f'=adjust_slice!')
        cleaned_number = re.sub(r'\D*(\d+)\D*', r'\1', prompt)
        axis_match = re.search(r'[xyz]', prompt.lower())
        axis = axis_match.group(0) if axis_match else None
        try:
            return {'type': 'slice_adjustment', 'number': int(cleaned_number), 'axis': axis}
        except ValueError:
            return {'type': 'error', 'message': 'Invalid number format'}
    else:
        print(f'=others!')
        full_response = ollama.chat(
            model='deepseek-r1:7b',
            messages=[{
                'role': 'user',
                'content': prompt
            }]
        )
        return {'type': 'general_response', 'content': full_response['message']['content']}
    

def main():
    generated_code = generate_napari_code(prompt)


if __name__ == "__main__":
    main()
