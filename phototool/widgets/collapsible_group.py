"""
可折叠的 GroupBox 控件
支持展开/折叠动画效果
"""

from PyQt5.QtWidgets import QGroupBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from .svg_toggle_btn import SvgToggleBtn


class CollapsibleGroupBox(QGroupBox):
    """可折叠的 GroupBox"""

    def __init__(self, title, parent=None, expanded=True):
        super().__init__(title, parent)
        self._expanded = expanded
        self._content_widget = None
        self._toggle_btn = None
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self._setup_toggle()
        self._update_state()

    def setContentWidget(self, widget):
        """设置内容控件"""
        self._content_widget = widget
        self._main_layout.addWidget(widget)
        # 限制内容widget的最大宽度，防止超出滚动区域
        self._update_content_width()
        self._update_state()

    def _update_content_width(self):
        """限制内容widget的宽度"""
        if self._content_widget:
            # 设置内容widget的最大宽度为500
            self._content_widget.setMaximumWidth(480)

    def _update_state(self):
        # 更新按钮图标 (SVG) - 展开时旋转180度（箭头朝上），折叠时保持原样（箭头朝下）
        self._toggle_btn.set_rotated(self._expanded)
        # 显示/隐藏内容
        if self._content_widget:
            self._content_widget.setVisible(self._expanded)

    def _setup_toggle(self):
        # 创建标题栏容器
        header_widget = QWidget()
        header_widget.setObjectName("collapsibleHeader")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(5)

        # 创建折叠/展开按钮 (SVG 图标)
        self._toggle_btn = SvgToggleBtn()
        self._toggle_btn.setFixedSize(20, 20)
        self._toggle_btn.clicked.connect(self.toggle)
        header_layout.addWidget(self._toggle_btn)

        # 标题
        title_label = QLabel(self.title())
        title_label.setObjectName("collapsibleTitle")
        title_label.setStyleSheet("""
            QLabel#collapsibleTitle {
                font-weight: bold;
                color: #4a9eff;
                font-size: 13px;
            }
        """)
        title_layout = QVBoxLayout()
        title_layout.addWidget(title_label)
        header_layout.addLayout(title_layout, 1)

        header_layout.addStretch()

        self._main_layout.addWidget(header_widget)

    def toggle(self):
        """切换折叠/展开状态"""
        self._expanded = not self._expanded
        self._update_state()

    def isExpanded(self):
        return self._expanded

    def setExpanded(self, expanded):
        self._expanded = expanded
        self._update_state()
