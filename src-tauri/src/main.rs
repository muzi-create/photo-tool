#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{Manager, WindowEvent};

struct Sidecar(Mutex<Option<Child>>);

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

fn main() {
    tauri::Builder::default()
        .manage(Sidecar(Mutex::new(None)))
        .setup(|app| {
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
            let child = Command::new(sidecar)
                .arg("--port")
                .arg(port.to_string())
                .env("PHOTOTOOL_LOG_DIR", log_path().and_then(|path| path.parent().map(Path::to_path_buf)).unwrap_or_default())
                .spawn()?;
            *app.state::<Sidecar>().0.lock().unwrap() = Some(child);

            let window = app.get_webview_window("main").expect("main window missing");
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
            if let WindowEvent::CloseRequested { .. } = event {
                if let Some(sidecar) = window.app_handle().try_state::<Sidecar>() {
                    if let Some(mut child) = sidecar.0.lock().unwrap().take() {
                        // PyInstaller one-file executables spawn an unpacked child
                        // process.  End the process tree so the HTTP server cannot
                        // survive after the desktop window has closed.
                        let _ = Command::new("taskkill")
                            .args(["/PID", &child.id().to_string(), "/T", "/F"])
                            .status();
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .unwrap_or_else(|error| log_message(format!("desktop runtime failed: {error}")));
}
