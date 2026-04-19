"""
可拖拽的裁剪选框控件（Rubber Band）
支持拖拽移动、边缘/角点调整尺寸
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor


class CropRubberBand(QWidget):
    """可拖拽的裁剪选框（Rubber Band）"""
    crop_changed = pyqtSignal(object)
    crop_cleared = pyqtSignal()

    MODE_NONE = 0
    MODE_MOVE = 1
    MODE_RESIZE_TL = 2
    MODE_RESIZE_TR = 3
    MODE_RESIZE_BL = 4
    MODE_RESIZE_BR = 5
    MODE_RESIZE_T = 6
    MODE_RESIZE_B = 7
    MODE_RESIZE_L = 8
    MODE_RESIZE_R = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.image_rect = None
        self._rubber_band = None
        self._origin = QPointF()
        self._drag_mode = self.MODE_NONE
        self._can_redraw = True
        self._edge_threshold = 8
        self.setStyleSheet("background: transparent; border: none;")

    def set_image_rect(self, rect):
        self.image_rect = rect
        if rect.width() > 0 and rect.height() > 0:
            self._rubber_band = QRectF(rect.x(), rect.y(), rect.width(), rect.height())
            self._can_redraw = False
        else:
            self._rubber_band = None
        self.update()

    def update_image_rect(self, rect):
        """更新 image_rect 坐标，同时按比例更新选框位置（不重置选框）"""
        if rect.width() <= 0 or rect.height() <= 0:
            self.image_rect = rect
            self._rubber_band = None
            self.update()
            return
        # 先保存选框在旧 image_rect 中的相对比例
        ratios = self._get_crop_rect_ratios()
        # 更新 image_rect
        self.image_rect = rect
        # 根据相对比例恢复选框在新 image_rect 中的位置
        if ratios is not None:
            x1_r, y1_r, x2_r, y2_r = ratios
            new_x = rect.x() + x1_r * rect.width()
            new_y = rect.y() + y1_r * rect.height()
            new_w = (x2_r - x1_r) * rect.width()
            new_h = (y2_r - y1_r) * rect.height()
            self._rubber_band = QRectF(new_x, new_y, new_w, new_h)
        else:
            # 没有选框时，设为整张图片
            self._rubber_band = QRectF(rect.x(), rect.y(), rect.width(), rect.height())
        self._can_redraw = False
        self.update()

    def reset_crop(self):
        if self.image_rect:
            self._rubber_band = QRectF(self.image_rect.x(), self.image_rect.y(),
                                       self.image_rect.width(), self.image_rect.height())
            self._can_redraw = False
            self.update()
            self.crop_changed.emit(self._get_crop_rect_ratios())
            self.crop_cleared.emit()

    def enable_redraw(self):
        self._can_redraw = True
        self._rubber_band = None
        self.update()

    def _get_crop_rect_ratios(self):
        if self._rubber_band is None or self.image_rect is None:
            return None
        if self.image_rect.width() <= 0 or self.image_rect.height() <= 0:
            return None
        img_x, img_y = self.image_rect.x(), self.image_rect.y()
        img_w, img_h = self.image_rect.width(), self.image_rect.height()
        rb = self._rubber_band.normalized()
        rb_x, rb_y = rb.x(), rb.y()
        rb_w, rb_h = rb.width(), rb.height()
        x1_ratio = max(0.0, min(1.0, (rb_x - img_x) / img_w))
        y1_ratio = max(0.0, min(1.0, (rb_y - img_y) / img_h))
        x2_ratio = max(0.0, min(1.0, (rb_x - img_x + rb_w) / img_w))
        y2_ratio = max(0.0, min(1.0, (rb_y - img_y + rb_h) / img_h))
        return (x1_ratio, y1_ratio, x2_ratio, y2_ratio)

    def _detect_drag_mode(self, pos):
        if self._rubber_band is None:
            return self.MODE_NONE
        rb = self._rubber_band.normalized()
        x, y = pos.x(), pos.y()
        t = self._edge_threshold
        if abs(x - rb.left()) <= t and abs(y - rb.top()) <= t:
            return self.MODE_RESIZE_TL
        if abs(x - rb.right()) <= t and abs(y - rb.top()) <= t:
            return self.MODE_RESIZE_TR
        if abs(x - rb.left()) <= t and abs(y - rb.bottom()) <= t:
            return self.MODE_RESIZE_BL
        if abs(x - rb.right()) <= t and abs(y - rb.bottom()) <= t:
            return self.MODE_RESIZE_BR
        if rb.left() - t <= x <= rb.right() + t and abs(y - rb.top()) <= t:
            return self.MODE_RESIZE_T
        if rb.left() - t <= x <= rb.right() + t and abs(y - rb.bottom()) <= t:
            return self.MODE_RESIZE_B
        if abs(x - rb.left()) <= t and rb.top() - t <= y <= rb.bottom() + t:
            return self.MODE_RESIZE_L
        if abs(x - rb.right()) <= t and rb.top() - t <= y <= rb.bottom() + t:
            return self.MODE_RESIZE_R
        if rb.contains(pos):
            return self.MODE_MOVE
        return self.MODE_NONE

    def _get_resize_cursor(self, mode):
        cursors = {
            self.MODE_RESIZE_TL: Qt.SizeFDiagCursor,
            self.MODE_RESIZE_BR: Qt.SizeFDiagCursor,
            self.MODE_RESIZE_TR: Qt.SizeBDiagCursor,
            self.MODE_RESIZE_BL: Qt.SizeBDiagCursor,
            self.MODE_RESIZE_T: Qt.SizeVerCursor,
            self.MODE_RESIZE_B: Qt.SizeVerCursor,
            self.MODE_RESIZE_L: Qt.SizeHorCursor,
            self.MODE_RESIZE_R: Qt.SizeHorCursor,
        }
        return cursors.get(mode, Qt.CrossCursor)

    def paintEvent(self, event):
        if self.image_rect is None:
            return
        img_x, img_y = self.image_rect.x(), self.image_rect.y()
        img_w, img_h = self.image_rect.width(), self.image_rect.height()
        if img_w <= 0 or img_h <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._rubber_band is None or self._rubber_band.width() <= 0 or self._rubber_band.height() <= 0:
            painter.setPen(QPen(QColor(100, 100, 100), 1, Qt.DashLine))
            painter.drawRect(int(img_x), int(img_y), int(img_w), int(img_h))
            return
        rb_rect = self._rubber_band.normalized().intersected(QRectF(img_x, img_y, img_w, img_h))
        rb_x, rb_y = rb_rect.x(), rb_rect.y()
        rb_w, rb_h = rb_rect.width(), rb_rect.height()
        if rb_w <= 0 or rb_h <= 0:
            return
        is_full_image = (abs(rb_x - img_x) < 1 and abs(rb_y - img_y) < 1 and
                         abs(rb_w - img_w) < 1 and abs(rb_h - img_h) < 1)
        # 遮罩
        painter.fillRect(QRectF(0, 0, self.width(), rb_y), QColor(0, 0, 0, 100))
        painter.fillRect(QRectF(0, rb_y + rb_h, self.width(), self.height() - rb_y - rb_h), QColor(0, 0, 0, 100))
        painter.fillRect(QRectF(0, rb_y, rb_x, rb_h), QColor(0, 0, 0, 100))
        painter.fillRect(QRectF(rb_x + rb_w, rb_y, self.width() - rb_x - rb_w, rb_h), QColor(0, 0, 0, 100))
        # 选区边框
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawRect(int(rb_x), int(rb_y), int(rb_w), int(rb_h))
        # 网格线
        if not is_full_image and rb_w > 30 and rb_h > 30:
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
            for i in range(1, 3):
                line_x = rb_x + rb_w * i / 3
                painter.drawLine(int(line_x), int(rb_y), int(line_x), int(rb_y + rb_h))
            for i in range(1, 3):
                line_y = rb_y + rb_h * i / 3
                painter.drawLine(int(rb_x), int(line_y), int(rb_x + rb_w), int(line_y))
        # 角点手柄
        if not is_full_image:
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            handle_size = 8
            corners = [(rb_x, rb_y), (rb_x + rb_w, rb_y), (rb_x, rb_y + rb_h), (rb_x + rb_w, rb_y + rb_h)]
            for hx, hy in corners:
                painter.drawRect(int(hx - handle_size / 2), int(hy - handle_size / 2), handle_size, handle_size)
        else:
            painter.setPen(QPen(QColor(255, 255, 255), 2, Qt.DashLine))
            painter.drawRect(int(rb_x), int(rb_y), int(rb_w), int(rb_h))

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self.image_rect is None:
            return
        pos = event.pos()
        if self._rubber_band is not None and self._rubber_band.width() > 0:
            self._drag_mode = self._detect_drag_mode(pos)
            if self._drag_mode != self.MODE_NONE:
                self._origin = pos
                self._rubber_band_start = QRectF(self._rubber_band)
                event.accept()
                return
        if self._can_redraw:
            img_x, img_y = self.image_rect.x(), self.image_rect.y()
            img_w, img_h = self.image_rect.width(), self.image_rect.height()
            if img_x <= pos.x() <= img_x + img_w and img_y <= pos.y() <= img_y + img_h:
                self._origin = pos
                self._rubber_band = QRectF(pos, pos)
                self._drag_mode = self.MODE_MOVE
                self._rubber_band_start = QRectF(self._rubber_band)
                self.update()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.image_rect is None:
            return
        pos = event.pos()
        if not (event.buttons() & Qt.LeftButton):
            if self._rubber_band is not None:
                mode = self._detect_drag_mode(pos)
                self.setCursor(self._get_resize_cursor(mode))
            else:
                self.setCursor(Qt.CrossCursor)
            return
        if self._drag_mode == self.MODE_NONE:
            return
        dx = pos.x() - self._origin.x()
        dy = pos.y() - self._origin.y()
        img_x = self.image_rect.x()
        img_y = self.image_rect.y()
        img_w = self.image_rect.width()
        img_h = self.image_rect.height()
        rb = QRectF(self._rubber_band_start)
        if self._drag_mode == self.MODE_MOVE:
            new_x = max(img_x, min(rb.x() + dx, img_x + img_w - rb.width()))
            new_y = max(img_y, min(rb.y() + dy, img_y + img_h - rb.height()))
            self._rubber_band = QRectF(new_x, new_y, rb.width(), rb.height())
        elif self._drag_mode == self.MODE_RESIZE_TL:
            new_x = max(img_x, rb.x() + dx)
            new_y = max(img_y, rb.y() + dy)
            new_w, new_h = rb.right() - new_x, rb.bottom() - new_y
            if new_w > 10 and new_h > 10:
                self._rubber_band = QRectF(new_x, new_y, new_w, new_h)
        elif self._drag_mode == self.MODE_RESIZE_TR:
            new_y = max(img_y, rb.y() + dy)
            new_w = min(img_x + img_w, rb.x() + rb.width() + dx) - rb.x()
            new_h = rb.bottom() - new_y
            if new_w > 10 and new_h > 10:
                self._rubber_band = QRectF(rb.x(), new_y, new_w, new_h)
        elif self._drag_mode == self.MODE_RESIZE_BL:
            new_x = max(img_x, rb.x() + dx)
            new_w = rb.right() - new_x
            new_h = min(img_y + img_h, rb.y() + rb.height() + dy) - rb.y()
            if new_w > 10 and new_h > 10:
                self._rubber_band = QRectF(new_x, rb.y(), new_w, new_h)
        elif self._drag_mode == self.MODE_RESIZE_BR:
            new_w = min(img_x + img_w, rb.x() + rb.width() + dx) - rb.x()
            new_h = min(img_y + img_h, rb.y() + rb.height() + dy) - rb.y()
            if new_w > 10 and new_h > 10:
                self._rubber_band = QRectF(rb.x(), rb.y(), new_w, new_h)
        elif self._drag_mode == self.MODE_RESIZE_T:
            new_y = max(img_y, rb.y() + dy)
            new_h = rb.bottom() - new_y
            if new_h > 10:
                self._rubber_band = QRectF(rb.x(), new_y, rb.width(), new_h)
        elif self._drag_mode == self.MODE_RESIZE_B:
            new_h = min(img_y + img_h, rb.y() + rb.height() + dy) - rb.y()
            if new_h > 10:
                self._rubber_band = QRectF(rb.x(), rb.y(), rb.width(), new_h)
        elif self._drag_mode == self.MODE_RESIZE_L:
            new_x = max(img_x, rb.x() + dx)
            new_w = rb.right() - new_x
            if new_w > 10:
                self._rubber_band = QRectF(new_x, rb.y(), new_w, rb.height())
        elif self._drag_mode == self.MODE_RESIZE_R:
            new_w = min(img_x + img_w, rb.x() + rb.width() + dx) - rb.x()
            if new_w > 10:
                self._rubber_band = QRectF(rb.x(), rb.y(), new_w, rb.height())
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_mode != self.MODE_NONE:
            if self._rubber_band.width() < 5 or self._rubber_band.height() < 5:
                self._rubber_band = QRectF(self.image_rect.x(), self.image_rect.y(),
                                           self.image_rect.width(), self.image_rect.height())
            self._drag_mode = self.MODE_NONE
            self.update()
            self.crop_changed.emit(self._get_crop_rect_ratios())
            event.accept()

    def set_crop_rect_from_size(self, width, height):
        """根据指定尺寸设置裁剪区域（居中）"""
        if self.image_rect is None:
            return
        if hasattr(self, '_preview_scale') and self._original_pixmap:
            scale = self._preview_scale
            preview_w = width * scale
            preview_h = height * scale
        else:
            img_w = self.image_rect.width()
            img_h = self.image_rect.height()
            orig_w = self._original_pixmap.width() if self._original_pixmap else 1
            orig_h = self._original_pixmap.height() if self._original_pixmap else 1
            scale_x = img_w / orig_w
            scale_y = img_h / orig_h
            preview_w = width * scale_x
            preview_h = height * scale_y
        x, y = self.image_rect.x(), self.image_rect.y()
        iw, ih = self.image_rect.width(), self.image_rect.height()
        cx, cy = x + iw / 2, y + ih / 2
        rx = cx - preview_w / 2
        ry = cy - preview_h / 2
        if rx < x: rx = x
        if ry < y: ry = y
        if rx + preview_w > x + iw: rx = x + iw - preview_w
        if ry + preview_h > y + ih: ry = y + ih - preview_h
        if preview_w > iw: preview_w, rx = iw, x
        if preview_h > ih: preview_h, ry = ih, y
        self._rubber_band = QRectF(rx, ry, preview_w, preview_h)
        self._can_redraw = False
        self.update()
        self.crop_changed.emit(self._get_crop_rect_ratios())
