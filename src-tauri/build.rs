fn main() {
    tauri_build::build();
    // Tauri embeds its Windows manifest in app binaries, not Cargo examples.
    // The native updater drill also needs Common Controls v6 to load dialogs.
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        println!("cargo:rustc-link-arg-examples=/MANIFEST:EMBED");
        let manifest = std::path::Path::new(&std::env::var("CARGO_MANIFEST_DIR").unwrap())
            .join("examples/update-drill.manifest");
        println!("cargo:rerun-if-changed={}", manifest.display());
        println!(
            "cargo:rustc-link-arg-examples=/MANIFESTINPUT:{}",
            manifest.display()
        );
    }
}
