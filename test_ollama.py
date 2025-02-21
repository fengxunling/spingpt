import ollama

response = ollama.generate(model='deepseek-r1:7b',
prompt='what is a qubit?')
print(response['response'])