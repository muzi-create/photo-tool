# PhotoTool

面向个人的本地图片处理工具，基于 Reflex、Pillow 和 Tauri 开发。支持浏览器开发、Python 原生窗口预览和 Windows 安装包；图片由本机 Python 服务处理。

版本更新与变化见 [CHANGELOG.md](CHANGELOG.md)。

## 功能

- 编辑图片并导出为 JPEG、PNG、WEBP、BMP；多张图片自动打包为 ZIP。
- 调整输出质量、尺寸和宽高比，支持旋转、翻转、裁剪、撤销裁剪及恢复原图。
- 在图片上添加多个文字说明框，支持中文、换行、拖动定位和边角调整大小、字号、加粗、对齐、文字/背景颜色及透明背景；导出时将文字合成到图片中。
- 生成 Windows、iOS、Android、Favicon 等预设图标，支持自定义尺寸、多尺寸 ICO、PNG 和 ZIP。
- 为图标添加圆形或圆角矩形遮罩；圆形半径自动取各输出尺寸的一半。
- 桌面版生成结果后弹出保存窗口；浏览器版遵循浏览器的下载设置。
- 生产构建已关闭右下角的“Built with Reflex”标识。

ICO 仅支持不超过 256 px 的尺寸。选择 PNG 时，每个勾选尺寸生成一个文件；选择 ICO 时，所有有效尺寸写入一个 `icon.ico`；选择 ICO + PNG 时，两种格式合并为 ZIP。未选择尺寸时无法生成。

## 环境准备

日常开发需要 Python 3.10+ 和 Node.js（建议 22 LTS）。制作 Windows 安装包还需要 Rust stable、Visual Studio C++ 构建工具和 Windows SDK；运行桌面窗口需要 Microsoft Edge WebView2 Runtime。

在项目根目录打开 PowerShell：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m phototool.dependencies
npm ci
```

每次打开新终端时，先激活 `venv`。如果 PowerShell 阻止激活脚本，可仅为当前终端设置：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

`requirements.txt` 管理 Python 依赖；`package-lock.json` 固定 Tauri CLI 依赖；`src-tauri/Cargo.lock` 固定 Rust 依赖。Reflex 首次编译时会生成 `.web/` 并安装前端依赖。

Python 依赖显式包含 `SQLAlchemy[asyncio]`，以安装 Reflex 异步运行所需的 `greenlet`。SQLAlchemy 2.1 默认不再安装它；桌面打包配置也会包含它的原生扩展。
桌面服务直接使用的 `uvicorn` 和 `websockets` 同样由 `requirements.txt` 安装，避免依赖其他包间接提供。

### 依赖声明与导入检查

安装包版本、需要导入的模块和递归收集的模块包统一在 `requirements.txt` 维护。导入配置使用注释，保持兼容标准 `pip install -r requirements.txt`：

```text
# import: PIL.Image PIL.ImageFilter
Pillow>=10.0.0
```

| 注释配置 | 用途 |
| --- | --- |
| `# import: 模块名 ...` | 检查后台服务必需模块，并交给 PyInstaller 收集。 |
| `# collect-submodules: 包名 ...` | 递归收集并检查整个组件包；用于 Reflex 动态组件。 |
| `# preview-import: 模块名 ...` | 检查 Python 原生窗口预览使用的依赖。 |
| `# build-import: 模块名 ...` | 检查打包工具使用的依赖。 |

新增外部依赖时，同时添加安装包声明及对应的导入注释；包名与导入名可能不同，例如 `Pillow` 对应 `PIL`、`pywebview` 对应 `webview`。`greenlet._greenlet` 等原生扩展也需要列入检查。

执行 `python -m phototool.dependencies` 或 `npm run web:check` 检查所有配置的导入（包括递归组件）及 `pip check`。可用 `--profile runtime`、`preview` 或 `build` 只检查对应入口。失败时会列出无法导入的模块，并给出使用当前 Python 解释器安装依赖的完整命令。

## 开发与运行

### 浏览器开发

激活虚拟环境后执行：

```powershell
python -m reflex run
```

