use base64::{engine::general_purpose::STANDARD, Engine};
use minisign_verify::{PublicKey, Signature};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, time::Duration};
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_updater::{Update, UpdaterExt};
use url::Url;

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Artifact {
    pub url: String,
    pub signature: String,
    pub sha256: String,
}
#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Feed {
    pub version: String,
    pub notes: String,
    pub channel: String,
    pub paused: bool,
    pub rollout: u8,
    pub platforms: BTreeMap<String, Artifact>,
}
#[derive(Clone, Serialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct Status {
    pub state: String,
    pub version: String,
    pub notes: String,
    pub progress: Option<u8>,
}
pub struct Pending {
    pub update: Update,
    pub sha256: String,
    pub channel: String,
}

fn decoded(s: &str) -> Result<String, String> {
    String::from_utf8(
        STANDARD
            .decode(s.trim())
            .map_err(|_| "Update signature encoding is invalid.")?,
    )
    .map_err(|_| "Update signature encoding is invalid.".into())
}
pub fn verify(bytes: &[u8], signature: &str, key: &str) -> Result<(), String> {
    let key_text = decoded(key)?;
    let pk = PublicKey::decode(&key_text).map_err(|_| "Update verification key is invalid.")?;
    let sig =
        Signature::decode(&decoded(signature)?).map_err(|_| "Update signature is invalid.")?;
    pk.verify(bytes, &sig, false)
        .map_err(|_| "Update signature verification failed; nothing was installed.".into())
}
pub fn artifact<'a>(
    feed: &'a Feed,
    channel: &str,
    current: &str,
    target: &str,
    cohort: u8,
    repo: &str,
) -> Result<Option<&'a Artifact>, String> {
    if feed.channel != channel || feed.rollout > 100 {
        return Err("Update channel metadata is invalid.".into());
    }
    let v = semver::Version::parse(&feed.version).map_err(|_| "Update version is invalid.")?;
    let c = semver::Version::parse(current).map_err(|_| "Installed version is invalid.")?;
    if v <= c {
        return Ok(None);
    }
    if channel == "stable" && !v.pre.is_empty() {
        return Err("Preview packages cannot enter the stable channel.".into());
    }
    if feed.paused || cohort >= feed.rollout {
        return Ok(None);
    }
    let a = feed
        .platforms
        .get(target)
        .ok_or("No update for this platform and architecture.")?;
    let u = Url::parse(&a.url).map_err(|_| "Update package address is invalid.")?;
    let prefix = format!("/{repo}/releases/download/v{}/", feed.version);
    if u.scheme() != "https"
        || u.host_str() != Some("github.com")
        || !u.username().is_empty()
        || u.password().is_some()
        || u.query().is_some()
        || u.fragment().is_some()
        || u.port().is_some()
        || !u.path().starts_with(&prefix)
        || !u.path().contains(target)
        || a.signature.is_empty()
        || a.sha256.len() != 64
        || !a.sha256.bytes().all(|b| b.is_ascii_hexdigit())
    {
        return Err("Update package does not match the trusted release or architecture.".into());
    }
    Ok(Some(a))
}
fn target() -> Result<String, String> {
    let os = match std::env::consts::OS {
        "windows" => "windows",
        "macos" => "darwin",
        _ => return Err("Updates are supported on Windows and Mac only.".into()),
    };
    Ok(format!("{os}-{}", std::env::consts::ARCH))
}
fn policy() -> reqwest::redirect::Policy {
    reqwest::redirect::Policy::custom(|attempt| {
        if attempt.previous().len() >= 5 {
            return attempt.stop();
        }
        if attempt.url().scheme() == "https"
            && matches!(
                attempt.url().host_str(),
                Some(
                    "github.com"
                        | "raw.githubusercontent.com"
                        | "release-assets.githubusercontent.com"
                        | "objects.githubusercontent.com"
                )
            )
        {
            attempt.follow()
        } else {
            attempt.stop()
        }
    })
}
fn key_repo(app: &AppHandle) -> Result<(String, String), String> {
    let key = app
        .config()
        .plugins
        .0
        .get("updater")
        .and_then(|p| p.get("pubkey"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let repo = option_env!("NEAR_DOT_UPDATE_REPO")
        .unwrap_or("")
        .to_string();
    if key.is_empty() || repo.is_empty() {
        return Err("Updates are not configured in this development build. Release signing and a reviewed public repository are required.".into());
    }
    Ok((key, repo))
}
pub fn configured(app: &AppHandle) -> bool {
    key_repo(app).is_ok()
}
async fn fetch(client: &reqwest::Client, url: &str, limit: usize) -> Result<Vec<u8>, String> {
    let mut r = client
        .get(url)
        .send()
        .await
        .map_err(|_| "Update service is unreachable. Try again later.")?
        .error_for_status()
        .map_err(|_| "Update feed is unavailable.")?;
    let mut bytes = Vec::new();
    while let Some(c) = r
        .chunk()
        .await
        .map_err(|_| "Update feed was interrupted.")?
    {
        if bytes.len() + c.len() > limit {
            return Err("Update metadata is too large.".into());
        }
        bytes.extend_from_slice(&c);
    }
    Ok(bytes)
}
pub async fn check(app: &AppHandle, manual: bool) -> Result<Status, String> {
    let state = app.state::<super::AppState>();
    let _guard = state.update_lock.lock().await;
    *state.pending.lock().unwrap() = None;
    let p = state.preferences.lock().unwrap().clone();
    let (key, repo) = key_repo(app)?;
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(20))
        .redirect(policy())
        .build()
        .map_err(|_| "Update client could not start.")?;
    let url = format!(
        "https://raw.githubusercontent.com/{repo}/main/channels/{}.json",
        p.channel
    );
    let bytes = fetch(&client, &url, 64 * 1024).await?;
    let signature = fetch(&client, &format!("{url}.sig"), 4096).await?;
    verify(
        &bytes,
        std::str::from_utf8(&signature).map_err(|_| "Invalid feed signature.")?,
        &key,
    )?;
    let feed: Feed = serde_json::from_slice(&bytes).map_err(|_| "Update metadata is invalid.")?;
    let current = app.package_info().version.to_string();
    let target = target()?;
    let Some(a) = artifact(&feed, &p.channel, &current, &target, p.cohort, &repo)? else {
        return Ok(Status {
            state: "current".into(),
            notes: "No eligible update. Rollout may be paused or staged.".into(),
            ..Default::default()
        });
    };
    if !manual && p.skipped_version == feed.version {
        return Ok(Status {
            state: "skipped".into(),
            ..Default::default()
        });
    }
    // Tauri receives a verified feed URL. Bind its response to signed metadata again.
    let update = app
        .updater_builder()
        .pubkey(key)
        .target(target)
        .endpoints(vec![Url::parse(&url).unwrap()])
        .map_err(|_| "Update endpoint is invalid.")?
        .timeout(Duration::from_secs(120))
        .configure_client(|b| b.redirect(policy()))
        .build()
        .map_err(|_| "Update service could not initialize.")?
        .check()
        .await
        .map_err(|_| "Update check failed; no installation started.")?
        .ok_or("Update metadata changed. Check again.")?;
    if update.version != feed.version
        || update.download_url.as_str() != a.url
        || update.signature != a.signature
    {
        return Err(
            "Update metadata changed or was altered. Check again; nothing was installed.".into(),
        );
    }
    *state.pending.lock().unwrap() = Some(Pending {
        update,
        sha256: a.sha256.clone(),
        channel: p.channel,
    });
    Ok(Status {
        state: "available".into(),
        version: feed.version,
        notes: feed.notes,
        ..Default::default()
    })
}
pub async fn install(app: &AppHandle) -> Result<(), String> {
    let state = app.state::<super::AppState>();
    // Refresh signed rollout controls immediately before installation (pause wins).
    let status = check(app, true).await?;
    if status.state != "available" {
        return Err("Update is no longer eligible; no installation started.".into());
    }
    let _guard = state.update_lock.lock().await;
    let pending = state
        .pending
        .lock()
        .unwrap()
        .take()
        .ok_or("Check for an update first.")?;
    if state.preferences.lock().unwrap().channel != pending.channel {
        return Err("Channel changed; check again.".into());
    }
    let mut downloaded = 0u64;
    let bytes=pending.update.download(|chunk,total| {
        downloaded+=chunk as u64;
        let progress=total.filter(|n|*n>0).map(|n|((downloaded.saturating_mul(100)/n).min(100)) as u8);
        let _=app.emit_to("settings","update-status",Status{state:"downloading".into(),progress,..Default::default()});
    },||{}).await.map_err(|_|"Download or signature verification failed; nothing was installed. Check again to retry.")?;
    if format!("{:x}", Sha256::digest(&bytes)) != pending.sha256.to_lowercase() {
        return Err("Update checksum mismatch; nothing was installed.".into());
    }
    let _ = app.emit_to(
        "settings",
        "update-status",
        Status {
            state: "installing".into(),
            notes: "OS approval may appear. Keep this window open.".into(),
            ..Default::default()
        },
    );
    pending
        .update
        .install(bytes)
        .map_err(|_| "Installation failed. Use the signed recovery instructions.")?;
    state
        .restart_ready
        .store(true, std::sync::atomic::Ordering::Relaxed);
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    fn feed() -> Feed {
        Feed{version:"0.2.0".into(),notes:String::new(),channel:"stable".into(),paused:false,rollout:100,platforms:BTreeMap::from([("windows-x86_64".into(),Artifact{url:"https://github.com/example/near-dot/releases/download/v0.2.0/NearDot-windows-x86_64.exe".into(),signature:"fixture".into(),sha256:"a".repeat(64)})])}
    }
    #[test]
    fn upgrade_downgrade_platform_rollout_pause() {
        let mut f = feed();
        assert!(artifact(
            &f,
            "stable",
            "0.1.0",
            "windows-x86_64",
            50,
            "example/near-dot"
        )
        .unwrap()
        .is_some());
        assert!(artifact(
            &f,
            "stable",
            "0.3.0",
            "windows-x86_64",
            50,
            "example/near-dot"
        )
        .unwrap()
        .is_none());
        assert!(artifact(
            &f,
            "stable",
            "0.1.0",
            "darwin-aarch64",
            50,
            "example/near-dot"
        )
        .is_err());
        f.rollout = 10;
        assert!(artifact(
            &f,
            "stable",
            "0.1.0",
            "windows-x86_64",
            50,
            "example/near-dot"
        )
        .unwrap()
        .is_none());
        f.paused = true;
        assert!(artifact(
            &f,
            "stable",
            "0.1.0",
            "windows-x86_64",
            0,
            "example/near-dot"
        )
        .unwrap()
        .is_none());
    }
    #[test]
    fn rejects_package_and_channel_substitution() {
        let mut f = feed();
        assert!(artifact(
            &f,
            "preview",
            "0.1.0",
            "windows-x86_64",
            0,
            "example/near-dot"
        )
        .is_err());
        f.platforms.get_mut("windows-x86_64").unwrap().url = "http://evil.test/update.exe".into();
        assert!(artifact(
            &f,
            "stable",
            "0.1.0",
            "windows-x86_64",
            0,
            "example/near-dot"
        )
        .is_err());
    }
    #[test]
    fn real_signature_accepts_original_rejects_tampering_and_wrong_key() {
        let kp = minisign::KeyPair::generate_unencrypted_keypair().unwrap();
        let bytes = b"synthetic update payload";
        let sig = minisign::sign(Some(&kp.pk), &kp.sk, &bytes[..], Some("test"), None).unwrap();
        let key = STANDARD.encode(kp.pk.to_box().unwrap().to_string());
        let signature = STANDARD.encode(sig.to_string());
        assert!(verify(bytes, &signature, &key).is_ok());
        assert!(verify(b"tampered update payload", &signature, &key).is_err());
        let wrong = minisign::KeyPair::generate_unencrypted_keypair().unwrap();
        assert!(verify(
            bytes,
            &signature,
            &STANDARD.encode(wrong.pk.to_box().unwrap().to_string())
        )
        .is_err());
    }
}
