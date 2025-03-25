import ollama
import re
import os
import sys

file_path = os.path.dirname(os.path.realpath(__file__))


def generate_napari_code(prompt):
    """Generate executable napari code"""
    # system_prompt = (
    #     "You are a control assistant for the napari medical image viewer. User instructions must include axis name and slice position.\n"
    #     "Response rules:\n"
    #     "Evaluate the most possible Python code and select the id of it\n\n"
    #     "Available variables:\n"
    #     "- x_slider: X-axis slice controller (range: 0-{x_max})\n"
    #     "- y_slider: Y-axis slice controller (range: 0-{y_max})\n"
    #     "- z_slider: Z-axis slice controller (range: 0-{z_max})\n\n"
    #     "Possible selections:\n"
    #     "x_slider.setValue, \n"
    #     "y_slider.setValue, id:2\n"
    #     "z_slider.setValue, id:3\n"
    #     "```"
    # ).format(
    #     x_max=100,  # needs to be dynamically set based on actual image dimensions
    #     y_max=100,
    #     z_max=100
    # )

    # Add instruction cleaning logic
    # extract number from the instruction
    cleaned_number = re.sub(r'\D*(\d+)\D*', r'\1', prompt)
    
    # extract the axis information (x/y/z)
    axis_match = re.search(r'[xyz]', prompt.lower())
    axis = axis_match.group(0) if axis_match else None
    
    print(f'cleaned_number: {cleaned_number}')
    print(f'axis: {axis}')

    # response = ollama.chat(
    #     model='deepseek-r1:7b',
    #     messages=[
    #         {'role': 'system', 'content': system_prompt},
    #         {'role': 'user', 'content': cleaned_prompt}
    #     ]
    # )
    
    try:
        # Return a tuple of number and axis (convert string to integer)
        return (int(cleaned_number), axis)  # Original code returned (cleaned_prompt, axis)
    except ValueError as e:
        return (0, None)  # Add error handling

def main():
    generated_code = generate_napari_code(prompt)


if __name__ == "__main__":
    main()
