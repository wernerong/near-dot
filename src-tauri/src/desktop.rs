//! Launch/focus a real external ChatGPT web-app window. No AI transport.
use std::{
    io::Write,
    process::Stdio,
    sync::{atomic::AtomicBool, Mutex},
    time::{Duration, Instant},
};
use tauri::Manager;

#[derive(Default)]
pub struct Desktop {
    operation: Mutex<()>,
    pub opening: AtomicBool,
    pub last_error: Mutex<Option<String>>,
}

#[cfg(windows)]
fn allow_helper_focus(pid: u32) {
    #[link(name = "user32")]
    unsafe extern "system" {
        fn AllowSetForegroundWindow(process_id: u32) -> i32;
    }
    // Only our freshly spawned, integrity-checked helper receives the grant.
    // Windows still decides whether this user-initiated caller may grant focus.
    // Never use ASFW_ANY or change the system foreground-lock policy.
    unsafe { AllowSetForegroundWindow(pid) };
}

pub fn open(app: &tauri::AppHandle, url: &str) -> Result<(), String> {
    if !cfg!(target_os = "windows") {
        return Err("The dedicated ChatGPT app window is currently available on Windows.".into());
    }
    let url = crate::destination::validate(url)?;
    let state = app.state::<Desktop>();
    let _guard = state
        .operation
        .try_lock()
        .map_err(|_| "ChatGPT is already opening. Give it a moment.")?;
    let pet = app
        .get_webview_window("companion")
        .ok_or("The pet window is unavailable.")?;
    let pos = pet
        .outer_position()
        .map_err(|_| "The pet position is unavailable.")?;
    let size = pet
        .outer_size()
        .map_err(|_| "The pet size is unavailable.")?;
    let scale = pet.scale_factor().unwrap_or(1.);
    let width = (430. * scale) as u32;
    let height = (580. * scale) as u32;
    let xy = crate::geometry::recover(
        (
            pos.x + size.width as i32 - width as i32,
            pos.y - height as i32 - (12. * scale) as i32,
        ),
        (width, height),
        &crate::areas(&pet),
    );
    let s = app.state::<crate::AppState>();
    let directory = s
        .path
        .parent()
        .ok_or("Chat app storage is unavailable.")?
        .join("chat-app");
    let topmost = s.preferences.lock().unwrap().always_on_top;
    let value = serde_json::json!({"operation":"open", "url":url, "rect":[xy.0,xy.1,width,height], "topmost":topmost});
    let mut child = crate::chat::helper(app, "chat_app.py")?
        .arg("--state")
        .arg(directory)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "Chat app window controls could not start.")?;
    #[cfg(windows)]
    allow_helper_focus(child.id());
    let result = (|| {
        let mut input = child.stdin.take().ok_or("Chat app input is unavailable.")?;
        let bytes =
            serde_json::to_vec(&value).map_err(|_| "Chat app request could not be prepared.")?;
        input
            .write_all(&bytes)
            .map_err(|_| "Chat app controls closed.")?;
        drop(input);
        let start = Instant::now();
        loop {
            if child
                .try_wait()
                .map_err(|_| "Chat app controls could not complete.")?
                .is_some()
            {
                break;
            }
            if start.elapsed() > Duration::from_secs(45) {
                return Err("ChatGPT is still opening. Click the pet again in a moment.".into());
            }
            std::thread::sleep(Duration::from_millis(20));
        }
        Ok(())
    })();
    if let Err(error) = result {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }
    let output = child
        .wait_with_output()
        .map_err(|_| "Chat app controls could not complete.")?;
    if output.stdout.len() > 8192 {
        return Err("Invalid chat app response.".into());
    }
    let response: serde_json::Value =
        serde_json::from_slice(&output.stdout).map_err(|_| "Invalid chat app response.")?;
    if response.get("ok") != Some(&serde_json::json!(true)) {
        return Err(response
            .get("error")
            .and_then(|v| v.as_str())
            .unwrap_or("The ChatGPT app window could not open.")
            .into());
    }
    Ok(())
}
