#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::ffi::OsStr;
use std::net::{SocketAddr, TcpListener, TcpStream};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{Manager, WindowEvent};

mod downloads;
mod tray;

struct Sidecar(Mutex<Option<Child>>);

fn background_command(program: impl AsRef<OsStr>) -> Command {
    let mut command = Command::new(program);
    #[cfg(windows)]
    // GUI applications must also hide console helpers such as taskkill.
    command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    command
}

fn reserve_local_port() -> std::io::Result<u16> {
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    Ok(listener.local_addr()?.port())
}

fn log_path() -> Option<PathBuf> {
    let base = std::env::var_os("LOCALAPPDATA")?;
    let directory = PathBuf::from(base).join("PhotoTool").join("logs");
    std::fs::create_dir_all(&directory).ok()?;
    Some(directory.join("desktop.log"))
}

fn log_message(message: impl AsRef<str>) {
    use std::io::Write;
    if let Some(path) = log_path() {
        if let Ok(mut log) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
            let _ = writeln!(log, "{}", message.as_ref());
        }
    }
}

fn first_existing(candidates: impl IntoIterator<Item = PathBuf>) -> Option<PathBuf> {
    candidates.into_iter().find(|path| Path::new(path).is_file())
}

fn stop_sidecar(app: &tauri::AppHandle) {
    if let Some(sidecar) = app.try_state::<Sidecar>() {
        if let Some(mut child) = sidecar.0.lock().unwrap().take() {
            // PyInstaller's unpacked child must also stop when the app exits.
            let _ = background_command("taskkill")
                .args(["/PID", &child.id().to_string(), "/T", "/F"])
                .status();
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn main() {
    let app = tauri::Builder::default()
        .manage(Sidecar(Mutex::new(None)))
        .setup(|app| {
            // Register the download handler before the webview is created so
            // both development and packaged pages can choose a save location.
            let window = tauri::WebviewWindowBuilder::from_config(
                app,
                &app.config().app.windows[0],
            )?
            .on_download(downloads::handle_download)
            .build()?;
            tray::setup(app)?;
            let port = reserve_local_port()?;
            let resource_dir = app.path().resource_dir()?;
            log_message(format!("starting: resource_dir={} port={port}", resource_dir.display()));
            // Tauri preserves the source's `build/tauri-resources/sidecar` path under the
            // installer resource directory. Include `dist/sidecar` for packages
            // produced by earlier builds, so an in-place upgrade remains runnable.
            let mut sidecar_candidates = vec![
                resource_dir
                    .join("build")
                    .join("tauri-resources")
                    .join("sidecar")
                    .join("PhotoToolSidecar.exe"),
                resource_dir
                    .join("_up_")
                    .join("build")
                    .join("tauri-resources")
                    .join("sidecar")
                    .join("PhotoToolSidecar.exe"),
                resource_dir
                    .join("dist")
                    .join("sidecar")
                    .join("PhotoToolSidecar.exe"),
                resource_dir
                    .join("_up_")
                    .join("dist")
                    .join("sidecar")
                    .join("PhotoToolSidecar.exe"),
                resource_dir.join("sidecar").join("PhotoToolSidecar.exe"),
                resource_dir.join("PhotoToolSidecar.exe"),
            ];
            if let Some(local_app_data) = std::env::var_os("LOCALAPPDATA") {
                sidecar_candidates.push(
                    std::path::PathBuf::from(local_app_data.clone())
                        .join("PhotoTool")
                        .join("_up_")
                        .join("build")
                        .join("tauri-resources")
                        .join("sidecar")
                        .join("PhotoToolSidecar.exe"),
                );
                sidecar_candidates.push(
                    PathBuf::from(local_app_data)
                        .join("PhotoTool")
                        .join("_up_")
                        .join("dist")
                        .join("sidecar")
                        .join("PhotoToolSidecar.exe"),
                );
            }
            let sidecar = first_existing(sidecar_candidates).ok_or_else(|| {
                log_message("startup failed: PhotoToolSidecar.exe was not found in application resources");
                std::io::Error::new(
                    std::io::ErrorKind::NotFound,
                    "PhotoToolSidecar.exe was not found in application resources",
                )
            })?;
            log_message(format!("launching sidecar={}", sidecar.display()));
            let child = background_command(sidecar)
                .arg("--port")
                .arg(port.to_string())
                .env("PHOTOTOOL_LOG_DIR", log_path().and_then(|path| path.parent().map(Path::to_path_buf)).unwrap_or_default())
                .spawn()?;
            *app.state::<Sidecar>().0.lock().unwrap() = Some(child);

            let url = format!("http://127.0.0.1:{port}/").parse().unwrap();
            let address = SocketAddr::from(([127, 0, 0, 1], port));
            thread::spawn(move || {
                // A one-file PyInstaller sidecar may need extra time to unpack
                // on its first run, especially when antivirus scans the bundle.
                for _ in 0..480 {
                    if TcpStream::connect_timeout(&address, Duration::from_millis(200)).is_ok() {
                        log_message(format!("sidecar ready: port={}", address.port()));
                        let _ = window.navigate(url);
                        return;
                    }
                    thread::sleep(Duration::from_millis(250));
                }
                log_message("sidecar did not become ready within 120 seconds.");
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    api.prevent_close();
                    tray::request_close(window);
                }
            }
        })
        .build(tauri::generate_context!());
    match app {
        Ok(app) => app.run(|app, event| {
            // Hiding the window keeps the local service alive. Both the close
            // dialog and tray Exit menu reach this shared shutdown path.
            if matches!(event, tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit) {
                stop_sidecar(app);
            }
        }),
        Err(error) => log_message(format!("desktop runtime failed: {error}")),
    }
}
