import os
import sys
import platform
import subprocess
import webbrowser
from pathlib import Path

def create_required_directories():
    """创建应用所需的目录结构"""
    directories = ['temp', 'uploads', 'annotations', 'data']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    print("✓ 已创建必要目录")

def check_dependencies():
    """检查必要的Python依赖"""
    required_packages = ['flask', 'nibabel', 'numpy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"缺少以下依赖包: {', '.join(missing_packages)}")
        install = input("是否自动安装这些依赖? (y/n): ")
        if install.lower() == 'y':
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✓ 依赖安装完成")
        else:
            print("请手动安装依赖后再运行程序")
            sys.exit(1)
    else:
        print("✓ 所有依赖已安装")

def setup_static_files():
    """确保静态文件正确放置"""
    static_dir = Path('static')
    css_dir = static_dir / 'css'
    js_dir = static_dir / 'js'
    
    # 创建静态文件目录
    os.makedirs(css_dir, exist_ok=True)
    os.makedirs(js_dir, exist_ok=True)
    
    # 检查并复制CSS文件
    css_source = Path('style.css')
    css_dest = css_dir / 'style.css'
    if css_source.exists() and not css_dest.exists():
        with open(css_source, 'r', encoding='utf-8') as src, open(css_dest, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        print(f"✓ 已复制CSS文件到 {css_dest}")
    
    # 检查并复制JS文件
    js_source = Path('viewer.js')
    js_dest = js_dir / 'viewer.js'
    if js_source.exists() and not js_dest.exists():
        with open(js_source, 'r', encoding='utf-8') as src, open(js_dest, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        print(f"✓ 已复制JavaScript文件到 {js_dest}")

def start_server(host='127.0.0.1', port=5000, debug=True):
    """启动Flask服务器"""
    # 检查是否在Windows上运行
    is_windows = platform.system().lower() == 'windows'
    
    print(f"\n启动服务器于 http://{host}:{port}")
    print("按 Ctrl+C 停止服务器")
    
    # 确定用于浏览器访问的URL
    browser_url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}"
    print(f"请通过以下地址访问: {browser_url}")
    
    # 打开浏览器
    try:
        webbrowser.open(browser_url)
    except Exception as e:
        print(f"自动打开浏览器失败: {e}")
    
    # 导入并运行Flask应用
    try:
        from app import app
        print("成功导入Flask应用")
        app.run(host=host, port=port, debug=False)
    except ImportError as e:
        print(f"导入Flask应用失败: {e}")
        print("请确认app.py文件在当前目录下")
    except Exception as e:
        print(f"启动服务器失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("=" * 50)
    print("医学影像查看器启动程序")
    print("=" * 50)
    
    # 检测操作系统
    system = platform.system()
    print(f"检测到操作系统: {system}")
    
    # 创建必要目录
    create_required_directories()
    
    # 检查依赖
    check_dependencies()
    
    # 设置静态文件
    setup_static_files()
    
    # 确定主机地址
    # 在本地开发时使用localhost，如果需要在局域网访问则使用0.0.0.0
    host = '127.0.0.1'  # 默认只允许本机访问
    
    # 询问是否允许局域网访问
    network_access = input("是否允许局域网内其他设备访问? (y/n): ")
    if network_access.lower() == 'y':
        host = '0.0.0.0'
        print("已启用局域网访问模式")
    
    # 启动服务器
    start_server(host=host)

if __name__ == "__main__":
    main()