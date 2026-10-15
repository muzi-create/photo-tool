//! Close choices and system tray access for the packaged desktop app.

use std::sync::atomic::{AtomicBool, Ordering};
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::Manager;

#[derive(Default)]
struct ClosePrompt(AtomicBool);

#[derive(Debug, PartialEq, Eq)]
enum CloseAction {
    MinimizeToTray,
    Exit,
    Cancel,
}

fn restore_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if let Err(error) = window
            .show()
            .and_then(|_| window.unminimize())
            .and_then(|_| window.set_focus())
        {
            crate::log_message(format!("restoring main window failed: {error}"));
        }
    }
}

pub fn setup(app: &tauri::App) -> tauri::Result<()> {
    app.manage(ClosePrompt::default());
    let open = MenuItem::with_id(app, "tray_open", "打开 PhotoTool", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let exit = MenuItem::with_id(app, "tray_exit", "退出程序", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &separator, &exit])?;
    let icon = app.default_window_icon().cloned().ok_or_else(|| {
        std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "PhotoTool tray icon is missing",
        )
    })?;
    TrayIconBuilder::with_id("phototool_tray")
        .icon(icon)
        .tooltip("PhotoTool · 个人图片处理工作台")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "tray_open" => restore_window(app),
            "tray_exit" => app.exit(0),
            _ => (),
        })
        .on_tray_icon_event(|tray, event| {
            if matches!(
                event,
                TrayIconEvent::Click {
                    button: MouseButton::Left,
                    button_state: MouseButtonState::Up,
                    ..
                }
            ) {
                restore_window(tray.app_handle());
            }
        })
        .build(app)?;
    Ok(())
}

#[cfg(windows)]
fn close_action_from_button(button: i32) -> CloseAction {
    match button {
        100 => CloseAction::MinimizeToTray,
        101 => CloseAction::Exit,
        _ => CloseAction::Cancel,
    }
}

#[cfg(windows)]
fn ask_close_action(window: &tauri::Window) -> tauri::Result<CloseAction> {
    use windows::core::w;
    use windows::Win32::UI::Controls::{
        TaskDialogIndirect, TASKDIALOGCONFIG, TASKDIALOG_BUTTON, TDCBF_CANCEL_BUTTON,
        TDF_ALLOW_DIALOG_CANCELLATION, TDF_POSITION_RELATIVE_TO_WINDOW, TDF_USE_COMMAND_LINKS,
    };

    let buttons = [
        TASKDIALOG_BUTTON {
            nButtonID: 100,
            pszButtonText: w!("最小化到系统托盘\n保留当前工作，点击托盘图标可重新打开"),
        },
        TASKDIALOG_BUTTON {
            nButtonID: 101,
            pszButtonText: w!("退出程序\n关闭 PhotoTool 并停止后台服务"),
        },
    ];
    let dialog = TASKDIALOGCONFIG {
        cbSize: std::mem::size_of::<TASKDIALOGCONFIG>() as u32,
        hwndParent: window.hwnd()?,
        dwFlags: TDF_ALLOW_DIALOG_CANCELLATION
            | TDF_POSITION_RELATIVE_TO_WINDOW
            | TDF_USE_COMMAND_LINKS,
        dwCommonButtons: TDCBF_CANCEL_BUTTON,
        pszWindowTitle: w!("关闭 PhotoTool"),
        pszMainInstruction: w!("请选择关闭后的操作"),
        cButtons: buttons.len() as u32,
        pButtons: buttons.as_ptr(),
        nDefaultButton: 100,
        ..Default::default()
    };
    let mut button = 0;
    // The button array and all string literals outlive the modal dialog.
    unsafe { TaskDialogIndirect(&dialog, Some(&mut button), None, None) }
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    Ok(close_action_from_button(button))
}

#[cfg(not(windows))]
fn ask_close_action(_window: &tauri::Window) -> tauri::Result<CloseAction> {
    Ok(CloseAction::Exit)
}

pub fn request_close(window: &tauri::Window) {
    let prompt = window.state::<ClosePrompt>();
    // Modal dialogs pump Windows messages; avoid another prompt on reentry.
    if prompt.0.swap(true, Ordering::SeqCst) {
        return;
    }
    let action = ask_close_action(window);
    prompt.0.store(false, Ordering::SeqCst);
    match action {
        Ok(CloseAction::MinimizeToTray) => {
            if let Err(error) = window.hide() {
                crate::log_message(format!("minimizing to tray failed: {error}"));
            }
        }
        Ok(CloseAction::Exit) => window.app_handle().exit(0),
        Ok(CloseAction::Cancel) => (),
        Err(error) => crate::log_message(format!("close dialog failed: {error}")),
    }
}
