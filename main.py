import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QFile


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

    from phototool.views.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
