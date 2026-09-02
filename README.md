# PhotoTool

基于 **Reflex + Pillow** 的企业级图片处理工作台，采用白蓝配色与响应式 Web 界面。图片在本机 Reflex 服务内处理，不依赖外部云端接口。

## 功能

- 格式转换：JPEG / PNG / WEBP / BMP，支持批量结果 ZIP 下载
- 质量与尺寸：质量控制、自定义宽高、保持宽高比
- 旋转翻转：90° 旋转、水平/垂直翻转和实时预览
- 裁剪：自由选区、固定尺寸、锁定比例、预设尺寸、撤销与恢复原图
- 图标生成：iOS / Android / Windows / Favicon 等多平台预设、ICO/PNG 输出和圆角遮罩

## 安装与运行

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
reflex run
```

也可以使用兼容入口：

```bash
python main.py
```

`reflex run` 用于浏览器开发模式；`python main.py` 会打开原生 Windows 桌面窗口，默认大小为 1440 × 920，最小尺寸为 1100 × 720。

## 测试与构建

```bash
python -m unittest discover -s tests -v
reflex compile
reflex export
```

## Windows 桌面打包（Tauri + Python Sidecar）

在 Windows Python 环境执行：

```powershell
pip install -r requirements.txt
npm install
.\build_tauri.ps1
```

软件拆分为三个独立层级：

1. `src-tauri/`：Rust/Tauri 原生 Windows 窗口、生命周期与 Sidecar 启停。
2. `phototool/sidecar.py`：Python + Uvicorn + Reflex 后端，调用 Pillow 核心处理图片。
3. `.web/build/client/`：Reflex 编译后的前端静态资源，负责白蓝企业级页面和交互。

打包结果为 Tauri NSIS 安装包和 Windows 可执行文件。构建脚本会先编译前端，再用 PyInstaller 生成 `PhotoToolSidecar.exe`，最后由 Tauri 将 Sidecar、静态页面和图标打包进安装程序。启动后默认窗口为 1440 × 920，最小尺寸为 1100 × 720，并居中显示；关闭窗口时 Tauri 会终止 Sidecar。

如果 PowerShell 禁止执行脚本，也可以直接执行：

```powershell
python -m reflex compile
python -m PyInstaller --clean --noconfirm sidecar.spec
npx tauri build
```

## 项目结构

```text
PhotoTool/
├── main.py                     # 本地启动入口
├── rxconfig.py                 # Reflex 配置
├── assets/
│   ├── styles.css              # 企业级白蓝主题
│   └── crop_interactions.js    # 裁剪拖动与缩放交互
├── phototool/
│   ├── phototool.py            # Reflex 页面与组件
│   ├── web_state.py            # 页面状态与业务适配
│   └── core/                   # UI 无关的 Pillow 处理核心
└── tests/                      # 核心处理测试
```

## 技术栈

- Python 3.10+
- Reflex 0.8.x
- Pillow 10+

## License

MIT
