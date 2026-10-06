//! Fixed local relay operations. No shell, URLs or credential inputs are accepted
//! from the renderer. Windows credentials are collected by a native OS prompt.
use serde::{Deserialize, Serialize};
use std::{
    io::{BufRead, BufReader, Read, Write},
    process::{Child, ChildStdin, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc, Mutex,
    },
    time::Duration,
};
use tauri::Manager;

pub fn enabled() -> bool {
    cfg!(target_os = "windows") || transport_enabled()
}
pub fn transport_enabled() -> bool {
    cfg!(target_os = "windows") || cfg!(all(feature = "private-relay", target_os = "macos"))
}

fn script(app: &tauri::AppHandle, name: &str) -> Result<std::path::PathBuf, String> {
    if cfg!(debug_assertions) {
        Ok(std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../experiments/dot-relay")
            .join(name))
    } else {
        Ok(app
            .path()
            .resource_dir()
            .map_err(|_| "Chat resources are unavailable.")?
            .join("relay")
            .join(name))
    }
}

fn runtime(app: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    #[cfg(target_os = "windows")]
    {
        let root = if cfg!(debug_assertions) {
            std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("relay-runtime")
        } else {
            app.path()
                .resource_dir()
                .map_err(|_| "Chat resources are unavailable.")?
                .join("relay-runtime")
        };
        // The trusted manifest is compiled into Rust, never read from a mutable
        // sidecar. Verify Python, DLLs, stdlib and client before executing them.
        let expected: std::collections::BTreeMap<String, String> =
            serde_json::from_str(include_str!("../relay-runtime/runtime-manifest.json"))
                .map_err(|_| "Invalid packaged runtime manifest.")?;
        use sha2::{Digest, Sha256};
        for (relative, hash) in expected {
            let path = root.join(relative);
            let meta = std::fs::symlink_metadata(&path)
                .map_err(|_| "The packaged chat runtime is incomplete.")?;
            use std::os::windows::fs::MetadataExt;
            if meta.file_attributes() & 0x400 != 0 || !meta.is_file() {
                return Err("Chat runtime links are forbidden.".into());
            }
            let bytes =
                std::fs::read(path).map_err(|_| "The packaged chat runtime is unavailable.")?;
            if format!("{:x}", Sha256::digest(bytes)) != hash {
                return Err("Chat runtime verification failed. Nothing was started.".into());
            }
        }
        Ok(root)
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = app;
        Ok(std::path::PathBuf::from("/usr/bin"))
    }
}

fn helper(app: &tauri::AppHandle, name: &str) -> Result<Command, String> {
    let root = runtime(app)?;
    let python = if cfg!(target_os = "windows") {
        root.join("python/python.exe")
    } else {
        root.join("python3")
    };
    let mut command = Command::new(python);
    let script = if cfg!(target_os = "windows") {
        root.join("relay").join(name)
    } else {
        script(app, name)?
    };
    command.args(["-I", "-u", "-c"])
        .arg("import sys,runpy; from pathlib import Path; p=Path(sys.argv.pop(1)); sys.path.insert(0,str(p.parent)); runpy.run_path(str(p),run_name='__main__')")
        .arg(script);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    Ok(command)
}

fn setup_operation(app: &tauri::AppHandle, operation: &str) -> Result<(), String> {
    let mut child = helper(app, "setup.py")?
        .arg(operation)
        .stdin(if operation == "configure" {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "The local connection setup could not start.")?;
    // Keep the input handle open during a native prompt. If Near Dot exits,
    // EOF tells the helper to close its prompt rather than becoming orphaned.
    let parent_lifetime = child.stdin.take();
    let output = child
        .wait_with_output()
        .map_err(|_| "The local connection setup could not complete.")?;
    drop(parent_lifetime);
    let value: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|_| "The local connection setup could not complete.")?;
    if !output.status.success() || value.get("ok") != Some(&serde_json::json!(true)) {
        return Err(value
            .get("error")
            .and_then(|v| v.as_str())
            .unwrap_or("The local connection setup failed.")
            .into());
    }
    Ok(())
}
fn require_private() -> Result<(), String> {
    if transport_enabled() {
        Ok(())
    } else {
        Err("Desktop chat and ChatGPT history sync are unavailable in this public preview.".into())
    }
}

