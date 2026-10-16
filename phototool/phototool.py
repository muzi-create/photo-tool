"""Personal Reflex user interface for PhotoTool."""

import reflex as rx

from phototool.web_state import ICON_PRESETS, PhotoToolState, TextAnnotation


BLUE = "#1769e0"


def app_icon(name: str, size: int = 18) -> rx.Component:
    return rx.icon(name, size=size)


def section_title(icon: str, title: str, description: str = "") -> rx.Component:
    return rx.hstack(
        rx.center(app_icon(icon, 17), class_name="section-icon"),
        rx.vstack(
            rx.text(title, class_name="section-title"),
            rx.cond(description != "", rx.text(description, class_name="section-description")),
            spacing="0",
            align="start",
        ),
        spacing="3",
        align="center",
        width="100%",
    )


def field(label: str, control: rx.Component, hint: str = "") -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(label, class_name="field-label"),
            rx.cond(hint != "", rx.text(hint, class_name="field-hint")),
            justify="between",
            width="100%",
        ),
        control,
        spacing="2",
        width="100%",
        align="start",
    )


def settings_section(icon: str, title: str, *children: rx.Component) -> rx.Component:
    return rx.el.details(
        rx.el.summary(section_title(icon, title), class_name="settings-summary"),
        rx.vstack(*children, spacing="4", width="100%", class_name="settings-body"),
        open=False,
        class_name="settings-section",
    )


def upload_button(upload_id: str, handler, label: str = "选择图片") -> rx.Component:
    return rx.upload(
        rx.button(app_icon("upload", 16), label, class_name="button-primary"),
        id=upload_id,
        accept={"image/*": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]},
        multiple=upload_id == "convert_upload",
        on_drop=handler(rx.upload_files(upload_id=upload_id)),
        border="none",
        padding="0",
    )


def empty_upload(upload_id: str, handler, title: str, subtitle: str) -> rx.Component:
    return rx.upload(
        rx.vstack(
            rx.center(app_icon("image-up", 30), class_name="upload-icon"),
            rx.text(title, class_name="upload-title"),
            rx.text(subtitle, class_name="upload-subtitle"),
            rx.button(app_icon("folder-open", 16), "浏览文件", class_name="button-secondary"),
            spacing="4",
            align="center",
        ),
        id=upload_id,
        accept={"image/*": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]},
        multiple=upload_id == "convert_upload",
        on_drop=handler(rx.upload_files(upload_id=upload_id)),
        class_name="upload-zone",
    )


def crop_handle(position: str) -> rx.Component:
    return rx.box(class_name=f"crop-handle crop-handle-{position}", custom_attrs={"data-handle": position})


def crop_overlay() -> rx.Component:
    return rx.cond(
        PhotoToolState.crop_enabled,
        rx.box(
            rx.box(
                crop_handle("nw"), crop_handle("n"), crop_handle("ne"), crop_handle("e"),
                crop_handle("se"), crop_handle("s"), crop_handle("sw"), crop_handle("w"),
                id="crop-selection",
                class_name="crop-selection",
                style=PhotoToolState.crop_selection_style,
            ),
            id="crop-stage-overlay",
            class_name="crop-overlay",
            custom_attrs={"data-crop-mode": PhotoToolState.crop_mode},
        ),
    )


def text_overlay() -> rx.Component:
    def annotation(box: TextAnnotation) -> rx.Component:
        return rx.el.button(
            rx.image(src=box.preview_url, alt=box.text, draggable=False, class_name="text-box-image"),
            *[
                rx.el.span(
                    class_name=f"text-resize-handle text-resize-{position}",
                    custom_attrs={"data-text-handle": position, "aria-hidden": "true"},
                )
                for position in ("nw", "n", "ne", "e", "se", "s", "sw", "w")
            ],
            type="button",
            on_click=PhotoToolState.select_text_box(box.id),
            class_name=rx.cond(
                PhotoToolState.text_selected_id == box.id,
                "text-annotation text-annotation-selected", "text-annotation",
            ),
            custom_attrs={"data-text-id": box.id, "data-text-layout": box.preview_layout,
                          "aria-label": "选择文字说明框", "style": box.style},
        )

    return rx.box(
        rx.foreach(PhotoToolState.text_boxes, annotation),
        class_name="text-overlay",
    )


