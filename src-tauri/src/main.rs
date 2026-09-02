#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{Manager, WindowEvent};

struct Sidecar( Mutex<Option<Child>> );

fn main() {
    tauri::Builder::default()
        .manage(Sidecar(Mutex::new(None)))
        .setup(|app| {
            let resource_dir = app.path().resource_dir()?;
            let sidecar = resource_dir.join("sidecar").join("PhotoToolSidecar.exe");
            let child = Command::new(sidecar)
                .arg("--port")
                .arg("8765")
                .spawn()?;
            *app.state::<Sidecar>().0.lock().unwrap() = Some(child);

            let window = app.get_webview_window("main").expect("main window missing");
            let url = "http://127.0.0.1:8765/".parse().unwrap();
            thread::spawn(move || {
                thread::sleep(Duration::from_millis(450));
                let _ = window.navigate(url);
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                if let Some(sidecar) = window.app_handle().try_state::<Sidecar>() {
                    if let Some(mut child) = sidecar.0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running PhotoTool");
}
