//! Keep Windows preferences outside host-package AppData virtualization.
use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
};

pub fn directory(home: &Path, config: &Path, windows: bool) -> PathBuf {
    if windows {
        home.join(".near-dot")
    } else {
        config.to_path_buf()
    }
}

pub fn migrate(legacy: &Path, destination: &Path) -> Result<(), String> {
    if legacy == destination {
        return Ok(());
    }
    fs::create_dir_all(destination).map_err(|_| "Settings directory could not be created.")?;
    let marker = destination.join("migration-complete");
    match fs::metadata(&marker) {
        Ok(_) => return Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(_) => return Err("Settings migration status could not be read.".into()),
    }
    for name in ["preferences.json", "avatar.png"] {
        let target = destination.join(name);
        match fs::metadata(&target) {
            Ok(_) => continue,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(_) => {
                return Err("Existing settings could not be checked; nothing was replaced.".into())
            }
        }
        let bytes = match fs::read(legacy.join(name)) {
            Ok(bytes) => bytes,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(_) => {
                return Err(
                    "Previous settings could not be read; the originals are preserved.".into(),
                )
            }
        };
        let mut staged = tempfile::NamedTempFile::new_in(destination)
            .map_err(|_| "Settings migration could not be staged.".to_string())?;
        staged
            .write_all(&bytes)
            .and_then(|_| staged.as_file().sync_all())
            .map_err(|_| "Settings migration could not be saved.".to_string())?;
        match staged.persist_noclobber(&target) {
            Ok(_) => {}
            Err(e) if e.error.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(_) => {
                return Err(
                    "Settings migration could not complete; the originals are preserved.".into(),
                )
            }
        }
    }
    match fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(marker)
    {
        Ok(file) => file
            .sync_all()
            .map_err(|_| "Settings migration status could not be saved.".to_string()),
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => Ok(()),
        Err(_) => Err("Settings migration status could not be saved.".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn windows_launch_context_does_not_select_a_different_store() {
        let home = Path::new("synthetic-user");
        let normal = Path::new("synthetic-roaming/near-dot");
        let packaged = Path::new("synthetic-package-cache/near-dot");
        assert_eq!(
            directory(home, normal, true),
            directory(home, packaged, true)
        );
        assert_eq!(directory(home, normal, false), normal);
    }
    #[test]
    fn migration_preserves_bytes_and_survives_relaunch_without_reimporting() {
        let temp = tempfile::tempdir().unwrap();
        let old = temp.path().join("synthetic-old");
        let new = temp.path().join("synthetic-new");
        fs::create_dir(&old).unwrap();
        fs::write(old.join("preferences.json"), br#"{"schema":9}"#).unwrap();
        fs::write(old.join("avatar.png"), b"synthetic-image").unwrap();
        migrate(&old, &new).unwrap();
        assert_eq!(
            fs::read(new.join("preferences.json")).unwrap(),
            br#"{"schema":9}"#
        );
        assert_eq!(
            fs::read(old.join("preferences.json")).unwrap(),
            br#"{"schema":9}"#
        );
        fs::write(new.join("preferences.json"), b"synthetic-new-choice").unwrap();
        fs::remove_file(new.join("avatar.png")).unwrap();
        migrate(&old, &new).unwrap();
        assert_eq!(
            fs::read(new.join("preferences.json")).unwrap(),
            b"synthetic-new-choice"
        );
        assert!(!new.join("avatar.png").exists());
    }
    #[test]
    fn interrupted_migration_keeps_new_settings_and_completes_missing_artwork() {
        let temp = tempfile::tempdir().unwrap();
        let old = temp.path().join("synthetic-old");
        let new = temp.path().join("synthetic-new");
        fs::create_dir(&old).unwrap();
        fs::create_dir(&new).unwrap();
        fs::write(old.join("preferences.json"), b"synthetic-old-choice").unwrap();
        fs::write(old.join("avatar.png"), b"synthetic-image").unwrap();
        fs::write(new.join("preferences.json"), b"synthetic-new-choice").unwrap();
        migrate(&old, &new).unwrap();
        assert_eq!(
            fs::read(new.join("preferences.json")).unwrap(),
            b"synthetic-new-choice"
        );
        assert_eq!(
            fs::read(new.join("avatar.png")).unwrap(),
            b"synthetic-image"
        );
    }
    #[test]
    fn unreadable_legacy_entry_does_not_certify_migration_or_reset_it() {
        let temp = tempfile::tempdir().unwrap();
        let old = temp.path().join("synthetic-old");
        let new = temp.path().join("synthetic-new");
        fs::create_dir_all(old.join("preferences.json")).unwrap();
        assert!(migrate(&old, &new).is_err());
        assert!(!new.join("migration-complete").exists());
        assert!(!new.join("preferences.json").exists());
        assert!(old.join("preferences.json").is_dir());
    }
}