访问 [http://127.0.0.1:3000](http://127.0.0.1:3000)。Reflex 后端默认使用 8000 端口；保持终端打开，按 `Ctrl+C` 停止服务。页面和状态代码修改后会自动刷新。

也可以使用 npm 快捷命令：

```powershell
npm run web:setup
npm run web:start
```

`web:setup` 调用 `setup_python.ps1` 创建或复用 `venv`，安装依赖并完成全部导入检查；`web:start` 和 `web:compile` 在运行前检查后台依赖。`npm run web:bootstrap` 可连续完成安装检查和启动。

### Python 原生窗口预览

此入口用于从源码预览桌面窗口，使用 PyWebView。先导出前端，再启动：

```powershell
.\build_frontend.ps1
python main.py
```

`build_frontend.ps1` 会导出生产前端、将事件和上传地址修正为当前页面地址，并生成桌面加载页。请使用此脚本完成导出，避免动态端口下的按钮和上传连接到错误服务。

源码预览默认使用本机 8765 端口。关闭窗口后，进程及本地服务一同结束。
`python main.py` 会先检查后台及 PyWebView 依赖；检查失败时停止启动并显示修复命令。

## Windows 打包

激活已安装依赖的虚拟环境，并在项目根目录执行：

```powershell
.\build_tauri.ps1
```

如果当前终端禁止运行脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_tauri.ps1
```

也可在已激活虚拟环境的终端执行 `npm run desktop:build` 或 `npm run package`。

构建流程为：检查依赖导入 → 导出前端 → 使用 `sidecar.spec` 重新生成 Python Sidecar → 复制 Sidecar 资源 → 构建 Tauri 窗口及 NSIS 安装包。构建脚本优先使用项目 `venv`，不存在时使用当前 `python`。每次都会重新生成 Sidecar，确保安装包包含最新 Python 代码和前端。

`sidecar.spec` 直接读取 `requirements.txt` 中的导入配置，不再单独维护隐藏导入列表；缺失模块或递归组件无法导入时立即停止打包。依赖安装仍由环境准备步骤完成。

交付文件为：

```text
src-tauri/target/release/bundle/nsis/PhotoTool_1.0.0_x64-setup.exe
```

版本号随 `src-tauri/tauri.conf.json` 的 `version` 变化。双击安装后，从开始菜单或安装目录中的 `phototool-desktop.exe` 启动。桌面版和 Python 原生窗口预览均默认全屏打开；按 `F11` 切换全屏，按 `Esc` 返回普通窗口。普通窗口默认 1440 × 920，最小 1100 × 720。

`PhotoToolSidecar.exe` 是窗口自动调用的后台服务，直接双击不会显示界面。修改源码后，需要重新打包并安装才能更新已安装的软件。

### 构建文件的作用

| 路径 | 用途 |
| --- | --- |
| `src-tauri/target/release/bundle/nsis/` | 对外交付的安装包。 |
| `build/sidecar-output/PhotoToolSidecar.exe` | PyInstaller 生成的后台服务。 |
| `build/tauri-resources/sidecar/PhotoToolSidecar.exe` | Tauri 打包使用的资源副本。 |
| `.web/build/client/` | 导出的 HTML、JavaScript、CSS 和加载页。 |
| `src-tauri/target/` 的其他内容 | Rust 构建缓存、中间文件和未安装的程序。 |

安装后的窗口启动 Sidecar，由 Sidecar 在本机随机端口提供界面与图片处理服务。点击窗口关闭按钮时可选择：

- **最小化到系统托盘**：隐藏主窗口，保留当前工作和后台服务。单击托盘图标或在托盘菜单选择“打开 PhotoTool”即可恢复。
- **退出程序**：关闭应用并结束 Sidecar 进程树；也可从托盘右键菜单直接退出。
- **取消**：返回当前窗口。

上述关闭选择适用于 Tauri 打包版；`python main.py` 的 PyWebView 预览仍在关闭窗口时结束。后台服务和退出时的清理命令均以无控制台窗口方式运行。

## 测试与检查

```powershell
python -m unittest discover -s tests -v
node --test tests/test_text_interactions.js
node --check assets/crop_interactions.js
```

测试覆盖依赖清单解析、多项导入失败报告、实际后台模块导入、图片变换、透明度处理、小尺寸 PNG、多尺寸 ICO、SQLAlchemy 异步运行、静态资源 MIME 类型和打包环境下的 Reflex 应用查找。

检查 Rust 代码时，需先通过完整打包流程生成 Sidecar 资源，然后执行：

```powershell
cargo check --locked --manifest-path src-tauri/Cargo.toml
```

## 项目结构

```text
PhotoTool/
├── assets/
│   ├── crop_interactions.js          # 裁剪拖拽与前端状态同步
│   ├── styles.css                    # 页面样式
│   └── img/logo.ico                  # Windows 应用与安装包图标
├── phototool/
│   ├── core/
│   │   ├── conversion.py             # 图片变换与格式转换
│   │   └── image_converter.py        # 图标生成、遮罩及图片处理
│   ├── desktop_launcher.py           # PyWebView 源码预览窗口
│   ├── dependencies.py               # 读取统一清单、导入检查与打包模块收集
│   ├── desktop_server.py             # 源码预览使用的本地服务
│   ├── patch_exported_frontend.py    # 导出后修正后端连接地址
│   ├── phototool.py                  # Reflex 页面组件
│   ├── sidecar.py                    # Tauri 调用的 Python 服务入口
│   └── web_state.py                  # 页面状态、上传与下载事件
├── src-tauri/
│   ├── src/main.rs                   # 窗口与 Sidecar 生命周期
│   ├── src/downloads.rs              # Windows 保存位置选择
│   ├── src/tray.rs                   # 关闭选择、托盘菜单与窗口恢复
│   ├── nsis-hooks.nsh                # 安装升级时刷新旧 Sidecar
│   └── tauri.conf.json               # 桌面窗口和安装包配置
├── tests/                            # Python 回归测试
├── build_frontend.ps1                # 导出并修正桌面前端
├── build_tauri.ps1                   # 完整 Windows 打包入口
├── main.py                           # Python 原生窗口预览入口
├── rxconfig.py                       # Reflex 配置与标识开关
├── sidecar.spec                      # 当前 PyInstaller Sidecar 配置
├── requirements.txt                  # Python 依赖与导入配置
├── setup_python.ps1                  # 安装 Python 依赖并检查所有导入
└── package.json                      # npm 快捷命令与 Tauri CLI 依赖
```

当前界面使用 Reflex。旧 PyQt5 界面、旧版整包 PyInstaller 入口及仅供旧界面使用的资源已移除。

## 生成文件与清理

以下目录由工具生成，已加入 Git 忽略规则：

| 路径 | 是否可以清理及恢复方式 |
| --- | --- |
| `__pycache__/`、`.pytest_cache/`、`.ruff_cache/` | 可清理；执行代码或检查时自动生成。 |
| `build/`、`dist/` | 可清理；`build_tauri.ps1` 重建当前打包资源。 |
| `src-tauri/target/`、`src-tauri/gen/` | 可清理；Rust/Tauri 下次构建时重新生成。清理会同时删除本地安装包。 |
| `.web/` | 包含前端依赖、工具配置和导出页面；通常保留。需要重建时重新执行 Reflex 开发或前端导出。 |
| `node_modules/` | 当前 Tauri CLI 依赖；需要重装时执行 `npm ci`。 |
| `venv/` | 当前 Python 虚拟环境；需要重建时按“环境准备”安装依赖。 |
| `.states/`、`uploaded_files/`、`*.log` | 运行时状态、上传文件及诊断信息；清理前确认其中没有需要保留的数据。 |

执行缓存清理前先退出运行中的应用和构建进程。项目级编辑器设置保存在 `.idea/` 或 `.vscode/`，按个人需要保留。

## 常见问题

- **找不到 Reflex 或其他 Python 模块**：确认终端已激活 `venv`，再执行 `python -m pip install -r requirements.txt`。
- **提示 SQLAlchemy asyncio 缺少 greenlet**：在项目根目录执行 `.\venv\Scripts\python.exe -m pip install -r requirements.txt`，然后重启服务。安装版出现此错误时，需在依赖安装完成后执行 `build_tauri.ps1` 重新打包并安装；修改本机 Python 环境不会更新已有 exe。
- **端口被占用**：浏览器开发检查 3000/8000，Python 窗口预览检查 8765；关闭先前启动的服务。安装版会自动选择空闲端口。
- **生成后找不到文件**：桌面版需在保存窗口中确认位置；取消窗口会取消下载。浏览器版检查默认下载文件夹及浏览器下载记录。
- **打包后按钮或上传无响应**：使用完整的 `build_tauri.ps1` 重新打包，确保前端地址修正和最新 Sidecar 均已包含。
- **双击 Sidecar 没有窗口**：启动入口是安装后的 `phototool-desktop.exe`，源码预览入口是 `python main.py`。
- **更新源码后旧问题仍存在**：旧安装包和已安装程序不会自动更新；重新打包并安装最新安装包。

安装版诊断日志通常位于 `%LOCALAPPDATA%/PhotoTool/logs/`，包含 `desktop.log` 和 `sidecar.log`。Sidecar 日志目录不可写时会尝试临时目录等备用位置。