def image_preview() -> rx.Component:
    return rx.section(
        rx.hstack(
            rx.hstack(
                rx.center(app_icon("image", 17), class_name="panel-heading-icon"),
                rx.vstack(
                    rx.text("图片预览", class_name="panel-title"),
                    rx.text(PhotoToolState.file_name, class_name="panel-subtitle"),
                    spacing="0",
                    align="start",
                ),
                spacing="3",
            ),
            rx.cond(
                PhotoToolState.has_files,
                rx.badge(PhotoToolState.file_count, " 个文件", color_scheme="blue", variant="soft"),
            ),
            justify="between",
            align="center",
            class_name="panel-header",
        ),
        rx.box(
            rx.cond(
                PhotoToolState.has_files,
                rx.box(
                    rx.box(
                        rx.image(src=PhotoToolState.preview_url, alt="图片预览", class_name="preview-image"),
                        text_overlay(),
                        crop_overlay(),
                        id="crop-stage",
                        class_name="crop-stage",
                    ),
                    class_name="preview-canvas",
                ),
                empty_upload("convert_upload", PhotoToolState.handle_upload, "拖放图片到这里", "支持单张上传，最大程度保留原图质量"),
            ),
            class_name="preview-workspace",
        ),
        rx.hstack(
            rx.hstack(
                rx.badge(PhotoToolState.image_width, " × ", PhotoToolState.image_height, color_scheme="gray", variant="surface"),
                rx.text(PhotoToolState.file_meta, class_name="meta-text"),
                spacing="3",
            ),
            rx.hstack(
                upload_button("convert_upload", PhotoToolState.handle_upload, "添加图片"),
                rx.button(app_icon("trash-2", 16), "清除", on_click=PhotoToolState.clear_files, class_name="button-ghost"),
                spacing="2",
            ),
            justify="between",
            align="center",
            class_name="panel-footer",
        ),
        class_name="panel preview-panel",
    )


def number_input(value, handler, minimum: int = 1, maximum: int = 10000, disabled=False) -> rx.Component:
    return rx.input(
        type="number", value=value, min=minimum, max=maximum,
        on_change=handler, disabled=disabled, class_name="field-control",
    )


def transform_button(icon: str, label: str, handler, active=False) -> rx.Component:
    return rx.button(
        app_icon(icon, 16), label, on_click=handler,
        class_name=rx.cond(active, "tool-button tool-button-active", "tool-button"),
    )


