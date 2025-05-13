from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "<h1>医学影像查看器测试页面</h1>"

if __name__ == '__main__':
    app.run(debug=True)