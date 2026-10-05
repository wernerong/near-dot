fn main() {
    tauri_build::build();
    // Tauri embeds its Windows manifest in app binaries, not Cargo test harnesses.
    // Mock-runtime tests and the updater drill also load Common Controls v6.
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        println!("cargo:rustc-link-arg=/MANIFEST:EMBED");
        let manifest = std::path::Path::new(&std::env::var("CARGO_MANIFEST_DIR").unwrap())
            .join("examples/update-drill.manifest");
        println!("cargo:rerun-if-changed={}", manifest.display());
        println!(
            "cargo:rustc-link-arg=/MANIFESTINPUT:{}",
            manifest.display()
        );
    }
}
