# PhotoTool

基于 **Reflex + Pillow** 的企业级图片处理工作台，采用白蓝配色与响应式 Web 界面。图片在本机 Reflex 服务内处理，不依赖外部云端接口。

## 一键启动（Windows PowerShell）

在项目根目录打开 PowerShell，直接粘贴并运行以下命令。首次运行会创建 `venv`、安装依赖，然后启动浏览器开发服务；后续运行会复用已有环境。

```powershell
if (-not (Test-Path .\venv\Scripts\python.exe)) { python -m venv venv }; .\venv\Scripts\python.exe -m pip install -r requirements.txt; .\venv\Scripts\python.exe -m reflex run
```

如果已完成环境配置，使用以下命令即可快速启动：

```powershell
.\venv\Scripts\python.exe -m reflex run
```

启动完成后访问 http://127.0.0.1:3000 。保持终端窗口打开，按 `Ctrl+C` 停止服务。

## 功能

- 格式转换：JPEG / PNG / WEBP / BMP，支持批量结果 ZIP 下载
- 质量与尺寸：质量控制、自定义宽高、保持宽高比；上传后默认同步原图像素尺寸
- 旋转翻转：90° 旋转、水平/垂直翻转和实时预览；预览以显示尺寸处理，大图操作更流畅
- 裁剪：自由选区、固定尺寸、锁定比例、预设尺寸、撤销与恢复原图
- 图标生成：iOS / Android / Windows / Favicon 等多平台预设、可勾选生成尺寸、ICO/PNG 输出和圆角遮罩

### 图标生成说明

- 在“生成尺寸”中勾选需要输出的尺寸；可使用“全选”和“清除”。未选择任何尺寸时不能生成。
- 选择 `PNG` 时，会为每个勾选尺寸生成一个 PNG；选择 `ICO (多尺寸)` 时，会将勾选的有效尺寸合并为一个 `icon.ico`；选择 `ICO + PNG` 时会同时生成两类文件并下载 ZIP。
- ICO 格式仅支持不超过 `256 × 256 px` 的尺寸。若只勾选了更大的尺寸，请改用 PNG，或同时勾选至少一个不超过 256 px 的尺寸。
- 圆角遮罩中，“圆角矩形”支持手动设置半径；“圆形”会禁用半径输入并自动使用各输出尺寸的一半作为半径。

## 从源码启动（推荐）

下面的方式直接运行项目源码，**不需要**安装或启动 `dist/`、`src-tauri/target/` 中的打包产物。

### 1. 准备环境

在项目根目录打开 PowerShell：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果 PowerShell 阻止激活虚拟环境，可只对当前终端放开限制后重试：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\venv\Scripts\Activate.ps1
```

### 2. 启动浏览器开发模式

```powershell
python -m reflex run
```

首次启动会安装/生成前端依赖，耗时会稍长。启动完成后，在浏览器访问：

- 前端页面：http://127.0.0.1:3000
- Reflex 后端：http://127.0.0.1:8000

保持该终端窗口打开；按 `Ctrl+C` 可停止服务。修改 Python、页面或样式文件后，Reflex 会自动重新编译或刷新页面。

### 3. 可选：以本地原生窗口运行源码

此模式使用 Python + PyWebView，不是 Tauri 打包版。先生成本地静态前端资源，再启动窗口：

```powershell
python -m reflex export --frontend-only --no-zip
python main.py
```

窗口关闭后，本地服务会随 Python 进程结束。若端口 `8765` 已被占用，请先关闭先前运行的 PhotoTool/Sidecar 进程。

### 常见问题

- `No module named reflex`：确认已激活 `venv`，再执行 `python -m pip install -r requirements.txt`。
- `3000` 或 `8000` 端口被占用：停止占用该端口的开发服务，再重新执行 `python -m reflex run`。
- 不要双击 `src-tauri\target\release\phototool-desktop.exe` 来开发；它依赖安装包附带的资源。开发时请使用上面的 `python -m reflex run`。

## 原有简要启动命令

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m reflex run
```

`python -m reflex run` 用于浏览器开发模式；`python main.py` 需要先执行一次前端导出，详见“从源码启动”。

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

构建完成后，交付和启动的文件是：

```text
src-tauri\target\release\bundle\nsis\PhotoTool_1.0.0_x64-setup.exe
```

请安装它，并从开始菜单或安装目录的 `phototool-desktop.exe` 启动。`PhotoToolSidecar.exe` 是仅供桌面壳调用的本地 HTTP 后端，**直接双击时不会打开窗口或页面**；任务管理器中出现它的进程是预期行为，不能作为用户启动入口。

### 打包产物路径与用途

下表中的路径均相对于项目根目录。除安装包外，其余内容均是构建中间产物或安装后的内部资源，通常不需要交付给最终用户。

| 路径 | 作用 | 是否直接交付/启动 |
| --- | --- | --- |
| `src-tauri\target\release\bundle\nsis\PhotoTool_1.0.0_x64-setup.exe` | Windows NSIS 安装包。它包含 Tauri 桌面窗口、前端文件和 Python Sidecar。 | **是。**交付给用户并双击安装。 |
| `C:\Users\<用户名>\AppData\Local\PhotoTool\phototool-desktop.exe` | 安装程序释放的实际桌面应用；开始菜单快捷方式也指向此文件。 | **是。**安装后由快捷方式或此文件启动。 |
| `build\sidecar-output\PhotoToolSidecar.exe` | PyInstaller 生成的 Python 本地服务。构建脚本临时使用它来制作安装包。 | 否。无窗口，不能单独作为应用启动。 |
| `build\tauri-resources\sidecar\PhotoToolSidecar.exe` | 供 Tauri 复制进安装包的 Sidecar 资源副本。 | 否。仅由 `phototool-desktop.exe` 自动启动。 |
| `dist\PhotoToolSidecar.exe` 或 `dist\sidecar\PhotoToolSidecar.exe` | 旧版构建留下的 Sidecar 产物；新构建不会再将它作为顶层交付文件。 | 否。可忽略，不要发给用户作为启动程序。 |
| `.web\build\client\` | Reflex 导出的静态前端（HTML、JavaScript、CSS 等），由安装包包含。 | 否。构建输入/资源目录。 |
| `src-tauri\target\release\phototool-desktop.exe` | 未安装的 Rust/Tauri 构建输出，缺少安装包布局下的资源时可能无法正常运行。 | 否。请使用 NSIS 安装包。 |
| `build\sidecar\` 与 `src-tauri\target\` | PyInstaller/Rust 的缓存、对象文件与构建日志。 | 否。用于加速下次构建。 |

启动链路如下：`phototool-desktop.exe` 创建窗口并启动 `PhotoToolSidecar.exe`；Sidecar 在本机随机端口提供页面；窗口连接该本地地址后显示界面。因而只看到 Sidecar 进程但没有窗口，通常表示启动了内部服务文件，而不是用户入口。

如果 PowerShell 禁止执行脚本，也可以直接执行：

```powershell
python -m reflex export --frontend-only --no-zip
python -m PyInstaller --clean --noconfirm --distpath build\sidecar-output sidecar.spec
New-Item -ItemType Directory -Force -Path build\tauri-resources\sidecar
Copy-Item build\sidecar-output\PhotoToolSidecar.exe build\tauri-resources\sidecar\PhotoToolSidecar.exe
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
