# PhotoTool

图片批量转换工具 —— 支持格式转换、质量压缩、尺寸缩放、图标生成等功能。

## 功能特性

- **格式转换**: 支持 JPEG / PNG / WEBP / BMP 格式互转
- **质量压缩**: 可调节输出质量，支持目标文件大小自动压缩
- **尺寸缩放**: 支持自定义尺寸，可保持宽高比
- **旋转翻转**: 90° 旋转、水平/垂直翻转
- **裁剪功能**: 自由选区、固定尺寸、锁定比例、预设尺寸
- **图标生成**: 支持 iOS / Android / Windows / Favicon 等多平台图标预设

## 项目结构

```
PhotoTool/
├── main.py                          # 应用入口
├── phototool/                       # 主包
│   ├── __init__.py
│   ├── core/                        # 核心业务逻辑
│   │   ├── __init__.py
│   │   └── image_converter.py
│   ├── ui/                          # 样式主题
│   │   ├── __init__.py
│   │   └── styles.py
│   ├── widgets/                     # 自定义控件
│   │   ├── __init__.py
│   │   ├── collapsible_group.py
│   │   ├── crop_rubber_band.py
│   │   ├── drop_area.py
│   │   └── svg_toggle_btn.py
│   ├── views/                       # 视图
│   │   ├── __init__.py
│   │   └── main_window.py
│   └── threads/                     # 工作线程
│       ├── __init__.py
│       ├── conversion_thread.py
│       ├── image_worker.py
│       └── image_compress_worker.py
├── assets/                          # 静态资源
│   └── img/
│       └── down.svg
├── PhotoTool.spec                   # PyInstaller 打包配置
├── requirements.txt                 # 依赖
├── .gitignore
└── README.md
```

## 安装与运行

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

## 打包

pip install pyinstaller
pyinstaller PhotoTool.spec
```

## 技术栈

- Python 3.8+
- PyQt5 - GUI 框架
- Pillow - 图片处理库
- PyInstaller - 打包工具

## License

MIT
