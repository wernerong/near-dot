mod avatar;
mod chat;
mod destination;
mod geometry;
mod preferences;
mod startup;
mod updates;

use preferences::Preferences;
use std::{
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex,
    },
    time::Duration,
};
use tauri::{Emitter, LogicalSize, Manager, PhysicalPosition, WebviewWindow, WindowEvent};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};
use tauri_plugin_opener::OpenerExt;

static STARTED: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
static START_RECORDED: AtomicBool = AtomicBool::new(false);
fn measure_startup() {
    if std::env::args().any(|a| a == "--measure-startup")
        && !START_RECORDED.swap(true, Ordering::Relaxed)
    {
        if let Some(t) = STARTED.get() {
            eprintln!("NEAR_DOT_STARTUP_MS={}", t.elapsed().as_millis());
        }
    }
}

pub struct AppState {
    avatar: Mutex<avatar::View>,
    avatar_operation: tokio::sync::Mutex<()>,
    preferences: Mutex<Preferences>,
    path: PathBuf,
    load_error: Mutex<Option<String>>,
    shortcut_warning: Mutex<Option<String>>,
    tested_destination: Mutex<Option<String>>,
    hidden: AtomicBool,
    pending: Mutex<Option<updates::Pending>>,
    update_lock: tokio::sync::Mutex<()>,
    restart_ready: AtomicBool,
    update_status: Mutex<Option<updates::Status>>,
    position_dirty: AtomicBool,
    last_move: Mutex<std::time::Instant>,
}
fn set_floating(window: &WebviewWindow, enabled: bool) -> tauri::Result<()> {
    window.set_always_on_top(enabled)?;
    #[cfg(target_os = "macos")]
    window.set_visible_on_all_workspaces(enabled)?;
    Ok(())
}

