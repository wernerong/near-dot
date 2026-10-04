// Windows startup is explicitly per-user even if launched elevated.
// The Run value name matches productName for NSIS uninstall cleanup.
#[cfg(windows)]
pub fn set(_app: &tauri::AppHandle, enabled: bool) -> Result<(), String> {
    let key = windows_registry::CURRENT_USER
        .create(r"Software\Microsoft\Windows\CurrentVersion\Run")
        .map_err(|_| "Login startup could not be configured for this user.")?;
    let result = if enabled {
        let executable =
            std::env::current_exe().map_err(|_| "Application location is unavailable.")?;
        key.set_string(
            "Near Dot",
            format!("\"{}\" --autostart", executable.display()),
        )
    } else {
        key.remove_value("Near Dot")
    };
    match result {
        Ok(()) => Ok(()),
        Err(e) if !enabled && e.code().0 == 0x80070002u32 as i32 => Ok(()),
        Err(_) => Err("Login startup could not be changed for this user.".into()),
    }
}
#[cfg(not(windows))]
pub fn set(app: &tauri::AppHandle, enabled: bool) -> Result<(), String> {
    use tauri_plugin_autostart::ManagerExt;
    (if enabled {
        app.autolaunch().enable()
    } else {
        app.autolaunch().disable()
    })
    .map_err(|_| "Login startup could not be changed. Check OS login-item settings.".into())
}