def crop_controls() -> rx.Component:
    presets = [
        "头像 200×200", "头像 500×500", "证件照 25×35", "壁纸 1920×1080",
        "壁纸 2560×1440", "微信封面 900×383", "小红书 1:1", "小红书 3:4",
    ]
    return rx.vstack(
        rx.hstack(
            rx.text("启用裁剪", class_name="field-label"),
            rx.switch(checked=PhotoToolState.crop_enabled, on_change=PhotoToolState.toggle_crop),
            justify="between",
            width="100%",
        ),
        rx.cond(
            PhotoToolState.crop_enabled,
            rx.vstack(
                field(
                    "选区模式",
                    rx.select(
                        ["自由选区", "固定尺寸", "锁定比例", "预设尺寸"],
                        value=PhotoToolState.crop_mode,
                        on_change=PhotoToolState.set_crop_mode,
                        width="100%",
                    ),
                ),
                rx.cond(
                    PhotoToolState.crop_mode == "锁定比例",
                    field("裁剪比例", rx.select(["1:1", "4:3", "16:9", "3:2", "2:3", "9:16"], value=PhotoToolState.crop_ratio, on_change=PhotoToolState.set_crop_ratio, width="100%")),
                ),
                rx.cond(
                    PhotoToolState.crop_mode == "预设尺寸",
                    rx.grid(
                        *[rx.button(name, on_click=PhotoToolState.apply_crop_preset(name), class_name="preset-button") for name in presets],
                        columns="2", spacing="2", width="100%",
                    ),
                ),
                rx.grid(
                    field("X", number_input(PhotoToolState.crop_pixel_x, PhotoToolState.set_crop_pixel_x, 0)),
                    field("Y", number_input(PhotoToolState.crop_pixel_y, PhotoToolState.set_crop_pixel_y, 0)),
                    field("宽度", number_input(PhotoToolState.crop_pixel_w, PhotoToolState.set_crop_pixel_w)),
                    field("高度", number_input(PhotoToolState.crop_pixel_h, PhotoToolState.set_crop_pixel_h)),
                    columns="2", spacing="3", width="100%",
                ),
                rx.text(PhotoToolState.crop_summary, class_name="selection-summary"),
                rx.hstack(
                    rx.button("应用选区", on_click=PhotoToolState.apply_crop, class_name="button-primary compact"),
                    rx.button(
                        app_icon("undo-2", 15),
                        rx.cond(PhotoToolState.crop_history_count > 0, rx.text("撤销 (", PhotoToolState.crop_history_count, ")"), rx.text("撤销")),
                        on_click=PhotoToolState.undo_crop,
                        disabled=PhotoToolState.crop_history_count == 0,
                        class_name="button-secondary compact",
                    ),
                    rx.button("重置", on_click=PhotoToolState.reset_crop, class_name="button-ghost compact"),
                    spacing="2",
                    width="100%",
                ),
                # These controlled ranges also receive pointer updates from crop_interactions.js.
                rx.el.input(id="crop-x", type="range", value=PhotoToolState.crop_x, min="0", max="100", step="0.1", on_change=PhotoToolState.set_crop_x, class_name="crop-sync-input"),
                rx.el.input(id="crop-y", type="range", value=PhotoToolState.crop_y, min="0", max="100", step="0.1", on_change=PhotoToolState.set_crop_y, class_name="crop-sync-input"),
                rx.el.input(id="crop-w", type="range", value=PhotoToolState.crop_w, min="1", max="100", step="0.1", on_change=PhotoToolState.set_crop_w, class_name="crop-sync-input"),
                rx.el.input(id="crop-h", type="range", value=PhotoToolState.crop_h, min="1", max="100", step="0.1", on_change=PhotoToolState.set_crop_h, class_name="crop-sync-input"),
                spacing="4", width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def text_controls() -> rx.Component:
    # Bind edits to their box so a delayed input event cannot edit a new selection.
    def edit(handler):
        return lambda value: handler(value, PhotoToolState.text_selected_id)

    return rx.vstack(
        rx.button(
            app_icon("plus", 16), "添加文字说明框",
            on_click=PhotoToolState.add_text_box,
            disabled=~PhotoToolState.has_files | (PhotoToolState.text_boxes.length() >= 20),
            class_name="button-secondary", width="100%",
        ),
        rx.text("拖动说明框内部可移动，拖动任意边框或角点可调整大小；批量导出时应用到所有图片。", class_name="field-hint"),
        rx.flex(
            rx.foreach(
                PhotoToolState.text_boxes,
                lambda box, index: rx.button(
                    "文字 ", index + 1,
                    on_click=PhotoToolState.select_text_box(box.id),
                    class_name=rx.cond(PhotoToolState.text_selected_id == box.id, "tool-button tool-button-active", "tool-button"),
                ),
            ),
            gap="2", wrap="wrap", width="100%",
        ),
        rx.cond(
            PhotoToolState.has_selected_text,
            rx.vstack(
                field("文字内容", rx.text_area(
                    value=PhotoToolState.text_content, on_change=edit(PhotoToolState.change_text_content),
                    placeholder="输入文字说明，支持换行", max_length=2000, rows="4",
                    class_name="text-content-input", width="100%",
                ), "最多 2000 字"),
                rx.grid(
                    field("字号 (px)", number_input(PhotoToolState.text_font_size, edit(PhotoToolState.change_text_font_size), 1, 500)),
                    field("说明框宽度 (%)", number_input(PhotoToolState.text_width, edit(PhotoToolState.change_text_width), 5, 100)),
                    columns="2", spacing="3", width="100%",
                ),
                rx.grid(
                    field("说明框高度 (%)", number_input(PhotoToolState.text_height, edit(PhotoToolState.change_text_height), 3, 100)),
                    field("尺寸模式", rx.button("自动适应文字", on_click=PhotoToolState.auto_text_height(PhotoToolState.text_selected_id), class_name="button-secondary compact", width="100%")),
                    columns="2", spacing="3", width="100%",
                ),
                rx.grid(
                    field("水平位置 (%)", number_input(PhotoToolState.text_x, edit(PhotoToolState.change_text_x), 0, 100)),
                    field("垂直位置 (%)", number_input(PhotoToolState.text_y, edit(PhotoToolState.change_text_y), 0, 100)),
                    columns="2", spacing="3", width="100%",
                ),
                rx.grid(
                    field("文字颜色", rx.el.input(type="color", value=PhotoToolState.text_color, on_change=edit(PhotoToolState.change_text_color), class_name="text-color-input", aria_label="文字颜色")),
                    field("背景颜色", rx.el.input(type="color", value=PhotoToolState.text_background, on_change=edit(PhotoToolState.change_text_background), class_name="text-color-input", aria_label="说明框背景颜色")),
                    columns="2", spacing="3", width="100%",
                ),
                field("背景不透明度", rx.hstack(
                    rx.el.input(type="range", value=PhotoToolState.text_opacity, min="0", max="100", on_change=edit(PhotoToolState.change_text_opacity), class_name="quality-range", aria_label="背景不透明度"),
                    rx.text(PhotoToolState.text_opacity, "%", class_name="field-hint"),
                    width="100%", align="center",
                ), "0% 为透明"),
                field("文字对齐", rx.select.root(
                    rx.select.trigger(width="100%"),
                    rx.select.content(
                        rx.select.item("左对齐", value="left"),
                        rx.select.item("居中", value="center"),
                        rx.select.item("右对齐", value="right"),
                    ),
                    value=PhotoToolState.text_align, on_change=edit(PhotoToolState.change_text_align),
                )),
                rx.hstack(
                    rx.hstack(rx.text("加粗", class_name="field-label"), rx.switch(checked=PhotoToolState.text_bold, on_change=edit(PhotoToolState.change_text_bold)), align="center", spacing="2"),
                    rx.button(app_icon("trash-2", 14), "删除说明框", on_click=PhotoToolState.delete_text_box, class_name="button-ghost compact"),
                    justify="between", width="100%", align="center",
                ),
                rx.text("调整宽度会自动换行，字号保持不变；超出说明框高度的文字会被裁切。", class_name="field-hint"),
                spacing="4", width="100%", key=PhotoToolState.text_selected_id,
            ),
        ),
        spacing="3", width="100%",
    )


def conversion_settings() -> rx.Component:
    return rx.section(
        rx.hstack(
            rx.vstack(rx.text("处理设置", class_name="panel-title"), rx.text("配置输出参数与编辑效果", class_name="panel-subtitle"), spacing="0", align="start"),
            rx.badge("实时预览", color_scheme="blue", variant="soft"),
            justify="between", align="center", class_name="panel-header",
        ),
        rx.box(
            settings_section(
                "file-output", "输出设置",
                field("输出格式", rx.select(["JPEG", "PNG", "WEBP", "BMP"], value=PhotoToolState.output_format, on_change=PhotoToolState.set_output_format, width="100%")),
                field(
                    "图片质量",
                    rx.vstack(
                        rx.el.input(type="range", value=PhotoToolState.quality, min="10", max="100", on_change=PhotoToolState.change_quality, class_name="quality-range"),
                        rx.hstack(rx.text("较小文件", class_name="field-hint"), rx.badge(PhotoToolState.quality, "%", color_scheme="blue"), rx.text("更高质量", class_name="field-hint"), justify="between", width="100%"),
                        width="100%", spacing="1",
                    ),
                ),
            ),
            settings_section(
                "scaling", "尺寸调整",
                rx.hstack(rx.text("启用尺寸调整", class_name="field-label"), rx.switch(checked=PhotoToolState.resize_enabled, on_change=PhotoToolState.set_resize_enabled), justify="between", width="100%"),
                rx.cond(
                    PhotoToolState.resize_enabled,
                    rx.vstack(
                        rx.grid(
                            field("宽度", number_input(PhotoToolState.resize_width, PhotoToolState.change_resize_width)),
                            field("高度", number_input(PhotoToolState.resize_height, PhotoToolState.change_resize_height)),
                            columns="2", spacing="3", width="100%",
                        ),
                        rx.hstack(rx.text("保持宽高比", class_name="field-label"), rx.switch(checked=PhotoToolState.keep_ratio, on_change=PhotoToolState.set_keep_ratio), justify="between", width="100%"),
                        width="100%", spacing="3",
                    ),
                ),
            ),
            settings_section(
                "rotate-cw", "旋转与翻转",
                rx.grid(
                    transform_button("rotate-ccw", "左转 90°", PhotoToolState.rotate_left),
                    transform_button("rotate-cw", "右转 90°", PhotoToolState.rotate_right),
                    transform_button("flip-horizontal-2", "水平翻转", PhotoToolState.toggle_flip_h, PhotoToolState.flip_h),
                    transform_button("flip-vertical-2", "垂直翻转", PhotoToolState.toggle_flip_v, PhotoToolState.flip_v),
                    columns="2", spacing="2", width="100%",
                ),
                rx.hstack(rx.text(PhotoToolState.transform_status, class_name="selection-summary"), rx.button("重置变换", on_click=PhotoToolState.reset_transform, class_name="link-button"), justify="between", width="100%"),
            ),
            settings_section("type", "文字说明", text_controls()),
            settings_section("crop", "裁剪设置", crop_controls()),
            class_name="settings-scroll",
        ),
        rx.box(
            rx.button(
                rx.cond(PhotoToolState.processing, rx.spinner(size="2"), app_icon("sparkles", 18)),
                rx.cond(PhotoToolState.file_count > 1, rx.text("批量保存并下载"), rx.text("保存编辑并下载")),
                on_click=PhotoToolState.convert_images,
                disabled=(PhotoToolState.file_count == 0) | PhotoToolState.processing,
                class_name="button-primary action-button",
            ),
            class_name="settings-footer",
        ),
        class_name="panel settings-panel",
    )


def convert_page() -> rx.Component:
    return rx.grid(image_preview(), conversion_settings(), width="100%", class_name="workspace-grid")


def icon_preview_panel() -> rx.Component:
    return rx.section(
        rx.hstack(
            rx.hstack(rx.center(app_icon("app-window", 17), class_name="panel-heading-icon"), rx.vstack(rx.text("图标预览", class_name="panel-title"), rx.text(PhotoToolState.icon_file_name, class_name="panel-subtitle"), spacing="0", align="start"), spacing="3"),
            rx.badge("智能适配", color_scheme="blue", variant="soft"),
            justify="between", align="center", class_name="panel-header",
        ),
        rx.box(
            rx.cond(
                PhotoToolState.has_icon_file,
                rx.vstack(
                    rx.box(rx.image(src=PhotoToolState.icon_preview_url, class_name="icon-source-preview"), class_name="icon-preview-checker"),
                    rx.hstack(rx.center(rx.image(src=PhotoToolState.corner_preview_url, class_name="corner-preview-image"), class_name="corner-preview-tile"), rx.vstack(rx.text("输出效果预览", class_name="field-label"), rx.text("自动居中裁切并保留透明通道", class_name="panel-subtitle"), align="start", spacing="1"), spacing="3", align="center", class_name="icon-preview-caption"),
                    spacing="5", align="center", class_name="icon-preview-content",
                ),
                empty_upload("icon_upload", PhotoToolState.handle_icon_upload, "上传图标源图", "建议使用 1024 × 1024 px 的 PNG 图片"),
            ),
            class_name="preview-workspace",
        ),
        rx.hstack(
            rx.text(PhotoToolState.icon_meta, class_name="meta-text"),
            rx.hstack(upload_button("icon_upload", PhotoToolState.handle_icon_upload, "更换图片"), rx.button(app_icon("trash-2", 16), "清除", on_click=PhotoToolState.clear_icon, class_name="button-ghost"), spacing="2"),
            justify="between", align="center", class_name="panel-footer",
        ),
        class_name="panel preview-panel",
    )


def icon_settings() -> rx.Component:
    preset_names = list(ICON_PRESETS) + ["自定义尺寸"]
    return rx.section(
        rx.hstack(rx.vstack(rx.text("图标设置", class_name="panel-title"), rx.text("生成系统级多尺寸图标", class_name="panel-subtitle"), spacing="0", align="start"), rx.badge("高质量", color_scheme="blue", variant="soft"), justify="between", class_name="panel-header"),
        rx.box(
            settings_section(
                "layout-grid", "图标预设",
                field("目标平台", rx.select(preset_names, value=PhotoToolState.icon_preset, on_change=PhotoToolState.set_icon_preset, width="100%")),
                rx.cond(PhotoToolState.icon_preset == "自定义尺寸", field("自定义尺寸", number_input(PhotoToolState.icon_size, PhotoToolState.set_icon_size, 16, 1024), "16–1024 px")),
                field("输出格式", rx.select(["ICO (多尺寸)", "PNG", "ICO + PNG"], value=PhotoToolState.icon_format, on_change=PhotoToolState.set_icon_format, width="100%")),
            ),
            settings_section(
                "squircle", "圆角设置",
                rx.hstack(rx.text("启用圆角遮罩", class_name="field-label"), rx.switch(checked=PhotoToolState.corner_enabled, on_change=PhotoToolState.set_corner_enabled), justify="between", width="100%"),
                rx.cond(
                    PhotoToolState.corner_enabled,
                    rx.vstack(
                        field("遮罩形状", rx.select(["圆角矩形", "圆形"], value=PhotoToolState.corner_shape, on_change=PhotoToolState.set_corner_shape, width="100%")),
                        field(
                            "圆角半径",
                            number_input(
                                PhotoToolState.displayed_corner_radius,
                                PhotoToolState.set_corner_radius,
                                1,
                                200,
                                disabled=PhotoToolState.is_circle_corner,
                            ),
                            PhotoToolState.corner_radius_hint,
                        ),
                        spacing="4", width="100%",
                    ),
                ),
            ),
            settings_section(
                "ruler", "生成尺寸",
                rx.vstack(
                    rx.flex(
                        rx.foreach(
                            PhotoToolState.icon_size_options,
                            lambda size: rx.checkbox(
                                rx.text(size, " × ", size, " px"),
                                checked=PhotoToolState.icon_selected_sizes.contains(size),
                                on_change=PhotoToolState.set_icon_size_selected(size),
                                class_name="icon-size-checkbox",
                            ),
                        ),
                        gap="3", wrap="wrap", width="100%",
                    ),
                    rx.hstack(
                        rx.button("全选", on_click=PhotoToolState.select_all_icon_sizes, class_name="link-button"),
                        rx.button("清除", on_click=PhotoToolState.clear_icon_sizes, class_name="link-button"),
                        spacing="2",
                    ),
                    rx.text("ICO 仅支持不超过 256 px 的已选尺寸", class_name="field-hint"),
                    spacing="2", width="100%", align="start",
                ),
            ),
            class_name="settings-scroll",
        ),
        rx.box(rx.button(app_icon("download", 18), "生成图标并下载", on_click=PhotoToolState.generate_icon, disabled=~PhotoToolState.has_icon_file | ~PhotoToolState.has_selected_icon_sizes | PhotoToolState.processing, class_name="button-primary action-button"), class_name="settings-footer"),
        class_name="panel settings-panel",
    )


def icon_page() -> rx.Component:
    return rx.grid(icon_preview_panel(), icon_settings(), width="100%", class_name="workspace-grid")


def sidebar_item(icon: str, label: str, mode: str) -> rx.Component:
    return rx.button(
        app_icon(icon, 19), rx.text(label, class_name="nav-label"),
        on_click=PhotoToolState.switch_mode(mode),
        title=label,
        aria_label=label,
        class_name=rx.cond(PhotoToolState.active_mode == mode, "nav-item nav-item-active", "nav-item"),
    )


def sidebar() -> rx.Component:
    return rx.el.aside(
        rx.hstack(rx.center(rx.text("PT", class_name="logo-mark"), class_name="logo-box"), rx.vstack(rx.text("PhotoTool", class_name="brand-name"), rx.text("IMAGE STUDIO", class_name="brand-kicker"), spacing="0", align="start"), spacing="3", class_name="brand"),
        rx.vstack(sidebar_item("images", "图片编辑", "convert"), sidebar_item("app-window", "图标生成", "icon"), spacing="2", width="100%", class_name="nav-list"),
        rx.spacer(),
        rx.box(rx.hstack(rx.center(app_icon("shield-check", 16), class_name="security-icon"), rx.vstack(rx.text("本地处理", class_name="security-title"), rx.text("文件不会上传云端", class_name="security-copy"), spacing="0", align="start"), spacing="3"), class_name="security-card"),
        class_name="sidebar",
    )


def topbar() -> rx.Component:
    return rx.el.header(
        rx.vstack(
            rx.text(rx.cond(PhotoToolState.active_mode == "convert", "图片编辑工作台", "应用图标生成器"), class_name="page-title"),
            rx.text(rx.cond(PhotoToolState.active_mode == "convert", "专业、可靠的图片编辑与导出工具", "面向多平台的一站式高质量图标输出"), class_name="page-subtitle"),
            spacing="0", align="start",
        ),
        rx.hstack(rx.badge(rx.icon("circle-check", size=14), PhotoToolState.status, color_scheme="blue", variant="soft", size="2"), rx.button(app_icon("circle-help", 17), "帮助", class_name="button-ghost"), spacing="3", align="center"),
        class_name="topbar",
    )


def index() -> rx.Component:
    return rx.box(
        rx.el.input(id="text-box-sync", type="text", default_value="", on_change=PhotoToolState.move_text_box, class_name="crop-sync-input", tab_index=-1, aria_hidden="true"),
        sidebar(),
        rx.box(
            topbar(),
            rx.el.main(rx.cond(PhotoToolState.active_mode == "convert", convert_page(), icon_page()), class_name="main-content"),
            rx.cond(PhotoToolState.processing, rx.box(rx.progress(value=PhotoToolState.progress, width="100%"), class_name="global-progress")),
            class_name="content-shell",
        ),
        class_name="app-shell",
    )


app = rx.App(
    theme=rx.theme(appearance="light", accent_color="blue", gray_color="slate", radius="large"),
    stylesheets=["/styles.css"],
    head_components=[
        rx.el.script(src="/crop_interactions.js", defer=True),
        rx.el.script(src="/text_interactions.js?v=resize-padding-5", defer=True),
    ],
)
app.add_page(index, route="/", title="PhotoTool · 个人图片处理工作台")
