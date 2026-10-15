//! Let desktop users choose where Reflex downloads are saved.

use tauri::webview::DownloadEvent;

#[cfg(windows)]
fn choose_destination(
    owner: windows::Win32::Foundation::HWND,
    suggested: &std::path::Path,
) -> std::io::Result<Option<std::path::PathBuf>> {
    use std::ffi::OsString;
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    use windows::core::{w, PCWSTR, PWSTR};
    use windows::Win32::UI::Controls::Dialogs::{
        CommDlgExtendedError, GetSaveFileNameW, OFN_EXPLORER, OFN_NOCHANGEDIR, OFN_OVERWRITEPROMPT,
        OFN_PATHMUSTEXIST, OPENFILENAMEW,
    };

    let mut filename = vec![0u16; 32768];
    let suggested_name: Vec<u16> = suggested
        .file_name()
        .unwrap_or_default()
        .encode_wide()
        .collect();
    if suggested_name.len() >= filename.len() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "Download filename is too long",
        ));
    }
    filename[..suggested_name.len()].copy_from_slice(&suggested_name);
    let extension: Vec<u16> = suggested
        .extension()
        .unwrap_or_default()
        .encode_wide()
        .chain(Some(0))
        .collect();
    let directory: Vec<u16> = suggested
        .parent()
        .unwrap_or_else(|| std::path::Path::new(""))
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();
    let mut dialog = OPENFILENAMEW {
        lStructSize: std::mem::size_of::<OPENFILENAMEW>() as u32,
        hwndOwner: owner,
        lpstrFile: PWSTR(filename.as_mut_ptr()),
        nMaxFile: filename.len() as u32,
        lpstrFilter: w!("所有文件 (*.*)\0*.*\0"),
        lpstrTitle: w!("保存生成结果"),
        lpstrDefExt: PCWSTR(extension.as_ptr()),
        lpstrInitialDir: PCWSTR(directory.as_ptr()),
        Flags: OFN_EXPLORER | OFN_NOCHANGEDIR | OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST,
        ..Default::default()
    };
    // All UTF-16 buffers outlive the modal dialog. Windows writes at most
    // nMaxFile code units, and NOCHANGEDIR preserves the application's cwd.
    unsafe {
        if !GetSaveFileNameW(&mut dialog).as_bool() {
            let error = CommDlgExtendedError();
            return if error.0 == 0 {
                Ok(None) // The user cancelled; no download should start.
            } else {
                Err(std::io::Error::other(format!(
                    "Save dialog failed: {}",
                    error.0
                )))
            };
        }
    }
    let length = filename
        .iter()
        .position(|unit| *unit == 0)
        .unwrap_or(filename.len());
    Ok(Some(OsString::from_wide(&filename[..length]).into()))
}

pub fn handle_download(webview: tauri::Webview, event: DownloadEvent<'_>) -> bool {
    match event {
        DownloadEvent::Requested { destination, .. } => {
            #[cfg(windows)]
            {
                let result = webview
                    .window()
                    .hwnd()
                    .map_err(std::io::Error::other)
                    .and_then(|owner| choose_destination(owner, destination));
                match result {
                    Ok(Some(path)) => {
                        *destination = path;
                        true
                    }
                    Ok(None) => false,
                    Err(error) => {
                        crate::log_message(format!("download save dialog failed: {error}"));
                        let _ = webview.eval("alert('无法打开保存窗口，请重试。')");
                        false
                    }
                }
            }
            #[cfg(not(windows))]
            true
        }
        DownloadEvent::Finished { path, success, .. } => {
            crate::log_message(format!(
                "download finished: path={path:?} success={success}"
            ));
            true
        }
        _ => true,
    }
}
