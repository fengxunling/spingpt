# import ollama

# response = ollama.generate(model='deepseek-r1:7b',
# prompt='hello world!')
# print(response['response'])

import ollama
import re

def read_prompts(filename):
    """Read prompts enclosed in double quotes"""
    with open(filename, 'r') as f:
        content = f.read()
    # Use regular expression to match content within double quotes
    return re.findall(r'"([^"]*)"', content)

def generate_napari_code(prompt):
    """Generate executable napari code"""
    system_prompt = (
        "You are a medical image processing assistant. Please generate Python code that can be executed directly in napari based on user requirements."
        "The code should:\n"
        "1. Assume the image data is loaded as a numpy array\n"
        "2. Use napari's API for visualization operations\n"
        "3. Include necessary image processing steps\n"
        "4. Be enclosed in a ```python code block"
    )

    response = ollama.chat(
        model='deepseek-r1:7b',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ]
    )
    return response['message']['content']

def main():
    try:
        # Read prompts from file
        prompts = read_prompts('test_prompts.txt')
        
        # generate code for each prompt
        for i, prompt in enumerate(prompts, 1):
            print(f"\nProcessing Prompt {i}: {prompt}")
            
            generated_code = generate_napari_code(prompt)
            
            # extract code block
            code_block = re.search(r'```python(.*?)```', generated_code, re.DOTALL)
            if code_block:
                executable_code = code_block.group(1).strip()
                print(f"\nGenerated Code for Prompt {i}:\n{executable_code}")
                
                with open(f"generated_code_{i}.py", 'w') as f:
                    f.write(executable_code)
            else:
                print(f"No valid code block found in response for prompt {i}")

    except FileNotFoundError:
        print("Error: test_prompts.txt file not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()