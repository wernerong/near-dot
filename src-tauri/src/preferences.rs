use serde::{Deserialize, Serialize};
use std::{fs, io::Write, path::Path};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(default, rename_all = "camelCase", deny_unknown_fields)]
pub struct Preferences {
    pub schema: u32,
    pub destination: String,
    pub verified: bool,
    pub setup_completed: bool,
    pub shortcut: String,
    pub size: u32,
    pub opacity: f64,
    pub always_on_top: bool,
    pub paused: bool,
    pub reply_preview: bool,
    pub startup: bool,
    pub auto_check: bool,
    pub unattended_next_launch: bool,
    pub channel: String,
    pub skipped_version: String,
    pub position: Option<(i32, i32)>,
    pub cohort: u8,
}
impl Default for Preferences {
    fn default() -> Self {
        Self {
            schema: 1,
            destination: String::new(),
            verified: false,
            setup_completed: false,
            shortcut: "CommandOrControl+Shift+D".into(),
            size: 156,
            opacity: 1.,
            always_on_top: true,
            paused: false,
            reply_preview: false,
            startup: false,
            auto_check: true,
            unattended_next_launch: false,
            channel: if env!("CARGO_PKG_VERSION").contains('-') {
                "preview"
            } else {
                "stable"
            }
            .into(),
            skipped_version: String::new(),
            position: None,
            cohort: 0,
        }
    }
}
impl Preferences {
    pub fn needs_setup(&self) -> bool {
        !self.setup_completed
    }
    pub fn validate(&self) -> Result<(), String> {
        if self.schema != 1 {
            return Err("Settings schema is unsupported; use a newer recovery release.".into());
        }
        if !self.destination.is_empty() {
            super::destination::validate(&self.destination)?;
        }
        if self.destination.is_empty() && self.verified {
            return Err("Test a destination before confirming it.".into());
        }
        if self.setup_completed && (!self.verified || self.destination.is_empty()) {
            return Err("Test and confirm your destination before finishing setup.".into());
        }
        if !(120..=240).contains(&self.size)
            || !self.opacity.is_finite()
            || !(0.35..=1.).contains(&self.opacity)
            || self.cohort > 99
        {
            return Err("Size or opacity is outside the supported range.".into());
        }
        if !["stable", "preview"].contains(&self.channel.as_str()) || self.shortcut.len() > 80 {
            return Err("Invalid update channel or shortcut.".into());
        }
        Ok(())
    }
}
pub fn load(path: &Path) -> Result<Preferences, String> {
    if !path.exists() {
        return Ok(Preferences::default());
    }
    let raw = fs::read(path).map_err(|_| "Settings could not be read.".to_string())?;
    let fields: serde_json::Value = serde_json::from_slice(&raw)
        .map_err(|_| "Settings are invalid; the original file has been preserved.".to_string())?;
    let mut p: Preferences = serde_json::from_value(fields.clone())
        .map_err(|_| "Settings are invalid; the original file has been preserved.".to_string())?;
    // A verified destination in the old schema already completed its original setup.
    if fields.get("setupCompleted").is_none() && p.verified {
        p.setup_completed = true;
    }
    p.validate()?;
    Ok(p)
}
pub fn save(path: &Path, p: &Preferences) -> Result<(), String> {
    p.validate()?;
    let dir = path.parent().ok_or("Settings directory is unavailable.")?;
    fs::create_dir_all(dir).map_err(|_| "Settings directory could not be created.")?;
    let mut file =
        tempfile::NamedTempFile::new_in(dir).map_err(|_| "Settings could not be staged.")?;
    let bytes = serde_json::to_vec_pretty(p).map_err(|_| "Settings could not be encoded.")?;
    file.write_all(&bytes)
        .and_then(|_| file.as_file().sync_all())
        .map_err(|_| "Settings could not be saved.")?;
    file.persist(path)
        .map_err(|_| "Settings could not be committed.")?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn atomic_roundtrip_and_upgrade_defaults() {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("preferences.json");
        let p = Preferences {
            paused: true,
            size: 180,
            ..Default::default()
        };
        save(&path, &p).unwrap();
        assert_eq!(load(&path).unwrap(), p);
        save(&path, &Preferences::default()).unwrap();
        assert_eq!(load(&path).unwrap(), Preferences::default());
        fs::write(&path, r#"{"schema":1,"paused":true}"#).unwrap();
        assert!(load(&path).unwrap().paused);
        assert!(load(&path).unwrap().always_on_top);
        fs::write(&path, r#"{"schema":1,"alwaysOnTop":false}"#).unwrap();
        assert!(!load(&path).unwrap().always_on_top);
    }
    #[test]
    fn preserves_corrupt_and_future_settings() {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("preferences.json");
        for raw in ["broken", r#"{"schema":9}"#] {
            fs::write(&path, raw).unwrap();
            assert!(load(&path).is_err());
            assert_eq!(fs::read_to_string(&path).unwrap(), raw);
        }
    }
    #[test]
    fn setup_survives_relaunch_and_legacy_upgrade() {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("preferences.json");
        assert!(load(&path).unwrap().needs_setup());
        let p = Preferences {
            destination: "https://chatgpt.com/c/synthetic-setup".into(),
            verified: true,
            setup_completed: true,
            ..Default::default()
        };
        let incomplete = Preferences {
            setup_completed: false,
            ..p.clone()
        };
        save(&path, &incomplete).unwrap();
        assert!(load(&path).unwrap().needs_setup());
        save(&path, &p).unwrap();
        assert!(!load(&path).unwrap().needs_setup());
        fs::write(&path, r#"{"schema":1,"destination":"https://chatgpt.com/c/synthetic-legacy","verified":true,"alwaysOnTop":false}"#).unwrap();
        let legacy = load(&path).unwrap();
        assert!(!legacy.needs_setup());
        assert!(!legacy.always_on_top);
        assert!(Preferences {
            setup_completed: true,
            ..Default::default()
        }
        .validate()
        .is_err());
    }
}