fn avatar_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_config_dir()
        .map(|p| p.join("avatar.png"))
        .map_err(|_| "Local image directory is unavailable.".into())
}
#[tauri::command]
fn get_avatar(w: WebviewWindow, app: tauri::AppHandle) -> Result<avatar::View, String> {
    known(&w)?;
    Ok(app.state::<AppState>().avatar.lock().unwrap().clone())
}
#[tauri::command]
async fn import_avatar(
    w: WebviewWindow,
    app: tauri::AppHandle,
    kind: Option<avatar::Kind>,
) -> Result<avatar::View, String> {
    known(&w)?;
    if !["settings", "chat"].contains(&w.label()) {
        return Err("Choose an image from Chat or Settings.".into());
    }
    let kind = kind.unwrap_or_default();
    let state = app.state::<AppState>();
    let _operation = state.avatar_operation.lock().await;
    let (sender, receiver) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .set_parent(&w)
        .set_title(match kind {
            avatar::Kind::Image => "Choose your companion icon",
            avatar::Kind::Pet => "Import your pet sprite sheet",
        })
        .add_filter("Still PNG image", &["png"])
        .pick_file(move |file| {
            let _ = sender.send(file);
        });
    let file = receiver
        .await
        .map_err(|_| "Image selection could not finish.")?;
    let Some(file) = file else {
        return Ok(state.avatar.lock().unwrap().clone());
    };
    let source = file.into_path().map_err(|_| "Choose a local image file.")?;
    let destination = avatar_path(&app)?;
    let view =
        tauri::async_runtime::spawn_blocking(move || avatar::import(&source, &destination, kind))
            .await
            .map_err(|_| "Image could not be prepared.")??;
    *app.state::<AppState>().avatar.lock().unwrap() = view.clone();
    let _ = app.emit("avatar-changed", view.clone());
    Ok(view)
}
#[tauri::command]
async fn reset_avatar(w: WebviewWindow, app: tauri::AppHandle) -> Result<avatar::View, String> {
    known(&w)?;
    if !["settings", "chat"].contains(&w.label()) {
        return Err("Choose an image from Chat or Settings.".into());
    }
    let state = app.state::<AppState>();
    let _operation = state.avatar_operation.lock().await;
    let path = avatar_path(&app)?;
    let view = tauri::async_runtime::spawn_blocking(move || avatar::reset(&path))
        .await
        .map_err(|_| "Default image could not be restored.")??;
    *app.state::<AppState>().avatar.lock().unwrap() = view.clone();
    let _ = app.emit("avatar-changed", view.clone());
    Ok(view)
}
fn settings_only(w: &WebviewWindow) -> Result<(), String> {
    known(w)?;
    if w.label() == "settings" {
        Ok(())
    } else {
        Err("This action is available in Settings.".into())
    }
}
fn known(w: &WebviewWindow) -> Result<(), String> {
    let url = w
        .url()
        .map_err(|_| "Window origin could not be verified.")?;
    let local = (url.scheme() == "tauri" && url.host_str() == Some("localhost"))
        || (matches!(url.scheme(), "http" | "https") && url.host_str() == Some("tauri.localhost"));
    let dev = cfg!(debug_assertions)
        && url.scheme() == "http"
        && url.host_str() == Some("127.0.0.1")
        && url.port() == Some(1420);
    if !local && !dev {
        return Err("OS actions require the packaged local UI.".into());
    }
    if ["settings", "companion", "chat", "bubble"].contains(&w.label()) {
        Ok(())
    } else {
        Err("Unknown window.".into())
    }
}
fn show_settings(app: &tauri::AppHandle) {
    if let Some(w) = app.get_webview_window("settings") {
        let _ = w.show();
        let _ = w.set_focus();
    }
}
fn place_near_companion(app: &tauri::AppHandle, label: &str) {
    let Some(pet) = app.get_webview_window("companion") else {
        return;
    };
    let Some(panel) = app.get_webview_window(label) else {
        return;
    };
    if let (Ok(pos), Ok(size), Ok(pet_size)) =
        (pet.outer_position(), panel.outer_size(), pet.outer_size())
    {
        let gap = (12. * pet.scale_factor().unwrap_or(1.)) as i32;
        let target = (
            pos.x + pet_size.width as i32 - size.width as i32,
            pos.y - size.height as i32 - gap,
        );
        let xy = geometry::recover(target, (size.width, size.height), &areas(&pet));
        let _ = panel.set_position(PhysicalPosition::new(xy.0, xy.1));
    }
}
fn show_latest_reply(app: &tauri::AppHandle) {
    let reply = app
        .state::<chat::Chat>()
        .snapshot
        .lock()
        .unwrap()
        .messages
        .iter()
        .rev()
        .find_map(|m| m.reply.clone());
    if let Some(reply) = reply {
        let text: String = if app
            .state::<AppState>()
            .preferences
            .lock()
            .unwrap()
            .reply_preview
        {
            reply.chars().take(160).collect()
        } else {
            "Your dot replied. Click to read and respond.".into()
        };
        let _ = app.emit_to("bubble", "reply-preview", serde_json::json!({"text":text}));
        place_near_companion(app, "bubble");
        if let Some(w) = app.get_webview_window("bubble") {
            // Explicit menu/button action may focus a reply for keyboard access.
            let _ = w.set_focusable(true);
            let _ = w.show();
            let _ = w.set_focus();
        }
    } else {
        show_chat(app);
    }
}
fn show_chat(app: &tauri::AppHandle) {
    if !chat::enabled() {
        show_settings(app);
        return;
    }
    let _ = app.emit_to("companion", "reply-available", false);
    if let Some(b) = app.get_webview_window("bubble") {
        let _ = b.hide();
    }
    if let Some(w) = app.get_webview_window("chat") {
        place_near_companion(app, "chat");
        let _ = set_floating(
            &w,
            app.state::<AppState>()
                .preferences
                .lock()
                .unwrap()
                .always_on_top,
        );
        let _ = w.show();
        let _ = w.set_focus();
        let _ = app.emit_to("chat", "chat-focus", ());
    }
}
fn activate(app: &tauri::AppHandle) -> Result<(), String> {
    if chat::enabled() {
        show_chat(app);
        Ok(())
    } else {
        launch(app).inspect_err(|message| {
            show_settings(app);
            let _ = app.emit_to("settings", "app-error", message);
        })
    }
}
#[tauri::command]
fn get_chat(w: WebviewWindow, app: tauri::AppHandle) -> Result<chat::Snapshot, String> {
    known(&w)?;
    if w.label() != "chat" {
        return Err("Message history is available only in Chat.".into());
    }
    Ok(app.state::<chat::Chat>().snapshot.lock().unwrap().clone())
}
#[tauri::command]
async fn send_chat(
    w: WebviewWindow,
    app: tauri::AppHandle,
    text: String,
) -> Result<chat::Snapshot, String> {
    known(&w)?;
    if w.label() != "chat" {
        return Err("Send from the Chat window.".into());
    }
    chat::validate_message(&text)?;
    let handle = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        handle.state::<chat::Chat>().request(
            &handle,
            serde_json::json!({"operation":"send", "text":text}),
        )
    })
    .await
    .map_err(|_| "Message could not be sent. Check saved messages before trying again.")?
}
#[tauri::command]
async fn retry_chat(
    w: WebviewWindow,
    app: tauri::AppHandle,
    message_id: String,
) -> Result<chat::Snapshot, String> {
    known(&w)?;
    if w.label() != "chat"
        || message_id.len() != 32
        || !message_id.chars().all(|c| c.is_ascii_hexdigit())
    {
        return Err("Invalid local message.".into());
    }
    let handle = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        handle.state::<chat::Chat>().request(
            &handle,
            serde_json::json!({"operation":"retry", "messageId":message_id}),
        )
    })
    .await
    .map_err(|_| "Retry could not complete. Saved messages are preserved.")?
}
#[tauri::command]
async fn connect_chat(w: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    known(&w)?;
    if w.label() != "chat" {
        return Err("Reconnect from Chat.".into());
    }
    tauri::async_runtime::spawn_blocking(move || app.state::<chat::Chat>().connect(&app))
        .await
        .map_err(|_| "Reconnect could not complete.")?
}
fn chat_monitor(app: tauri::AppHandle) {
    std::thread::spawn(move || {
        let mut initialized = false;
        loop {
            if app.state::<chat::Chat>().stopped() {
                break;
            }
            let result = app
                .state::<chat::Chat>()
                .request(&app, serde_json::json!({"operation":"snapshot"}));
            let snapshot = result.unwrap_or_else(|_| {
                let chat = app.state::<chat::Chat>();
                let mut saved = chat.snapshot.lock().unwrap();
                saved.connected = false;
                saved.state = "disconnected".into();
                saved.clone()
            });
            if !initialized
                && !snapshot.transport_running
                && snapshot.expires_in.is_some_and(|v| v > 0)
            {
                let _ = app.state::<chat::Chat>().connect(&app);
            }
            let replies: Vec<String> = snapshot
                .messages
                .iter()
                .filter(|m| m.reply.is_some())
                .map(|m| m.id.clone())
                .collect();
            let state = app.state::<chat::Chat>();
            let new_reply = {
                let mut seen = state.seen.lock().unwrap();
                let new_reply = snapshot
                    .messages
                    .iter()
                    .rev()
                    .find(|m| m.reply.is_some() && !seen.contains(&m.id))
                    .cloned();
                *seen = replies;
                new_reply
            };
            let pending = snapshot
                .messages
                .iter()
                .any(|m| m.delivered == 1 && m.reply.is_none());
            let _ = app.emit_to("chat", "chat-state", &snapshot);
            let _ = app.emit_to("companion", "chat-indicator", serde_json::json!({"pending":pending && snapshot.connected,"connected":snapshot.connected}));
            if initialized {
                if let Some(reply) = new_reply {
                    let visible = app
                        .get_webview_window("chat")
                        .is_some_and(|w| w.is_visible().unwrap_or(false));
                    if !visible && !app.state::<AppState>().hidden.load(Ordering::Relaxed) {
                        let preview = app
                            .state::<AppState>()
                            .preferences
                            .lock()
                            .unwrap()
                            .reply_preview;
                        let text: String = if preview {
                            reply.reply.unwrap_or_default().chars().take(160).collect()
                        } else {
                            "Your dot replied. Click to read and respond.".into()
                        };
                        let _ = app.emit_to(
                            "bubble",
                            "reply-preview",
                            serde_json::json!({"text":text}),
                        );
                        place_near_companion(&app, "bubble");
                        if let Some(w) = app.get_webview_window("bubble") {
                            let _ = set_floating(
                                &w,
                                app.state::<AppState>()
                                    .preferences
                                    .lock()
                                    .unwrap()
                                    .always_on_top,
                            );
                            let _ = w.set_focusable(false);
                            // Incoming replies never request focus. The accessible
                            // badge confirms the actual window was shown.
                            if w.show().is_ok() && w.is_visible().unwrap_or(false) {
                                let _ = app.emit_to("companion", "reply-available", true);
                            }
                        }
                    }
                }
            }
            initialized = true;
            let active = pending
                || app
                    .get_webview_window("chat")
                    .is_some_and(|w| w.is_visible().unwrap_or(false));
            std::thread::sleep(Duration::from_secs(if active { 2 } else { 10 }));
        }
    });
}
fn launch(app: &tauri::AppHandle) -> Result<(), String> {
    let p = app.state::<AppState>().preferences.lock().unwrap().clone();
    if !p.verified || p.destination.is_empty() {
        show_settings(app);
        return Err("Save a locally tested destination first.".into());
    }
    let url = destination::validate(&p.destination)?;
    app.opener().open_url(url, None::<&str>).map_err(|_| {
        "The default browser could not open the destination. Check your OS browser settings.".into()
    })
}
fn areas<R: tauri::Runtime>(w: &WebviewWindow<R>) -> Vec<geometry::Rect> {
    w.available_monitors()
        .unwrap_or_default()
        .iter()
        .map(|m| {
            let a = m.work_area();
            geometry::Rect {
                x: a.position.x,
                y: a.position.y,
                width: a.size.width,
                height: a.size.height,
            }
        })
        .collect()
}
fn recover<R: tauri::Runtime>(app: &tauri::AppHandle<R>, reset: bool) {
    // Native windows can emit DPI events while Tauri is still creating them,
    // before setup registers AppState. Setup performs recovery once it is ready.
    let Some(state) = app.try_state::<AppState>() else {
        return;
    };
    let Some(w) = app.get_webview_window("companion") else {
        return;
    };
    let areas = areas(&w);
    let size = w.outer_size().ok();
    let pos = if reset {
        areas.first().map(|a| {
            (
                a.x.saturating_add(a.width as i32).saturating_sub(230),
                a.y.saturating_add(a.height as i32).saturating_sub(240),
            )
        })
    } else {
        w.outer_position().ok().map(|p| (p.x, p.y))
    };
    if let (Some(pos), Some(size)) = (pos, size) {
        let xy = geometry::recover(pos, (size.width, size.height), &areas);
        if xy != pos || reset {
            let _ = w.set_position(PhysicalPosition::new(xy.0, xy.1));
        }
        state.preferences.lock().unwrap().position = Some(xy);
    }
}
fn persist(app: &tauri::AppHandle) -> Result<(), String> {
    let s = app.state::<AppState>();
    if s.load_error.lock().unwrap().is_some() {
        return Err("Repair settings before saving; the original is preserved.".into());
    }
    let result = preferences::save(&s.path, &s.preferences.lock().unwrap());
    result
}
fn companion_data(app: &tauri::AppHandle) -> serde_json::Value {
    let s = app.state::<AppState>();
    let p = s.preferences.lock().unwrap();
    serde_json::json!({"size":p.size,"opacity":p.opacity,"paused":p.paused,"hidden":s.hidden.load(Ordering::Relaxed),"configured":p.verified,"chatEnabled":chat::enabled(),"alwaysOnTop":app.get_webview_window("companion").and_then(|w| w.is_always_on_top().ok()).unwrap_or(false)})
}
fn changed(app: &tauri::AppHandle) {
    let _ = app.emit_to("companion", "companion-config", companion_data(app));
    let _ = app.emit_to("settings", "preferences-changed", ());
}
fn toggle(app: &tauri::AppHandle) {
    let s = app.state::<AppState>();
    let hide = !s.hidden.load(Ordering::Relaxed);
    s.hidden.store(hide, Ordering::Relaxed);
    if let Some(w) = app.get_webview_window("companion") {
        if hide {
            if let Some(b) = app.get_webview_window("bubble") {
                let _ = b.hide();
            }
            if let Some(c) = app.get_webview_window("chat") {
                let _ = c.hide();
            }
            let _ = w.hide();
        } else {
            recover(app, false);
            let _ = set_floating(&w, s.preferences.lock().unwrap().always_on_top);
            let _ = w.show();
        }
    }
    changed(app);
}
#[tauri::command]
fn get_preferences(w: WebviewWindow, app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    settings_only(&w)?;
    measure_startup();
    let s = app.state::<AppState>();
    let preferences = s.preferences.lock().unwrap().clone();
    Ok(
        serde_json::json!({"preferences":preferences,"warning":s.load_error.lock().unwrap().clone().or(s.shortcut_warning.lock().unwrap().clone()),"version":app.package_info().version.to_string(),"setupRequired":preferences.needs_setup(),"chatEnabled":chat::enabled(),"updatesConfigured":updates::configured(&app),"updateStatus":s.update_status.lock().unwrap().clone()}),
    )
}
#[tauri::command]
fn get_companion(w: WebviewWindow, app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    known(&w)?;
    measure_startup();
    Ok(companion_data(&app))
}
#[tauri::command]
fn open_destination(w: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    known(&w)?;
    launch(&app)
}
#[tauri::command]
fn test_destination(w: WebviewWindow, app: tauri::AppHandle, url: String) -> Result<(), String> {
    settings_only(&w)?;
    let url = destination::validate(&url)?;
    app.opener()
        .open_url(&url, None::<&str>)
        .map_err(|_| "Browser launch failed.".to_string())?;
    *app.state::<AppState>().tested_destination.lock().unwrap() = Some(url);
    Ok(())
}
#[tauri::command]
fn save_preferences(
    w: WebviewWindow,
    app: tauri::AppHandle,
    mut preferences: Preferences,
) -> Result<(), String> {
    settings_only(&w)?;
    preferences.validate()?;
    let s = app.state::<AppState>();
    if s.load_error.lock().unwrap().is_some() {
        return Err("Repair settings first; the original file is preserved.".into());
    }
    let old = s.preferences.lock().unwrap().clone();
    preferences.position = old.position;
    preferences.cohort = old.cohort;
    if !preferences.destination.is_empty() {
        preferences.destination = destination::validate(&preferences.destination)?;
    }
    if preferences.verified
        && !(old.verified && old.destination == preferences.destination)
        && s.tested_destination.lock().unwrap().as_ref() != Some(&preferences.destination)
    {
        return Err("Use Test link on this device before confirming your destination.".into());
    }
    let shortcut_changed = old.shortcut != preferences.shortcut;
    if shortcut_changed && !preferences.shortcut.is_empty() {
        app.global_shortcut().register(preferences.shortcut.as_str()).map_err(|_|"Shortcut is invalid or already in use. Choose another; your previous shortcut is still active.")?;
    }
    if preferences.startup != old.startup {
        let result = startup::set(&app, preferences.startup);
        if result.is_err() {
            if shortcut_changed && !preferences.shortcut.is_empty() {
                let _ = app
                    .global_shortcut()
                    .unregister(preferences.shortcut.as_str());
            }
            return Err(
                "Startup setting could not be changed. Check OS login-item permissions.".into(),
            );
        }
    }
    if let Err(e) = preferences::save(&s.path, &preferences) {
        if shortcut_changed && !preferences.shortcut.is_empty() {
            let _ = app
                .global_shortcut()
                .unregister(preferences.shortcut.as_str());
        }
        let _ = startup::set(&app, old.startup);
        return Err(e);
    }
    if shortcut_changed && !old.shortcut.is_empty() {
        let _ = app.global_shortcut().unregister(old.shortcut.as_str());
    }
    *s.preferences.lock().unwrap() = preferences.clone();
    if let Some(pet) = app.get_webview_window("companion") {
        set_floating(&pet, preferences.always_on_top).map_err(|_| {
            "Settings saved, but always-on-top could not be applied. Restart the app to retry."
                .to_string()
        })?;
        for label in ["chat", "bubble"] {
            if let Some(window) = app.get_webview_window(label) {
                set_floating(&window, preferences.always_on_top).map_err(|_| "Settings saved, but always-on-top could not be applied. Restart the app to retry.".to_string())?;
            }
        }
        let _ = pet.set_size(LogicalSize::new(
            preferences.size as f64,
            preferences.size as f64 + 20.,
        ));
    }
    if shortcut_changed {
        *s.shortcut_warning.lock().unwrap() = None;
    }
    recover(&app, false);
    changed(&app);
    Ok(())
}
#[tauri::command]
fn repair_preferences(w: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    settings_only(&w)?;
    let s = app.state::<AppState>();
    if s.path.exists() {
        std::fs::copy(&s.path, s.path.with_extension("preserved.json"))
            .map_err(|_| "Original settings could not be preserved.")?;
    }
    startup::set(&app, false)?;
    let _ = app.global_shortcut().unregister_all();
    let p = Preferences {
        shortcut: String::new(),
        ..Default::default()
    };
    preferences::save(&s.path, &p)?;
    *s.preferences.lock().unwrap() = p;
    *s.load_error.lock().unwrap() = None;
    *s.shortcut_warning.lock().unwrap() = None;
    recover(&app, true);
    changed(&app);
    Ok(())
}
#[tauri::command]
fn companion_action(w: WebviewWindow, app: tauri::AppHandle, action: String) -> Result<(), String> {
    known(&w)?;
    match action.as_str() {
        "settings" => show_settings(&app),
        "activate" => activate(&app)?,
        "chat" => show_chat(&app),
        "latest-reply" => show_latest_reply(&app),
        "dismiss-reply" => {
            let _ = app.emit_to("companion", "reply-available", false);
            if let Some(b) = app.get_webview_window("bubble") {
                let _ = b.hide();
            }
        }
        "close-chat" => {
            if let Some(c) = app.get_webview_window("chat") {
                let _ = c.hide();
            }
        }
        "toggle" => toggle(&app),
        "drag" => {
            if w.label() != "companion" {
                return Err("Drag is available on the companion.".into());
            }
            w.start_dragging()
                .map_err(|_| "Could not start dragging.")?;
        }
        "recover" => recover(&app, true),
        "drag-finished" => {
            recover(&app, false);
            persist(&app)?;
        }
        "quit" => {
            let _ = persist(&app);
            app.state::<chat::Chat>().shutdown();
            app.exit(0);
        }
        _ => return Err("Unknown action.".into()),
    }
    Ok(())
}
#[tauri::command]
async fn check_update(w: WebviewWindow, app: tauri::AppHandle) -> Result<updates::Status, String> {
    settings_only(&w)?;
    let result = updates::check(&app, true).await;
    if let Ok(status) = &result {
        *app.state::<AppState>().update_status.lock().unwrap() = Some(status.clone());
    }
    result
}
#[tauri::command]
async fn install_update(w: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    settings_only(&w)?;
    updates::install(&app).await
}
#[tauri::command]
fn restart_after_update(w: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    settings_only(&w)?;
    if !app
        .state::<AppState>()
        .restart_ready
        .load(Ordering::Relaxed)
    {
        return Err("No installed update awaits restart.".into());
    }
    let _ = persist(&app);
    app.restart();
}
fn tray(app: &tauri::AppHandle) -> tauri::Result<()> {
    use tauri::menu::{Menu, MenuItem};
    let items = [
        ("chat", "Chat with my dot"),
        ("latest-reply", "Show latest reply"),
        ("open", "Open in ChatGPT"),
        ("toggle", "Hide / show companion"),
        ("pause", "Pause / resume animation"),
        ("recover", "Reset position"),
        ("settings", "Settings and updates"),
        ("quit", "Quit"),
    ]
    .iter()
    .filter(|(id, _)| chat::enabled() || !["chat", "latest-reply"].contains(id))
    .map(|(id, text)| MenuItem::with_id(app, *id, *text, true, None::<&str>))
    .collect::<tauri::Result<Vec<_>>>()?;
    let version = MenuItem::with_id(
        app,
        "version",
        format!("Near Dot v{}", app.package_info().version),
        false,
        None::<&str>,
    )?;
    let mut items = items;
    items.insert(0, version);
    let refs = items
        .iter()
        .map(|m| m as &dyn tauri::menu::IsMenuItem<tauri::Wry>)
        .collect::<Vec<_>>();
    let menu = Menu::with_items(app, &refs)?;
    tauri::tray::TrayIconBuilder::with_id("near-dot")
        .icon(app.default_window_icon().unwrap().clone())
        .tooltip("Near Dot • Independent launcher")
        .menu(&menu)
        .show_menu_on_left_click(true)
        .on_menu_event(|app, e| match e.id.as_ref() {
            "open" => {
                if let Err(message) = launch(app) {
                    show_settings(app);
                    let _ = app.emit_to("settings", "app-error", message);
                }
            }
            "chat" => show_chat(app),
            "latest-reply" => show_latest_reply(app),
            "toggle" => toggle(app),
            "recover" => {
                recover(app, true);
                let _ = persist(app);
            }
            "settings" => show_settings(app),
            "pause" => {
                let s = app.state::<AppState>();
                {
                    let mut p = s.preferences.lock().unwrap();
                    p.paused = !p.paused;
                }
                let _ = persist(app);
                changed(app);
            }
            "quit" => {
                let _ = persist(app);
                app.state::<chat::Chat>().shutdown();
                app.exit(0);
            }
            _ => {}
        })
        .build(app)?;
    Ok(())
}
pub fn run() {
    let _ = STARTED.set(std::time::Instant::now());
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            show_settings(app)
        }))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(
            tauri_plugin_autostart::Builder::new()
                .app_name("Near Dot")
                .arg("--autostart")
                .build(),
        )
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, _, event| {
                    if event.state() == ShortcutState::Pressed {
                        let _ = activate(app);
                    }
                })
                .build(),
        )
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            let path = app.path().app_config_dir()?.join("preferences.json");
            let (mut p, error) = match preferences::load(&path) {
                Ok(p) => (p, None),
                Err(e) => (Preferences::default(), Some(e)),
            };
            if !path.exists() {
                // Persist a random local rollout bucket; it is never transmitted.
                p.cohort = (std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .subsec_nanos()
                    % 100) as u8;
            }
            let warning = if !p.shortcut.is_empty()
                && app.global_shortcut().register(p.shortcut.as_str()).is_err()
            {
                Some(
                    "The configured shortcut is unavailable. Use Settings to choose another."
                        .into(),
                )
            } else {
                None
            };
            app.manage(AppState {
                avatar: Mutex::new(avatar::load(&path.with_file_name("avatar.png"))),
                avatar_operation: tokio::sync::Mutex::new(()),
                preferences: Mutex::new(p.clone()),
                path,
                load_error: Mutex::new(error),
                shortcut_warning: Mutex::new(warning),
                tested_destination: Mutex::new(None),
                hidden: AtomicBool::new(false),
                pending: Mutex::new(None),
                update_lock: tokio::sync::Mutex::new(()),
                restart_ready: AtomicBool::new(false),
                update_status: Mutex::new(None),
                position_dirty: AtomicBool::new(false),
                last_move: Mutex::new(std::time::Instant::now()),
            });
            app.manage(chat::Chat::default());
            if chat::enabled() {
                chat_monitor(app.handle().clone());
            }
            let pet = app.get_webview_window("companion").unwrap();
            pet.set_size(LogicalSize::new(p.size as f64, p.size as f64 + 20.))?;
            set_floating(&pet, p.always_on_top)?;
            if let Some((x, y)) = p.position {
                pet.set_position(PhysicalPosition::new(x, y))?;
            }
            recover(app.handle(), p.position.is_none());
            tray(app.handle())?;
            let manual_install = p.unattended_next_launch
                && !std::env::args().any(|a| a == "--autostart" || a == "--no-unattended")
                && app.state::<AppState>().load_error.lock().unwrap().is_none();
            if !manual_install {
                pet.show()?;
            }
            if !manual_install
                && (p.needs_setup() || app.state::<AppState>().load_error.lock().unwrap().is_some())
            {
                show_settings(app.handle());
            }
            if manual_install {
                // One-shot opt-in: clear before attempting installation so restart cannot loop.
                app.state::<AppState>()
                    .preferences
                    .lock()
                    .unwrap()
                    .unattended_next_launch = false;
                persist(app.handle())?;
                let handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    let result = async {
                        let status = updates::check(&handle, false).await?;
                        if status.state == "available" {
                            updates::install(&handle).await?;
                            handle.restart();
                        }
                        Ok::<(), String>(())
                    }
                    .await;
                    if let Err(notes) = result {
                        *handle.state::<AppState>().update_status.lock().unwrap() =
                            Some(updates::Status {
                                state: "error".into(),
                                notes,
                                ..Default::default()
                            });
                        show_settings(&handle);
                    }
                    if let Some(w) = handle.get_webview_window("companion") {
                        let _ = w.show();
                    }
                    if !handle
                        .state::<AppState>()
                        .preferences
                        .lock()
                        .unwrap()
                        .verified
                    {
                        show_settings(&handle);
                    }
                    changed(&handle);
                });
            }
            let _ = persist(app.handle());
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let mut ticks = 0u8;
                loop {
                    std::thread::sleep(Duration::from_secs(1));
                    ticks = (ticks + 1) % 15;
                    if ticks == 0 {
                        recover(&handle, false);
                    }
                    let s = handle.state::<AppState>();
                    if s.position_dirty.load(Ordering::Relaxed)
                        && s.last_move.lock().unwrap().elapsed() >= Duration::from_millis(500)
                    {
                        s.position_dirty.store(false, Ordering::Relaxed);
                        recover(&handle, false);
                        let _ = persist(&handle);
                    }
                }
            });
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(Duration::from_secs(30)).await;
                loop {
                    if updates::configured(&handle)
                        && handle
                            .state::<AppState>()
                            .preferences
                            .lock()
                            .unwrap()
                            .auto_check
                    {
                        let status = match updates::check(&handle, false).await {
                            Ok(s) => s,
                            Err(e) => updates::Status {
                                state: "error".into(),
                                notes: e,
                                ..Default::default()
                            },
                        };
                        *handle.state::<AppState>().update_status.lock().unwrap() =
                            Some(status.clone());
                        let _ = handle.emit_to("settings", "update-status", status);
                    }
                    tokio::time::sleep(Duration::from_secs(6 * 60 * 60)).await;
                }
            });
            Ok(())
        })
        .on_window_event(|w, e| {
            // Window creation may pump native events before setup runs.
            let Some(s) = w.app_handle().try_state::<AppState>() else {
                return;
            };
            if matches!(e, WindowEvent::Focused(_)) && w.label() == "companion" {
                let _ = w.app_handle().emit_to(
                    "companion",
                    "companion-config",
                    companion_data(w.app_handle()),
                );
            }
            if let WindowEvent::Moved(pos) = e {
                if w.label() == "companion" {
                    s.preferences.lock().unwrap().position = Some((pos.x, pos.y));
                    *s.last_move.lock().unwrap() = std::time::Instant::now();
                    s.position_dirty.store(true, Ordering::Relaxed);
                    if w.app_handle()
                        .get_webview_window("bubble")
                        .is_some_and(|b| b.is_visible().unwrap_or(false))
                    {
                        place_near_companion(w.app_handle(), "bubble");
                    }
                }
            }
            if let WindowEvent::CloseRequested { api, .. } = e {
                api.prevent_close();
                if ["settings", "chat", "bubble"].contains(&w.label()) {
                    let _ = w.hide();
                } else {
                    toggle(w.app_handle());
                }
            }
            if matches!(e, WindowEvent::ScaleFactorChanged { .. }) && w.label() == "companion" {
                recover(w.app_handle(), false);
            }
        })
        .invoke_handler(tauri::generate_handler![
            connect_chat,
            get_chat,
            send_chat,
            retry_chat,
            get_avatar,
            import_avatar,
            reset_avatar,
            get_preferences,
            get_companion,
            save_preferences,
            repair_preferences,
            open_destination,
            test_destination,
            companion_action,
            check_update,
            install_update,
            restart_after_update
        ])
        .build(tauri::generate_context!())
        .expect("Near Dot could not start")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                app.state::<chat::Chat>().shutdown();
            }
        });
}

#[cfg(test)]
mod window_startup_tests {
    use super::*;

    #[test]
    fn recovery_before_setup_preserves_the_window_without_panicking() {
        let app = tauri::test::mock_app();
        let window = tauri::WebviewWindowBuilder::new(&app, "companion", Default::default())
            .build()
            .unwrap();
        // A valid window already exists when an early DPI callback arrives.
        let position = window.outer_position().unwrap();
        assert!(window.outer_size().is_ok());
        assert!(app.try_state::<AppState>().is_none());

        recover(app.handle(), false);
        recover(app.handle(), true);

        assert_eq!(window.outer_position().unwrap(), position);
        assert!(app.try_state::<AppState>().is_none());
    }
}