#[derive(Clone, Default, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Message {
    pub id: String,
    pub text: String,
    pub created: f64,
    pub delivered: u8,
    pub reply: Option<String>,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Snapshot {
    pub connected: bool,
    pub transport_running: bool,
    pub state: String,
    pub expires_in: Option<u64>,
    pub messages: Vec<Message>,
}
impl Default for Snapshot {
    fn default() -> Self {
        Self {
            connected: false,
            transport_running: false,
            state: if enabled() && !transport_enabled() {
                "interface-only"
            } else {
                "unconfigured"
            }
            .into(),
            expires_in: None,
            messages: vec![],
        }
    }
}
#[derive(Default)]
pub struct Chat {
    bridge: Mutex<Option<Bridge>>,
    tunnel: Mutex<Option<Child>>,
    stopped: AtomicBool,
    pub snapshot: Mutex<Snapshot>,
    pub seen: Mutex<Vec<String>>,
}
struct Bridge {
    child: Child,
    input: ChildStdin,
    output: mpsc::Receiver<String>,
}
impl Drop for Bridge {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
impl Bridge {
    fn start(app: &tauri::AppHandle) -> Result<Self, String> {
        require_private()?;
        let mut child = helper(app, "desktop.py")?
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|_| {
                "The private chat helper could not start. Python 3 is required for this preview."
            })?;
        let input = child.stdin.take().ok_or("Chat input is unavailable.")?;
        let output = child.stdout.take().ok_or("Chat output is unavailable.")?;
        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || {
            let mut reader = BufReader::new(output);
            loop {
                let mut line = String::new();
                match reader.by_ref().take(524289).read_line(&mut line) {
                    Ok(0) | Err(_) => break,
                    Ok(_) if line.len() > 524288 || !line.ends_with('\n') => break,
                    Ok(_) => {
                        if tx.send(line).is_err() {
                            break;
                        }
                    }
                }
            }
        });
        Ok(Self {
            child,
            input,
            output: rx,
        })
    }
    fn request(&mut self, request: serde_json::Value) -> Result<Snapshot, String> {
        let mut bytes =
            serde_json::to_vec(&request).map_err(|_| "Message could not be prepared.")?;
        bytes.push(b'\n');
        self.input
            .write_all(&bytes)
            .and_then(|_| self.input.flush())
            .map_err(|_| "Chat connection closed.")?;
        let line = self.output.recv_timeout(Duration::from_secs(25)).map_err(|_| "Connection check timed out. A sent message may still arrive; check saved messages before sending again.")?;
        let response: serde_json::Value =
            serde_json::from_str(&line).map_err(|_| "Invalid chat response.")?;
        let value = response
            .get("ok")
            .ok_or("The private connection is unavailable. Saved messages are preserved.")?;
        let snapshot: Snapshot =
            serde_json::from_value(value.clone()).map_err(|_| "Invalid chat state.")?;
        if snapshot.messages.len() > 50
            || snapshot.messages.iter().any(|m| {
                m.text.chars().count() > 1024
                    || m.reply.as_ref().is_some_and(|r| r.chars().count() > 1024)
            })
        {
            return Err("Chat response exceeds the preview limit.".into());
        }
        Ok(snapshot)
    }
}
impl Chat {
    pub fn stopped(&self) -> bool {
        self.stopped.load(Ordering::Relaxed)
    }
    pub fn shutdown(&self) {
        self.stopped.store(true, Ordering::Relaxed);
        if let Some(mut child) = self.tunnel.lock().unwrap().take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        // An in-flight helper request may finish after stdin closes on exit;
        // never block the UI on a network timeout while quitting.
        if let Ok(mut bridge) = self.bridge.try_lock() {
            *bridge = None;
        }
    }
    pub fn connect(&self, app: &tauri::AppHandle) -> Result<(), String> {
        self.connect_inner(app, true)
    }
    pub fn auto_connect(&self, app: &tauri::AppHandle) -> Result<(), String> {
        self.connect_inner(app, false)
    }
    fn connect_inner(&self, app: &tauri::AppHandle, resume: bool) -> Result<(), String> {
        #[cfg(not(target_os = "windows"))]
        let _ = resume;
        require_private()?;
        let snapshot = self.request(app, serde_json::json!({"operation":"snapshot"}))?;
        if snapshot.connected {
            return Ok(());
        }
        if snapshot.expires_in == Some(0) {
            return Err("The private connection has expired or is not configured. Renew it through the reviewed connection setup.".into());
        }
        if snapshot.transport_running {
            return Err("The local client is running, but the dot is not connected. Check the key expiration and dot subscription.".into());
        }
        let mut tunnel = self.tunnel.lock().unwrap();
        if let Some(child) = tunnel.as_mut() {
            if child
                .try_wait()
                .map_err(|_| "Could not inspect the connection.")?
                .is_none()
            {
                return Ok(());
            }
        }
        #[cfg(target_os = "windows")]
        {
            setup_operation(app, if resume { "check" } else { "automatic-check" })?;
            if resume {
                setup_operation(app, "resume")?;
            }
            let mut started = helper(app, "connect.py")?
                .args(["run", "--client"])
                .arg(runtime(app)?.join("tunnel/tunnel-client.exe"))
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .map_err(|_| "The local connection could not start.")?;
            std::thread::sleep(Duration::from_millis(500));
            if started
                .try_wait()
                .map_err(|_| "Connection check failed.")?
                .is_some()
            {
                return Err(
                    "The local connection could not start. Check your tunnel authorization.".into(),
                );
            }
            *tunnel = Some(started);
            Ok(())
        }
        #[cfg(not(target_os = "windows"))]
        {
            let state = app
                .path()
                .home_dir()
                .map_err(|_| "Private connection directory unavailable.")?
                .join("Library/Application Support/Near Dot/transport-proof");
            let client = state.join("tunnel-client");
            for path in [
                &state,
                &client,
                &state.join("runtime.key"),
                &state.join("connection.json"),
            ] {
                let meta = std::fs::symlink_metadata(path)
                    .map_err(|_| "The private connection setup is incomplete.")?;
                if meta.file_type().is_symlink() {
                    return Err("Private connection files cannot be symlinks.".into());
                }
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    if meta.permissions().mode() & 0o077 != 0 {
                        return Err("Private connection file permissions need repair.".into());
                    }
                }
            }
            use sha2::{Digest, Sha256};
            let binary =
                std::fs::read(&client).map_err(|_| "The verified tunnel client is missing.")?;
            if format!("{:x}", Sha256::digest(&binary))
                != "f534872593a60b12560b6c74cbbf94adf6f7e1d9fdd67a3f59b8268ff8a8249c"
            {
                return Err("Tunnel client verification failed. It was not started.".into());
            }
            let metadata: serde_json::Value = serde_json::from_slice(
                &std::fs::read(state.join("connection.json"))
                    .map_err(|_| "Connection metadata unavailable.")?,
            )
            .map_err(|_| "Invalid connection metadata.")?;
            let id = metadata
                .get("tunnel_id")
                .and_then(|v| v.as_str())
                .filter(|v| {
                    v.starts_with("tunnel_")
                        && v.chars()
                            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
                })
                .ok_or("Invalid tunnel identifier.")?;
            let script = if cfg!(debug_assertions) {
                std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("../experiments/dot-relay/relay.py")
            } else {
                app.path()
                    .resource_dir()
                    .map_err(|_| "Chat resources unavailable.")?
                    .join("relay/relay.py")
            };
            // The official client takes one shell-quoted command string. Every path
            // is app-owned, and single quotes are escaped rather than interpolated.
            let quote = |v: &str| format!("'{}'", v.replace('\'', "'\"'\"'"));
            let command = format!(
                "/usr/bin/python3 {} --state {} serve",
                quote(&script.to_string_lossy()),
                quote(&state.to_string_lossy())
            );
            let mut started = Command::new(client)
                .args([
                    "run",
                    "--control-plane.tunnel-id",
                    id,
                    "--control-plane.api-key",
                ])
                .arg(format!("file:{}", state.join("runtime.key").display()))
                .args([
                    "--mcp.command",
                    &command,
                    "--health.listen-addr",
                    "127.0.0.1:0",
                    "--health.url-file",
                ])
                .arg(state.join("health.url"))
                .args([
                    "--log.level",
                    "warn",
                    "--log.format",
                    "json",
                    "--log.file",
                    "",
                    "--log.http-raw-unsafe=false",
                ])
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::piped())
                .current_dir(&state)
                .spawn()
                .map_err(|_| "The verified tunnel client could not start.")?;
            let mut diagnostics = started
                .stderr
                .take()
                .ok_or("Client diagnostics unavailable.")?;
            std::thread::sleep(Duration::from_millis(500));
            if let Some(exit) = started
                .try_wait()
                .map_err(|_| "Client startup check failed.")?
            {
                let mut raw = String::new();
                let _ = diagnostics.by_ref().take(8192).read_to_string(&mut raw);
                let lower = raw.to_ascii_lowercase();
                let categories: Vec<&str> = [
                    "permission",
                    "directory",
                    "key",
                    "file",
                    "flag",
                    "stdio",
                    "exec",
                    "bind",
                    "address",
                    "home",
                    "config",
                    "log",
                    "certificate",
                    "workspace",
                    "tunnel",
                    "resource",
                    "env",
                    "path",
                    "syntax",
                    "quote",
                ]
                .into_iter()
                .filter(|word| lower.contains(word))
                .collect();
                return Err(format!("The client exited at startup (code {}; categories: {}). Private details were suppressed.", exit.code().unwrap_or(-1), categories.join(", ")));
            }
            // Drain vendor output without retaining identifiers, URLs or payloads.
            std::thread::spawn(move || {
                let _ = std::io::copy(&mut diagnostics, &mut std::io::sink());
            });
            *tunnel = Some(started);
            Ok(())
        }
    }

    pub fn configure(&self, app: &tauri::AppHandle) -> Result<(), String> {
        require_private()?;
        setup_operation(app, "configure")?;
        *self.bridge.lock().unwrap() = None;
        self.connect(app)
    }

    pub fn disconnect(&self, app: &tauri::AppHandle) -> Result<(), String> {
        require_private()?;
        let mut tunnel = self.tunnel.lock().unwrap();
        setup_operation(app, "pause")?;
        if let Some(mut child) = tunnel.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        drop(tunnel);
        *self.bridge.lock().unwrap() = None;
        let _ = self.request(app, serde_json::json!({"operation":"snapshot"}));
        Ok(())
    }

    pub fn forget(&self, app: &tauri::AppHandle) -> Result<(), String> {
        self.disconnect(app)?;
        setup_operation(app, "forget")?;
        *self.bridge.lock().unwrap() = None;
        self.request(app, serde_json::json!({"operation":"snapshot"}))?;
        Ok(())
    }

    pub fn request(
        &self,
        app: &tauri::AppHandle,
        request: serde_json::Value,
    ) -> Result<Snapshot, String> {
        require_private()?;
        let mut bridge = self.bridge.lock().unwrap();
        if bridge.is_none() {
            *bridge = Some(Bridge::start(app)?);
        }
        let result = bridge.as_mut().unwrap().request(request);
        if result.is_err() {
            *bridge = None;
        }
        if let Ok(snapshot) = &result {
            *self.snapshot.lock().unwrap() = snapshot.clone();
        }
        result
    }
}
pub fn validate_message(text: &str) -> Result<(), String> {
    if text.trim().is_empty() || text.chars().count() > 1024 || text.contains('\0') {
        Err("Write a message between 1 and 1,024 characters.".into())
    } else {
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn transport_capability_starts_disconnected() {
        assert_eq!(
            enabled(),
            cfg!(target_os = "windows") || transport_enabled()
        );
        assert_eq!(require_private().is_ok(), transport_enabled());
        if cfg!(target_os = "windows") {
            let snapshot = Snapshot::default();
            assert!(enabled());
            assert!(transport_enabled());
            assert_eq!(snapshot.state, "unconfigured");
            assert!(!snapshot.connected);
            assert!(!snapshot.transport_running);
            assert!(snapshot.messages.is_empty());
        }
    }
    #[test]
    fn text_is_bounded_without_shell_interpretation() {
        assert!(validate_message("  ").is_err());
        assert!(validate_message(&"a".repeat(1025)).is_err());
        assert!(validate_message("hello\0").is_err());
        assert!(validate_message("synthetic text $(not-executed) `not-executed`").is_ok());
        assert!(validate_message(&"界".repeat(1024)).is_ok());
    }
}
