"""
图片批量转换工具 - PyQt5 主窗口
主界面布局与交互逻辑
"""

import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QPushButton, QLabel, QSpinBox, QComboBox,
    QCheckBox, QGroupBox, QProgressBar, QFileDialog, QMessageBox,
    QApplication, QSlider, QFrame, QSizePolicy, QStatusBar, QButtonGroup,
    QRadioButton, QListWidget, QStackedLayout, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QFont, QPixmap, QTransform

from phototool.core.image_converter import ImageConverter
from phototool.ui.styles import StyleSheet
from phototool.widgets import CollapsibleGroupBox, CropRubberBand, DropArea
from phototool.threads.conversion_thread import ConversionThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files = []
        self.thread = None
        # 变换状态
        self._flip_h = False
        self._flip_v = False
        self._rotation_angle = 0
        self._original_pixmap = None
        self._original_pixmap_backup = None
        # 裁剪状态
        self._crop_enabled = False
        self._crop_rect = None
        self._crop_mode = "free"
        self._crop_applied = False
        self._crop_history = []
        self._crop_history_index = -1
        self.setStyleSheet(StyleSheet.get_global_stylesheet())
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("图片批量转换工具")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航栏
        self.nav_widget = self._create_nav_panel()
        main_layout.addWidget(self.nav_widget)

        # 右侧内容区
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 15, 20, 0)
        content_layout.setSpacing(15)
        main_layout.addWidget(self.content_widget, 1)

        # 内容面板容器
        self.convert_panel = self._create_convert_panel()
        self.icon_panel = self._create_icon_panel()

        self.current_mode = 'convert'
        self.content_layout = content_layout
        content_layout.addWidget(self.convert_panel, 3)
        content_layout.addWidget(self.icon_panel, 3)
        self.icon_panel.setVisible(False)

        # 底部进度条
        self._create_bottom_bar()

    def _create_nav_panel(self) -> QWidget:
        """左侧导航面板"""
        panel = QWidget()
        panel.setFixedWidth(64)
        panel.setObjectName("navPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 15, 8, 15)
        layout.setSpacing(8)

        logo_label = QLabel("PT")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFixedHeight(36)
        logo_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #4a9eff;
                background: transparent;
                border-radius: 6px;
            }
        """)
        layout.addWidget(logo_label)
        layout.addSpacing(15)

        # 转换模式按钮
        self.btn_convert_mode = QPushButton()
        self.btn_convert_mode.setFixedSize(48, 48)
        self.btn_convert_mode.setCheckable(True)
        self.btn_convert_mode.setChecked(True)
        self.btn_convert_mode.setToolTip("格式转换")
        self.btn_convert_mode.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 10px;
                background: transparent;
                color: #666666;
            }
            QPushButton:hover { background: #e8f4ff; }
            QPushButton:checked { background: #4a9eff; color: white; }
        """)
        self.btn_convert_mode.setText("🖼")
        self.btn_convert_mode.setFont(QFont("Segoe UI Emoji", 20))
        self.btn_convert_mode.clicked.connect(lambda: self.switch_mode('convert'))
        layout.addWidget(self.btn_convert_mode)

        self.convert_label = QLabel("转换")
        self.convert_label.setAlignment(Qt.AlignCenter)
        self.convert_label.setFixedHeight(18)
        self.convert_label.setStyleSheet("QLabel { font-size: 11px; color: #4a9eff; font-weight: bold; }")
        layout.addWidget(self.convert_label)

        layout.addSpacing(10)

        # 图标模式按钮
        self.btn_icon_mode = QPushButton()
        self.btn_icon_mode.setFixedSize(48, 48)
        self.btn_icon_mode.setCheckable(True)
        self.btn_icon_mode.setToolTip("生成图标")
        self.btn_icon_mode.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 10px;
                background: transparent;
                color: #666666;
            }
            QPushButton:hover { background: #e8f4ff; }
            QPushButton:checked { background: #4a9eff; color: white; }
        """)
        self.btn_icon_mode.setText("📋")
        self.btn_icon_mode.setFont(QFont("Segoe UI Emoji", 18))
        self.btn_icon_mode.clicked.connect(lambda: self.switch_mode('icon'))
        layout.addWidget(self.btn_icon_mode)

        self.icon_label = QLabel("图标")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedHeight(18)
        self.icon_label.setStyleSheet("QLabel { font-size: 11px; color: #999999; }")
        layout.addWidget(self.icon_label)

        layout.addStretch()
        return panel

    def switch_mode(self, mode: str):
        """切换模式"""
        if mode == self.current_mode:
            return
        self.current_mode = mode
        if mode == 'convert':
            self.btn_convert_mode.setChecked(True)
            self.btn_icon_mode.setChecked(False)
            self.convert_panel.setVisible(True)
            self.icon_panel.setVisible(False)
            self.convert_label.setStyleSheet("QLabel { font-size: 11px; color: #4a9eff; font-weight: bold; }")
            self.icon_label.setStyleSheet("QLabel { font-size: 11px; color: #999999; }")
        else:
            self.btn_convert_mode.setChecked(False)
            self.btn_icon_mode.setChecked(True)
            self.convert_panel.setVisible(False)
            self.icon_panel.setVisible(True)
            self.convert_label.setStyleSheet("QLabel { font-size: 11px; color: #999999; }")
            self.icon_label.setStyleSheet("QLabel { font-size: 11px; color: #4a9eff; font-weight: bold; }")
        self.status_label.setText("就绪")

    def resizeEvent(self, event):
        """窗口大小变化时更新裁剪覆盖层"""
        super().resizeEvent(event)
        if self._crop_enabled and hasattr(self, 'crop_overlay'):
            QTimer.singleShot(100, self._update_crop_overlay)

    def _create_convert_panel(self) -> QWidget:
        """格式转换模式面板"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 左侧预览面板
        left_widget = QWidget()
        left_widget.setObjectName("cardPanel")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("cardHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(15, 10, 15, 10)
        hl.addWidget(QLabel("<b>图片预览</b>"))
        self.file_name_label = QLabel("未选择图片")
        self.file_name_label.setObjectName("info")
        self.file_name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(self.file_name_label)
        left_layout.addWidget(header)

        # 图片预览区域
        self.preview_area = DropArea()
        self.preview_area.setObjectName("previewArea")
        self.preview_area.setStyleSheet("""
            QWidget#previewArea {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background: #fafafa;
            }
        """)
        self.preview_area.file_dropped.connect(self.handle_file_dropped)

        preview_container = QWidget()
        preview_container.setObjectName("previewDropZone")
        preview_container.setStyleSheet("background: transparent; border: none;")
        self.preview_label = QLabel("拖拽图片到此处\n或点击下方按钮选择")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: #999; font-size: 14px; border: none;")
        container_layout = QVBoxLayout(preview_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.addWidget(self.preview_label, 1, Qt.AlignCenter)

        self.crop_overlay = CropRubberBand(preview_container)
        self.crop_overlay.setVisible(False)
        self.crop_overlay.crop_changed.connect(self._on_crop_changed)

        stack_layout = QStackedLayout()
        stack_layout.setStackingMode(QStackedLayout.StackAll)
        stack_layout.addWidget(preview_container)
        stack_layout.addWidget(self.crop_overlay)

        preview_layout = QVBoxLayout(self.preview_area)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addLayout(stack_layout, 1)

        self._preview_label = self.preview_label
        self._preview_container = preview_container

        # 预览信息栏
        self.preview_info_layout = QHBoxLayout()
        self.preview_info_layout.setSpacing(15)
        self.preview_info_label = QLabel()
        self.preview_info_label.setObjectName("info")
        self.preview_size_label = QLabel()
        self.preview_size_label.setObjectName("info")
        self.preview_info_layout.addWidget(self.preview_info_label)
        self.preview_info_layout.addWidget(self.preview_size_label)
        preview_layout.addLayout(self.preview_info_layout)

        left_layout.addWidget(self.preview_area, 1)

        # 按钮栏
        btn_frame = QFrame()
        btn_frame.setObjectName("cardFooter")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(12, 8, 12, 8)
        btn_layout.setSpacing(10)
        self.add_btn = QPushButton("选择图片", clicked=self.select_image, objectName="primaryBtn")
        self.clear_btn = QPushButton("清除", clicked=self.clear_image, objectName="secondaryBtn")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        left_layout.addWidget(btn_frame)

        layout.addWidget(left_widget, 3)

        # 右侧设置面板
        right_panel = self._create_convert_settings()
        layout.addWidget(right_panel, 2)

        return panel

    def _create_crop_panel_content(self) -> QWidget:
        """裁剪功能区内容"""
        self.crop_switch = QCheckBox("启用裁剪")
        self.crop_switch.stateChanged.connect(self._on_crop_switch_changed)

        self.crop_settings_widget = QWidget()
        crop_settings_layout = QVBoxLayout(self.crop_settings_widget)
        crop_settings_layout.setContentsMargins(10, 10, 0, 0)
        crop_settings_layout.setSpacing(10)

        crop_settings_layout.addWidget(self.crop_switch)

        # 选区模式
        mode_group = CollapsibleGroupBox("选区模式")
        mode_content = QWidget()
        mode_layout = QVBoxLayout(mode_content)
        mode_layout.setContentsMargins(10, 5, 10, 8)
        mode_layout.setSpacing(6)

        self.crop_mode_group = QButtonGroup()
        self.crop_mode_free = QRadioButton("自由选区")
        self.crop_mode_free.setChecked(True)
        self.crop_mode_fixed = QRadioButton("固定尺寸")
        self.crop_mode_ratio = QRadioButton("锁定比例")
        self.crop_mode_preset = QRadioButton("预设尺寸")

        self.crop_mode_group.addButton(self.crop_mode_free, 0)
        self.crop_mode_group.addButton(self.crop_mode_fixed, 1)
        self.crop_mode_group.addButton(self.crop_mode_ratio, 2)
        self.crop_mode_group.addButton(self.crop_mode_preset, 3)

        mode_layout.addWidget(self.crop_mode_free)
        mode_layout.addWidget(self.crop_mode_fixed)
        mode_layout.addWidget(self.crop_mode_ratio)
        mode_layout.addWidget(self.crop_mode_preset)

        self.crop_mode_group.buttonClicked[int].connect(self._on_crop_mode_changed)
        mode_group.setContentWidget(mode_content)
        mode_group.setExpanded(True)
        crop_settings_layout.addWidget(mode_group)

        # 固定尺寸设置
        fixed_widget = QWidget()
        fixed_layout = QGridLayout(fixed_widget)
        fixed_layout.setContentsMargins(0, 5, 0, 0)
        fixed_layout.setSpacing(5)

        fixed_layout.addWidget(QLabel("宽度:"), 0, 0)
        self.crop_width_spin = QSpinBox()
        self.crop_width_spin.setRange(1, 10000)
        self.crop_width_spin.setValue(1920)
        self.crop_width_spin.setSuffix(" px")
        fixed_layout.addWidget(self.crop_width_spin, 0, 1)

        fixed_layout.addWidget(QLabel("高度:"), 1, 0)
        self.crop_height_spin = QSpinBox()
        self.crop_height_spin.setRange(1, 10000)
        self.crop_height_spin.setValue(1080)
        self.crop_height_spin.setSuffix(" px")
        fixed_layout.addWidget(self.crop_height_spin, 1, 1)

        fixed_layout.addWidget(QLabel("X:"), 2, 0)
        self.crop_x_spin = QSpinBox()
        self.crop_x_spin.setRange(0, 10000)
        self.crop_x_spin.setValue(0)
        fixed_layout.addWidget(self.crop_x_spin, 2, 1)

        fixed_layout.addWidget(QLabel("Y:"), 3, 0)
        self.crop_y_spin = QSpinBox()
        self.crop_y_spin.setRange(0, 10000)
        self.crop_y_spin.setValue(0)
        fixed_layout.addWidget(self.crop_y_spin, 3, 1)

        self.crop_width_spin.valueChanged.connect(self._on_crop_fixed_size_changed)
        self.crop_height_spin.valueChanged.connect(self._on_crop_fixed_size_changed)
        self.crop_x_spin.valueChanged.connect(self._on_crop_position_changed)
        self.crop_y_spin.valueChanged.connect(self._on_crop_position_changed)

        self.crop_fixed_widget = fixed_widget
        crop_settings_layout.addWidget(fixed_widget)

        # 锁定比例设置
        ratio_widget = QWidget()
        ratio_layout = QHBoxLayout(ratio_widget)
        ratio_layout.setContentsMargins(0, 5, 0, 0)
        ratio_layout.addWidget(QLabel("比例:"))
        self.crop_ratio_combo = QComboBox()
        self.crop_ratio_combo.addItems([
            "1:1 (正方形)", "4:3", "16:9", "3:2", "2:3", "9:16", "自定义"
        ])
        self.crop_ratio_combo.currentIndexChanged.connect(self._on_crop_ratio_changed)
        ratio_layout.addWidget(self.crop_ratio_combo, 1)
        self.crop_ratio_widget = ratio_widget
        crop_settings_layout.addWidget(ratio_widget)

        # 预设尺寸
        preset_widget = QWidget()
        preset_layout = QVBoxLayout(preset_widget)
        preset_layout.setContentsMargins(0, 5, 0, 0)
        preset_layout.setSpacing(5)
        preset_btn_layout = QGridLayout()
        preset_btn_layout.setSpacing(5)

        presets = [
            ("头像 200×200", 200, 200),
            ("头像 500×500", 500, 500),
            ("证件照 25×35", 25, 35),
            ("壁纸 1920×1080", 1920, 1080),
            ("壁纸 2560×1440", 2560, 1440),
            ("微信封面 900×383", 900, 383),
            ("小红书 1:1", 1080, 1080),
            ("小红书 3:4", 1080, 1440),
        ]

        self.preset_btns = []
        for i, (name, w, h) in enumerate(presets):
            btn = QPushButton(name)
            btn.setObjectName("secondaryBtn")
            btn.clicked.connect(lambda checked, pw=w, ph=h: self._apply_crop_preset(pw, ph))
            row, col = i // 2, i % 2
            preset_btn_layout.addWidget(btn, row, col)
            self.preset_btns.append(btn)

        preset_layout.addLayout(preset_btn_layout)
        self.crop_preset_widget = preset_widget
        crop_settings_layout.addWidget(preset_widget)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_apply_crop = QPushButton("应用选区")
        self.btn_apply_crop.setObjectName("primaryBtn")
        self.btn_apply_crop.clicked.connect(self._apply_crop_selection)
        btn_layout.addWidget(self.btn_apply_crop)

        self.btn_undo_crop = QPushButton("撤销")
        self.btn_undo_crop.setObjectName("secondaryBtn")
        self.btn_undo_crop.clicked.connect(self._undo_crop_selection)
        self.btn_undo_crop.setEnabled(False)
        self.btn_undo_crop.setToolTip("回退到上一步裁剪")
        btn_layout.addWidget(self.btn_undo_crop)

        self.btn_reset_crop = QPushButton("重置")
        self.btn_reset_crop.setObjectName("secondaryBtn")
        self.btn_reset_crop.clicked.connect(self._reset_crop_selection)
        self.btn_reset_crop.setToolTip("清除所有裁剪，恢复原始图片")
        btn_layout.addWidget(self.btn_reset_crop)

        crop_settings_layout.addLayout(btn_layout)
        self._on_crop_mode_changed(0)

        return self.crop_settings_widget

    def _on_crop_switch_changed(self, state):
        enabled = (state == Qt.Checked)
        self._crop_enabled = enabled
        if enabled:
            if not self.files or self._original_pixmap is None:
                QMessageBox.warning(self, "提示", "请先加载图片!")
                self.crop_switch.setChecked(False)
                self._crop_enabled = False
                return
            # 重置为自由选区模式
            self._crop_mode = "free"
            self.crop_mode_free.setChecked(True)
            # 允许重新绘制选框
            self.crop_overlay._can_redraw = True
            self.crop_overlay._rubber_band = None
            self.crop_overlay.setVisible(True)
            # 更新裁剪覆盖层（reset_selection=True 将选框重置为整张图片）
            QTimer.singleShot(150, lambda: self._update_crop_overlay(reset_selection=True))
        else:
            self.crop_overlay.setVisible(False)
            # 重置裁剪状态
            self._crop_mode = "free"
            self._crop_rect = None
            self.crop_overlay._can_redraw = True
            self.crop_overlay._rubber_band = None
            # 重置选区模式为自由选区
            self.crop_mode_free.setChecked(True)
            # 隐藏非自由选区的设置面板
            self.crop_fixed_widget.setVisible(False)
            self.crop_ratio_widget.setVisible(False)
            self.crop_preset_widget.setVisible(False)
            # 重置下拉框和输入控件
            self.crop_ratio_combo.setCurrentIndex(0)
            self.crop_width_spin.setValue(self._original_pixmap.width() if self._original_pixmap else 1920)
            self.crop_height_spin.setValue(self._original_pixmap.height() if self._original_pixmap else 1080)
            self.crop_x_spin.setValue(0)
            self.crop_y_spin.setValue(0)

    def _on_crop_mode_changed(self, mode_id):
        self._crop_mode = ["free", "fixed", "ratio", "preset"][mode_id]
        self.crop_fixed_widget.setVisible(False)
        self.crop_ratio_widget.setVisible(False)
        self.crop_preset_widget.setVisible(False)
        if mode_id == 1:
            self.crop_fixed_widget.setVisible(True)
        elif mode_id == 2:
            self.crop_ratio_widget.setVisible(True)
        elif mode_id == 3:
            self.crop_preset_widget.setVisible(True)

        # 裁剪已开启时，根据新模式立即调整选框
        if self._crop_enabled and hasattr(self, 'crop_overlay') and self.crop_overlay.image_rect:
            if mode_id == 0:
                # 自由选区：选框重置为整张图片
                self.crop_overlay.set_image_rect(self.crop_overlay.image_rect)
            elif mode_id == 1:
                # 固定尺寸：根据当前 spin 值调整
                self._on_crop_fixed_size_changed()
            elif mode_id == 2:
                # 锁定比例：根据当前下拉框值调整
                self._on_crop_ratio_changed(self.crop_ratio_combo.currentIndex())
            elif mode_id == 3:
                # 预设尺寸：默认应用第一个预设
                if self.preset_btns:
                    presets = [
                        ("头像 200×200", 200, 200),
                        ("头像 500×500", 500, 500),
                        ("证件照 25×35", 25, 35),
                        ("壁纸 1920×1080", 1920, 1080),
                        ("壁纸 2560×1440", 2560, 1440),
                        ("微信封面 900×383", 900, 383),
                        ("小红书 1:1", 1080, 1080),
                        ("小红书 3:4", 1080, 1440),
                    ]
                    self._apply_crop_preset(presets[0][1], presets[0][2])

    def _on_crop_fixed_size_changed(self):
        if self._crop_mode != "fixed" or not self._crop_enabled:
            return
        w = self.crop_width_spin.value()
        h = self.crop_height_spin.value()
        if hasattr(self, 'crop_overlay') and self.crop_overlay:
            self.crop_overlay.set_crop_rect_from_size(w, h)

    def _on_crop_position_changed(self):
        if self._crop_mode != "fixed" or not self._crop_enabled:
            return
        x, y = self.crop_x_spin.value(), self.crop_y_spin.value()
        w, h = self.crop_width_spin.value(), self.crop_height_spin.value()
        if hasattr(self, 'crop_overlay') and self.crop_overlay and self.crop_overlay.image_rect:
            img_rect = self.crop_overlay.image_rect
            scale_x = img_rect.width() / (self._original_pixmap.width() if self._original_pixmap else 1)
            scale_y = img_rect.height() / (self._original_pixmap.height() if self._original_pixmap else 1)
            rx = img_rect.x() + x * scale_x
            ry = img_rect.y() + y * scale_y
            rw = w * scale_x
            rh = h * scale_y
            rx = max(img_rect.x(), min(rx, img_rect.x() + img_rect.width() - rw))
            ry = max(img_rect.y(), min(ry, img_rect.y() + img_rect.height() - rh))
            self.crop_overlay._rubber_band = QRectF(rx, ry, rw, rh)
            self.crop_overlay.update()
            self.crop_overlay.crop_changed.emit(self.crop_overlay._get_crop_rect_ratios())

    def _on_crop_ratio_changed(self, index):
        if self._crop_mode != "ratio" or not self._crop_enabled:
            return
        ratios = {0: (1, 1), 1: (4, 3), 2: (16, 9), 3: (3, 2), 4: (2, 3), 5: (9, 16), 6: (1, 1)}
        if index in ratios and hasattr(self, 'crop_overlay') and self.crop_overlay:
            rw, rh = ratios[index]
            img_rect = self.crop_overlay.image_rect
            if img_rect:
                img_w, img_h = img_rect.width(), img_rect.height()
                target_ratio = rw / rh
                if img_w / img_h > target_ratio:
                    h = img_h
                    w = h * target_ratio
                else:
                    w = img_w
                    h = w / target_ratio
                x = img_rect.x() + (img_w - w) / 2
                y = img_rect.y() + (img_h - h) / 2
                self.crop_overlay._rubber_band = QRectF(x, y, w, h)
                self.crop_overlay.update()
                self.crop_overlay.crop_changed.emit(self.crop_overlay._get_crop_rect_ratios())

    def _apply_crop_preset(self, width, height):
        if hasattr(self, 'crop_overlay') and self.crop_overlay and self.crop_overlay.image_rect:
            self.crop_overlay.set_crop_rect_from_size(width, height)

    def _apply_crop_selection(self):
        if not hasattr(self, 'crop_overlay') or not self.crop_overlay:
            return
        crop_rect = self.crop_overlay._get_crop_rect_ratios()
        if crop_rect is None:
            QMessageBox.warning(self, "提示", "请先在图片上拖动画出裁剪区域!")
            return
        if self._original_pixmap is None:
            QMessageBox.warning(self, "提示", "没有可用的图片!")
            return
        self._crop_rect = crop_rect
        x1_ratio, y1_ratio, x2_ratio, y2_ratio = crop_rect
        orig_w = self._original_pixmap.width()
        orig_h = self._original_pixmap.height()
        x1 = int(x1_ratio * orig_w)
        y1 = int(y1_ratio * orig_h)
        x2 = int(x2_ratio * orig_w)
        y2 = int(y2_ratio * orig_h)
        if x2 <= x1 or y2 <= y1:
            QMessageBox.warning(self, "提示", "裁剪区域无效!")
            return
        self._crop_history.append(self._original_pixmap.copy())
        self._crop_history_index = len(self._crop_history) - 1
        cropped_pixmap = self._original_pixmap.copy(x1, y1, x2 - x1, y2 - y1)
        if cropped_pixmap.isNull():
            QMessageBox.warning(self, "提示", "裁剪失败!")
            return
        self._original_pixmap = cropped_pixmap
        self._crop_applied = True
        scaled_pixmap = cropped_pixmap.scaled(
            self.preview_area.width(), self.preview_area.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled_pixmap)
        self.preview_info_label.setText(f"{cropped_pixmap.width()} × {cropped_pixmap.height()}")
        QTimer.singleShot(100, self._update_crop_overlay_after_apply)
        self._update_undo_button_state()
        self.status_label.setText(f"裁剪选区已应用（可回退 {len(self._crop_history)} 步）")

    def _update_crop_overlay_after_apply(self):
        if not self._crop_enabled or not hasattr(self, 'crop_overlay'):
            return
        self.crop_overlay._can_redraw = True
        self._update_crop_overlay()
        self.crop_overlay._can_redraw = False

    def _reset_crop_selection(self):
        if self._original_pixmap_backup is None:
            return
        self._original_pixmap = self._original_pixmap_backup.copy()
        self._crop_applied = False
        self._crop_rect = None
        self._crop_history = []
        self._crop_history_index = -1
        scaled_pixmap = self._original_pixmap.scaled(
            self.preview_area.width(), self.preview_area.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled_pixmap)
        self.preview_info_label.setText(f"{self._original_pixmap.width()} × {self._original_pixmap.height()}")
        if hasattr(self, 'crop_overlay'):
            self.crop_overlay._can_redraw = True
            QTimer.singleShot(100, self._update_crop_overlay)
        self._update_undo_button_state()
        self.status_label.setText("已重置到原始图片")

    def _undo_crop_selection(self):
        if not self._crop_history or self._crop_history_index < 0:
            return
        self._original_pixmap = self._crop_history[self._crop_history_index].copy()
        self._crop_history = self._crop_history[:self._crop_history_index]
        self._crop_history_index = len(self._crop_history) - 1
        self._crop_applied = True
        self._crop_rect = None
        scaled_pixmap = self._original_pixmap.scaled(
            self.preview_area.width(), self.preview_area.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled_pixmap)
        self.preview_info_label.setText(f"{self._original_pixmap.width()} × {self._original_pixmap.height()}")
        if hasattr(self, 'crop_overlay'):
            self.crop_overlay._can_redraw = True
            QTimer.singleShot(100, self._update_crop_overlay)
        self._update_undo_button_state()
        steps = len(self._crop_history)
        self.status_label.setText(f"已回退到上一步" + (f"（还剩 {steps} 步可回退）" if steps > 0 else ""))

    def _update_undo_button_state(self):
        if hasattr(self, 'btn_undo_crop'):
            can_undo = len(self._crop_history) > 0
            self.btn_undo_crop.setEnabled(can_undo)
            self.btn_undo_crop.setText(f"撤销 ({len(self._crop_history)})" if can_undo else "撤销")

    def _create_convert_settings(self) -> QWidget:
        """转换模式的右侧设置面板"""
        panel = QWidget()
        panel.setObjectName("cardPanel")

        outer_layout = QHBoxLayout(panel)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("settingsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea#settingsScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea#settingsScrollArea > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        content_widget = QWidget()
        content_widget.setObjectName("scrollContent")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        content_widget.setMaximumWidth(500)

        # 输出格式
        fmt_group = CollapsibleGroupBox("输出格式")
        fmt_content = QWidget()
        fmt_layout = QFormLayout(fmt_content)
        fmt_layout.setContentsMargins(10, 8, 10, 8)
        fmt_layout.setSpacing(8)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "WEBP", "BMP"])
        self.format_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fmt_layout.addRow("格式:", self.format_combo)
        fmt_group.setContentWidget(fmt_content)
        fmt_group.setExpanded(True)
        layout.addWidget(fmt_group)

        # 图片质量
        quality_group = CollapsibleGroupBox("图片质量")
        quality_content = QWidget()
        quality_layout = QFormLayout(quality_content)
        quality_layout.setContentsMargins(10, 8, 10, 8)
        quality_layout.setSpacing(8)
        slider_widget = QWidget()
        slider_layout = QHBoxLayout(slider_widget)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(10)
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(85)
        slider_layout.addWidget(self.quality_slider, 1)
        self.quality_label = QLabel("85%")
        self.quality_label.setMinimumWidth(45)
        self.quality_label.setAlignment(Qt.AlignCenter)
        self.quality_slider.valueChanged.connect(lambda v: self.quality_label.setText(f"{v}%"))
        slider_layout.addWidget(self.quality_label)
        quality_layout.addRow("质量:", slider_widget)
        quality_group.setContentWidget(quality_content)
        quality_group.setExpanded(True)
        layout.addWidget(quality_group)

        # 尺寸调整
        resize_group = CollapsibleGroupBox("尺寸调整")
        resize_content = QWidget()
        resize_layout = QGridLayout(resize_content)
        resize_layout.setContentsMargins(10, 8, 10, 8)
        self.resize_checkbox = QCheckBox("启用尺寸调整")
        resize_layout.addWidget(self.resize_checkbox, 0, 0, 1, 2)
        width_label = QLabel("宽度:")
        width_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        width_label.setFixedWidth(50)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 10000)
        self.width_spinbox.setValue(1920)
        self.width_spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        resize_layout.addWidget(width_label, 1, 0)
        resize_layout.addWidget(self.width_spinbox, 1, 1)
        height_label = QLabel("高度:")
        height_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        height_label.setFixedWidth(50)
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 10000)
        self.height_spinbox.setValue(1080)
        self.height_spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        resize_layout.addWidget(height_label, 2, 0)
        resize_layout.addWidget(self.height_spinbox, 2, 1)
        self.keep_ratio_checkbox = QCheckBox("保持宽高比")
        self.keep_ratio_checkbox.setChecked(True)
        resize_layout.addWidget(self.keep_ratio_checkbox, 3, 0, 1, 2)
        resize_group.setContentWidget(resize_content)
        resize_group.setExpanded(True)
        layout.addWidget(resize_group)

        # 旋转调整
        rotate_group = CollapsibleGroupBox("旋转调整")
        rotate_content = QWidget()
        rotate_layout = QVBoxLayout(rotate_content)
        rotate_layout.setContentsMargins(10, 8, 10, 8)
        rotate_layout.setSpacing(10)
        btn_rotate_layout = QHBoxLayout()
        btn_rotate_layout.setSpacing(8)
        self.btn_rotate_left = QPushButton("↺ 左转90°")
        self.btn_rotate_left.setObjectName("secondaryBtn")
        self.btn_rotate_left.clicked.connect(self.rotate_left_90)
        btn_rotate_layout.addWidget(self.btn_rotate_left)
        self.btn_rotate_right = QPushButton("↻ 右转90°")
        self.btn_rotate_right.setObjectName("secondaryBtn")
        self.btn_rotate_right.clicked.connect(self.rotate_right_90)
        btn_rotate_layout.addWidget(self.btn_rotate_right)
        self.btn_flip_h = QPushButton("水平翻转")
        self.btn_flip_h.setObjectName("secondaryBtn")
        self.btn_flip_h.clicked.connect(self.flip_horizontal)
        btn_rotate_layout.addWidget(self.btn_flip_h)
        self.btn_flip_v = QPushButton("垂直翻转")
        self.btn_flip_v.setObjectName("secondaryBtn")
        self.btn_flip_v.clicked.connect(self.flip_vertical)
        btn_rotate_layout.addWidget(self.btn_flip_v)
        self.btn_reset_transform = QPushButton("重置")
        self.btn_reset_transform.setObjectName("secondaryBtn")
        self.btn_reset_transform.clicked.connect(self.reset_transform)
        btn_rotate_layout.addWidget(self.btn_reset_transform)
        btn_rotate_layout.addStretch()
        rotate_layout.addLayout(btn_rotate_layout)
        self.transform_status_label = QLabel("无变换")
        self.transform_status_label.setAlignment(Qt.AlignCenter)
        self.transform_status_label.setStyleSheet("color: #888; font-size: 12px;")
        rotate_layout.addWidget(self.transform_status_label)
        rotate_group.setContentWidget(rotate_content)
        rotate_group.setExpanded(True)
        layout.addWidget(rotate_group)

        # 裁剪设置
        crop_group = CollapsibleGroupBox("裁剪设置")
        crop_content = self._create_crop_panel_content()
        crop_group.setContentWidget(crop_content)
        crop_group.setExpanded(True)
        layout.addWidget(crop_group)

        layout.addStretch()

        # 转换按钮
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setObjectName("primaryBtn")
        self.convert_btn.setMinimumHeight(36)
        self.convert_btn.clicked.connect(self.start_convert)
        layout.addWidget(self.convert_btn)

        scroll_area.setWidget(content_widget)
        outer_layout.addWidget(scroll_area, 1)

        return panel

    def _create_icon_panel(self) -> QWidget:
        """图标生成模式面板"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        left_widget = QWidget()
        left_widget.setObjectName("cardPanel")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("cardHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(15, 10, 15, 10)
        hl.addWidget(QLabel("<b>图片预览</b>"))
        self.icon_file_name_label = QLabel("未选择图片")
        self.icon_file_name_label.setObjectName("info")
        self.icon_file_name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(self.icon_file_name_label)
        left_layout.addWidget(header)

        self.icon_preview_area = DropArea()
        self.icon_preview_area.setObjectName("previewArea")
        self.icon_preview_area.setStyleSheet("""
            QWidget#previewArea {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background: #fafafa;
            }
        """)
        self.icon_preview_area.file_dropped.connect(self.handle_icon_file_dropped)

        icon_preview_container = QWidget()
        icon_preview_container.setObjectName("previewDropZone")
        icon_preview_container.setStyleSheet("background: transparent; border: none;")
        self.icon_preview_label = QLabel("拖拽图片到此处\n或点击下方按钮选择")
        self.icon_preview_label.setAlignment(Qt.AlignCenter)
        self.icon_preview_label.setStyleSheet("color: #999; font-size: 14px; border: none;")
        container_layout = QVBoxLayout(icon_preview_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.addWidget(self.icon_preview_label, 1, Qt.AlignCenter)

        preview_layout = QVBoxLayout(self.icon_preview_area)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(icon_preview_container, 1)

        self.icon_preview_info_layout = QHBoxLayout()
        self.icon_preview_info_layout.setSpacing(15)
        self.icon_preview_info_label = QLabel()
        self.icon_preview_info_label.setObjectName("info")
        self.icon_preview_size_label = QLabel()
        self.icon_preview_size_label.setObjectName("info")
        self.icon_preview_info_layout.addWidget(self.icon_preview_info_label)
        self.icon_preview_info_layout.addWidget(self.icon_preview_size_label)
        preview_layout.addLayout(self.icon_preview_info_layout)

        left_layout.addWidget(self.icon_preview_area, 1)

        btn_frame = QFrame()
        btn_frame.setObjectName("cardFooter")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(12, 8, 12, 8)
        btn_layout.setSpacing(10)
        self.icon_add_btn = QPushButton("选择图片", clicked=self.select_icon_image, objectName="primaryBtn")
        self.icon_clear_btn = QPushButton("清除", clicked=self.clear_icon_image, objectName="secondaryBtn")
        btn_layout.addWidget(self.icon_add_btn)
        btn_layout.addWidget(self.icon_clear_btn)
        btn_layout.addStretch()
        left_layout.addWidget(btn_frame)

        layout.addWidget(left_widget, 3)

        right_panel = self._create_icon_settings()
        layout.addWidget(right_panel, 2)

        return panel

    def _create_icon_settings(self) -> QWidget:
        """图标模式的设置面板"""
        panel = QWidget()
        panel.setObjectName("cardPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        preset_group = QGroupBox("图标预设")
        preset_layout = QFormLayout(preset_group)
        preset_layout.setContentsMargins(10, 25, 10, 8)
        preset_layout.setSpacing(8)

        self.icon_preset_combo = QComboBox()
        self.icon_preset_combo.addItems([
            "Windows 系统图标", "iOS 应用图标", "Android 应用图标",
            "网站 Favicon", "Apple Touch Icon", "Windows 10/11 磁贴",
            "完整多平台图标包", "自定义尺寸"
        ])
        self.icon_preset_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        preset_layout.addRow("预设:", self.icon_preset_combo)

        self.custom_sizes_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_sizes_widget)
        custom_layout.setContentsMargins(0, 5, 0, 0)
        custom_layout.setSpacing(5)
        self.icon_size_spinbox = QSpinBox()
        self.icon_size_spinbox.setRange(16, 1024)
        self.icon_size_spinbox.setValue(256)
        self.icon_size_spinbox.setSuffix(" px")
        custom_layout.addWidget(QLabel("尺寸:"))
        custom_layout.addWidget(self.icon_size_spinbox)
        custom_layout.addStretch()
        custom_layout.itemAt(0).widget().setAlignment(Qt.AlignRight)
        preset_layout.addRow("", self.custom_sizes_widget)
        self.custom_sizes_widget.setVisible(False)

        self.icon_preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addWidget(preset_group)

        fmt_group = QGroupBox("输出格式")
        fmt_layout = QVBoxLayout(fmt_group)
        fmt_layout.setContentsMargins(10, 25, 10, 8)
        self.icon_format_combo = QComboBox()
        self.icon_format_combo.addItems(["ICO (多尺寸)", "PNG", "ICO + PNG"])
        self.icon_format_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fmt_layout.addWidget(self.icon_format_combo)
        layout.addWidget(fmt_group)

        preview_group = QGroupBox("生成预览")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(10, 25, 10, 8)
        self.icon_preview_list = QListWidget()
        self.icon_preview_list.setMaximumHeight(120)
        preview_layout.addWidget(self.icon_preview_list)
        self._update_icon_preview()
        self.icon_preset_combo.currentIndexChanged.connect(self._update_icon_preview)
        self.icon_size_spinbox.valueChanged.connect(self._update_icon_preview)
        layout.addWidget(preview_group)

        layout.addStretch()

        self.icon_generate_btn = QPushButton("生成图标")
        self.icon_generate_btn.setObjectName("primaryBtn")
        self.icon_generate_btn.setMinimumHeight(36)
        self.icon_generate_btn.clicked.connect(self.generate_icon)
        layout.addWidget(self.icon_generate_btn)
        return panel

    def _on_preset_changed(self):
        if self.icon_preset_combo.currentIndex() == 7:
            self.custom_sizes_widget.setVisible(True)
        else:
            self.custom_sizes_widget.setVisible(False)
        self._update_icon_preview()

    def _update_icon_preview(self):
        self.icon_preview_list.clear()
        preset_idx = self.icon_preset_combo.currentIndex()
        presets = {
            0: ImageConverter.ICON_PRESETS['windows'][:4],
            1: ImageConverter.ICON_PRESETS['ios'][:8],
            2: ImageConverter.ICON_PRESETS['android'],
            3: ImageConverter.ICON_PRESETS['favicon'][:5],
            4: ImageConverter.ICON_PRESETS['apple_touch'][:5],
            5: ImageConverter.ICON_PRESETS['microsoft'],
            6: list(set(ImageConverter.ICON_PRESETS['ios'][:6] + ImageConverter.ICON_PRESETS['android'])),
            7: [self.icon_size_spinbox.value()]
        }
        sizes = presets.get(preset_idx, [256])
        for size in sizes[:10]:
            self.icon_preview_list.addItem(f"{size} × {size} px")
        if len(sizes) > 10:
            self.icon_preview_list.addItem(f"... 共 {len(sizes)} 个尺寸")

    def _create_bottom_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("info")
        self.status_bar.addWidget(self.status_label, 1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.status_bar.addPermanentWidget(self.progress_bar)

    # === 槽函数 ===
    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def update_preview(self):
        self._flip_h = False
        self._flip_v = False
        self._rotation_angle = 0
        self._crop_rect = None
        if self._crop_enabled:
            self._crop_enabled = False
            self.crop_overlay.setVisible(False)
            if hasattr(self, 'crop_switch'):
                self.crop_switch.setChecked(False)
                self.crop_settings_widget.setVisible(False)
        if self.files:
            file_path = self.files[0]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self._original_pixmap = pixmap
                self._original_pixmap_backup = pixmap.copy()
                self._crop_applied = False
                scaled_pixmap = pixmap.scaled(
                    self.preview_area.width(), self.preview_area.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pixmap)
                self.preview_label.setStyleSheet("border: none;")
                self.preview_info_label.setText(f"{pixmap.width()} × {pixmap.height()}")
                file_size = Path(file_path).stat().st_size
                self.preview_size_label.setText(self._format_file_size(file_size))
                self.file_name_label.setText(Path(file_path).name)
                if self._crop_enabled:
                    QTimer.singleShot(100, self._update_crop_overlay)
            else:
                self._original_pixmap = None
                self._original_pixmap_backup = None
                self.preview_label.setText("无法加载图片")
                self.preview_info_label.setText("")
                self.preview_size_label.setText("")
        else:
            self._original_pixmap = None
            self._original_pixmap_backup = None
            self.preview_label.clear()
            self.preview_label.setText("拖拽图片到此处\n或点击下方按钮选择")
            self.preview_label.setStyleSheet("color: #999; font-size: 14px; border: none;")
            self.preview_info_label.setText("")
            self.preview_size_label.setText("")
            self.file_name_label.setText("未选择图片")
        self._update_transform_status()

    def update_icon_preview(self):
        if hasattr(self, 'icon_files') and self.icon_files:
            file_path = self.icon_files[0]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.icon_preview_area.width(), self.icon_preview_area.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_preview_label.setPixmap(scaled_pixmap)
                self.icon_preview_label.setStyleSheet("border: none;")
                self.icon_preview_info_label.setText(f"{pixmap.width()} × {pixmap.height()}")
                file_size = Path(file_path).stat().st_size
                self.icon_preview_size_label.setText(self._format_file_size(file_size))
                self.icon_file_name_label.setText(Path(file_path).name)
            else:
                self.icon_preview_label.setText("无法加载图片")
                self.icon_preview_info_label.setText("")
                self.icon_preview_size_label.setText("")
        else:
            self.icon_preview_label.clear()
            self.icon_preview_label.setText("拖拽图片到此处\n或点击下方按钮选择")
            self.icon_preview_label.setStyleSheet("color: #999; font-size: 14px; border: none;")
            self.icon_preview_info_label.setText("")
            self.icon_preview_size_label.setText("")
            self.icon_file_name_label.setText("未选择图片")

    def handle_file_dropped(self, file_path):
        self.files = [file_path]
        self.update_preview()

    def handle_icon_file_dropped(self, file_path):
        self.icon_files = [file_path]
        self.update_icon_preview()

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if file_path:
            self.files = [file_path]
            self.update_preview()

    def select_icon_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if file_path:
            self.icon_files = [file_path]
            self.update_icon_preview()

    def clear_image(self):
        self.files = []
        self.update_preview()

    def clear_icon_image(self):
        self.icon_files = []
        self.update_icon_preview()

    def flip_horizontal(self):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        self._flip_h = not self._flip_h
        self._update_transform_preview()

    def flip_vertical(self):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        self._flip_v = not self._flip_v
        self._update_transform_preview()

    def rotate_left_90(self):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        self._rotation_angle = (self._rotation_angle - 90) % 360
        self._update_transform_preview()

    def rotate_right_90(self):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        self._rotation_angle = (self._rotation_angle + 90) % 360
        self._update_transform_preview()

    def reset_transform(self):
        self._flip_h = False
        self._flip_v = False
        self._rotation_angle = 0
        self._update_transform_preview()
        if self._crop_enabled and hasattr(self, 'crop_overlay'):
            QTimer.singleShot(100, self._update_crop_overlay)

    def _update_crop_overlay(self, reset_selection=False):
        if self._original_pixmap is None:
            return
        self.preview_area.updateGeometry()
        self.preview_area.update()
        QApplication.processEvents()
        pixmap = self._original_pixmap
        preview_label = self._preview_label
        preview_w = self.preview_area.width()
        preview_h = self.preview_area.height()
        if preview_w <= 20 or preview_h <= 20:
            QTimer.singleShot(50, lambda: self._update_crop_overlay(reset_selection))
            return
        scaled_pixmap = pixmap.scaled(preview_w, preview_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_w = scaled_pixmap.width()
        scaled_h = scaled_pixmap.height()
        scale = scaled_w / pixmap.width()
        self.crop_overlay._preview_scale = scale
        self.crop_overlay._original_pixmap = self._original_pixmap
        self.crop_overlay.setGeometry(0, 0, preview_w, preview_h)
        label_geometry = preview_label.geometry()
        label_x = label_geometry.x()
        label_y = label_geometry.y()
        label_w = label_geometry.width()
        label_h = label_geometry.height()
        if reset_selection:
            # 初始化：将选框设为整张图片
            self.crop_overlay.set_image_rect(QRectF(label_x, label_y, label_w, label_h))
        else:
            # 保留当前选框比例，仅更新 image_rect 坐标
            self.crop_overlay.update_image_rect(QRectF(label_x, label_y, label_w, label_h))
        self.crop_overlay._can_redraw = False
        self.crop_overlay.update()

    def _on_crop_changed(self, rect_ratios):
        if rect_ratios is None:
            return
        self._crop_rect = rect_ratios
        if self._original_pixmap:
            orig_w = self._original_pixmap.width()
            orig_h = self._original_pixmap.height()
            x1_ratio, y1_ratio, x2_ratio, y2_ratio = rect_ratios
            w = int((x2_ratio - x1_ratio) * orig_w)
            h = int((y2_ratio - y1_ratio) * orig_h)
            ox = int(x1_ratio * orig_w)
            oy = int(y1_ratio * orig_h)
            self.crop_width_spin.valueChanged.disconnect()
            self.crop_height_spin.valueChanged.disconnect()
            self.crop_x_spin.valueChanged.disconnect()
            self.crop_y_spin.valueChanged.disconnect()
            self.crop_width_spin.setValue(max(1, w))
            self.crop_height_spin.setValue(max(1, h))
            self.crop_x_spin.setValue(max(0, ox))
            self.crop_y_spin.setValue(max(0, oy))
            self.crop_width_spin.valueChanged.connect(self._on_crop_fixed_size_changed)
            self.crop_height_spin.valueChanged.connect(self._on_crop_fixed_size_changed)
            self.crop_x_spin.valueChanged.connect(self._on_crop_position_changed)
            self.crop_y_spin.valueChanged.connect(self._on_crop_position_changed)

    def _update_transform_status(self):
        parts = []
        if self._rotation_angle != 0:
            parts.append(f"旋转 {self._rotation_angle}°")
        if self._flip_h:
            parts.append("水平翻转")
        if self._flip_v:
            parts.append("垂直翻转")
        if parts:
            self.transform_status_label.setText(" | ".join(parts))
            self.transform_status_label.setStyleSheet("color: #4a9eff; font-size: 12px; font-weight: bold;")
        else:
            self.transform_status_label.setText("无变换")
            self.transform_status_label.setStyleSheet("color: #888; font-size: 12px;")

    def _update_transform_preview(self):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        transform = QTransform()
        if self._rotation_angle != 0:
            cx = self._original_pixmap.width() / 2
            cy = self._original_pixmap.height() / 2
            transform.translate(cx, cy)
            transform.rotate(self._rotation_angle)
            transform.translate(-cx, -cy)
        if self._flip_h or self._flip_v:
            sx = -1 if self._flip_h else 1
            sy = -1 if self._flip_v else 1
            if self._rotation_angle != 0:
                rotated = self._original_pixmap.transformed(QTransform().rotate(self._rotation_angle))
                w = rotated.width()
                h = rotated.height()
            else:
                w = self._original_pixmap.width()
                h = self._original_pixmap.height()
            transform.translate(w / 2, h / 2)
            transform.scale(sx, sy)
            transform.translate(-w / 2, -h / 2)
        if transform.isIdentity():
            transformed = self._original_pixmap
        else:
            transformed = self._original_pixmap.transformed(transform)
        scaled = transformed.scaled(
            self.preview_area.width() - 20, self.preview_area.height() - 20,
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)
        self._update_transform_status()

    def start_convert(self):
        if not self.files:
            QMessageBox.warning(self, "提示", "请先添加文件!")
            return
        if len(self.files) == 1:
            ext = '.jpg' if self.format_combo.currentText() == 'JPEG' else f'.{self.format_combo.currentText().lower()}'
            default_name = Path(self.files[0]).stem + ext
            save_path, _ = QFileDialog.getSaveFileName(
                self, "另存为", default_name,
                f"{self.format_combo.currentText()} Files (*{ext});;All Files (*)")
            if not save_path:
                return
            output_dir = str(Path(save_path).parent)
            output_filename = Path(save_path).name
        else:
            output_dir = QFileDialog.getExistingDirectory(self, "选择输出文件夹", "", QFileDialog.ShowDirsOnly)
            if not output_dir:
                return
            output_filename = None

        self.convert_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在转换...")

        crop_opts = None
        if self._crop_enabled and self._crop_rect is not None:
            crop_opts = {'enabled': True, 'rect': self._crop_rect}

        self.thread = ConversionThread(
            self.files, self.format_combo.currentText(), self.quality_slider.value(),
            output_dir,
            {'enabled': self.resize_checkbox.isChecked(), 'width': self.width_spinbox.value(),
             'height': self.height_spinbox.value(), 'keep_ratio': self.keep_ratio_checkbox.isChecked()},
            {'angle': self._rotation_angle, 'flip_h': self._flip_h, 'flip_v': self._flip_v},
            single_filename=output_filename, crop_opts=crop_opts
        )
        self.thread.progress_updated.connect(
            lambda v, n: (self.progress_bar.setValue(v), self.status_label.setText(f"处理: {n}")))
        self.thread.finished.connect(
            lambda s, m: (self.progress_bar.setValue(100), self.status_label.setText(m),
                         self.convert_btn.setEnabled(True), QMessageBox.information(self, "完成", m)))
        self.thread.start()

    def generate_icon(self):
        if not hasattr(self, 'icon_files') or not self.icon_files:
            QMessageBox.warning(self, "提示", "请先选择图片!")
            return
        preset_idx = self.icon_preset_combo.currentIndex()
        format_idx = self.icon_format_combo.currentIndex()
        file_path = self.icon_files[0]

        if preset_idx == 7:
            size = self.icon_size_spinbox.value()
        else:
            preset_sizes = {0: 256, 1: 180, 2: 192, 3: 32, 4: 180, 5: 150, 6: 512}
            size = preset_sizes.get(preset_idx, 256)

        format_names = {0: 'ICO', 1: 'PNG', 2: 'ICO'}
        output_format = format_names.get(format_idx, 'PNG')
        ext = '.ico' if output_format == 'ICO' else '.png'
        default_name = f"icon_{size}x{size}{ext}"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "另存为", default_name,
            f"{output_format} Files (*{ext});;All Files (*)")
        if not save_path:
            return

        self.icon_generate_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在生成图标...")

        output_path = Path(save_path)
        try:
            with ImageConverter(file_path) as converter:
                result_file = converter.generate_icon(output_path, size=size, output_format=output_format)
            self.progress_bar.setValue(100)
            self.status_label.setText("图标生成完成")
            QMessageBox.information(
                self, "完成",
                f"图标生成完成！\n尺寸: {size}×{size} px\n格式: {output_format}\n\n保存至: {result_file}")
        except Exception as e:
            self.status_label.setText("生成失败")
            QMessageBox.critical(self, "错误", f"生成图标时出错:\n{str(e)}")
        finally:
            self.icon_generate_btn.setEnabled(True)
