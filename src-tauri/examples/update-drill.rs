//! Release-runner harness for the real Tauri updater. Never bundled in the app.
use std::{path::PathBuf, time::Duration};
use tauri_plugin_updater::UpdaterExt;

fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert_eq!(
        args.len(),
        5,
        "endpoint, test CA, installed executable, public key required"
    );
    let executable = PathBuf::from(&args[3]).canonicalize().unwrap();
    assert!(executable.starts_with(std::env::temp_dir().canonicalize().unwrap()));
    let endpoint = url::Url::parse(&args[1]).unwrap();
    assert_eq!(endpoint.scheme(), "https");
    assert_eq!(endpoint.host_str(), Some("127.0.0.1"));
    let ca = reqwest::Certificate::from_pem(&std::fs::read(&args[2]).unwrap()).unwrap();
    let key = std::fs::read_to_string(&args[4]).unwrap();
    let mut context = tauri::generate_context!();
    context.config_mut().app.windows.clear();
    context.config_mut().plugins.0.insert(
        "updater".into(),
        serde_json::json!({ "pubkey": key.trim(), "requireSignedVersion": true, "windows": { "installMode": "quiet" } }),
    );
    context.package_info_mut().version = semver::Version::parse("0.3.0-preview.1").unwrap();
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(move |app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let result = async {
                    let builder = handle
                        .updater_builder()
                        .executable_path(&executable)
                        .target(format!(
                            "{}-{}",
                            if cfg!(windows) { "windows" } else { "darwin" },
                            std::env::consts::ARCH
                        ))
                        .timeout(Duration::from_secs(90))
                        .endpoints(vec![endpoint])?
                        // Trust only this ephemeral test CA; certificate/hostname validation remains on.
                        .configure_client(move |client| client.add_root_certificate(ca.clone()));
                    #[cfg(windows)]
                    let builder = builder
                        .installer_arg(format!("/D={}", executable.parent().unwrap().display()))
                        .restart_after_install(false);
                    let updater = builder.build()?;
                    let update = updater.check().await?.expect("Expected a newer release");
                    let bytes = update.download(|_, _| {}, || {}).await?;
                    update.install(bytes)?;
                    Ok::<(), tauri_plugin_updater::Error>(())
                }
                .await;
                match result {
                    Ok(()) => handle.exit(0),
                    Err(error) => {
                        eprintln!("Isolated updater drill failed: {error:?}");
                        handle.exit(1);
                    }
                }
            });
            Ok(())
        })
        .run(context)
        .expect("Updater test runner failed");
}
