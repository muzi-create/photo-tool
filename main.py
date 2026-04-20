import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QFile, QTimer


def main():
    # PyInstaller 打包后设置工作目录为 _MEIPASS，确保相对路径资源可访问
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))

    # 设置应用图标
    icon_path = os.path.join('assets', 'img', 'logo.ico')
    if QFile.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 显示启动画面
    from phototool.views.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()  # 立即刷新显示

    # 模拟加载进度
    def update_splash(progress, message=""):
        splash.set_progress(progress, message)

    # 阶段1: 加载资源
    update_splash(10, "加载资源...")
    app.processEvents()
    QTimer.singleShot(100, lambda: None)  # 让UI有机会刷新

    # 阶段2: 初始化转换器
    update_splash(30, "初始化转换器...")
    from phototool.core.image_converter import ImageConverter
    _ = ImageConverter  # 预加载模块
    app.processEvents()

    # 阶段3: 加载样式
    update_splash(50, "加载界面样式...")
    from phototool.ui.styles import StyleSheet
    _ = StyleSheet
    app.processEvents()

    # 阶段4: 初始化主窗口
    update_splash(70, "初始化主窗口...")
    app.processEvents()

    from phototool.views.main_window import MainWindow
    window = MainWindow()
    update_splash(90, "准备就绪...")
    app.processEvents()

    # 阶段5: 完成加载
    update_splash(100, "启动完成!")
    QTimer.singleShot(200, lambda: None)  # 短暂显示100%状态
    app.processEvents()

    # 关闭启动画面并显示主窗口
    splash.finish(window)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
