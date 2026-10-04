use base64::{engine::general_purpose::STANDARD, Engine};
use serde::Serialize;
use std::{
    fs,
    io::{Cursor, Read, Write},
    path::Path,
};

const MAX_FILE: usize = 4 * 1024 * 1024;
const MAX_SIDE: u32 = 1024;
const MAX_PIXELS: usize = 4 * 1024 * 1024;

#[derive(Clone, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct View {
    pub data_url: Option<String>,
    pub warning: Option<String>,
}

fn read_bounded(path: &Path) -> Result<Vec<u8>, String> {
    let file = fs::File::open(path).map_err(|_| "Image could not be opened.")?;
    if !file
        .metadata()
        .map_err(|_| "Image could not be checked.")?
        .is_file()
    {
        return Err("Choose a regular PNG image file.".into());
    }
    let mut bytes = Vec::new();
    file.take((MAX_FILE + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|_| "Image could not be read.")?;
    if bytes.len() > MAX_FILE {
        return Err("Choose a PNG image smaller than 4 MiB.".into());
    }
    Ok(bytes)
}

// Decode and re-encode pixels only. No text, EXIF, ICC profile, path or URL reaches the UI.
fn normalize(bytes: &[u8]) -> Result<Vec<u8>, String> {
    if bytes.len() > MAX_FILE || !bytes.starts_with(b"\x89PNG\r\n\x1a\n") {
        return Err("Choose a valid PNG image smaller than 4 MiB.".into());
    }
    let mut decoder = png::Decoder::new(Cursor::new(bytes));
    decoder.set_limits(png::Limits {
        bytes: 8 * 1024 * 1024,
    });
    decoder.set_ignore_text_chunk(true);
    decoder.set_ignore_iccp_chunk(true);
    decoder.set_transformations(png::Transformations::EXPAND | png::Transformations::STRIP_16);
    let mut reader = decoder
        .read_info()
        .map_err(|_| "PNG image could not be decoded.")?;
    let info = reader.info();
    if info.width == 0 || info.height == 0 || info.width > MAX_SIDE || info.height > MAX_SIDE {
        return Err("Choose an image up to 1024 by 1024 pixels.".into());
    }
    if info.animation_control.is_some() {
        return Err("Choose a still PNG image; animated files are unsupported.".into());
    }
    let size = reader
        .output_buffer_size()
        .filter(|s| *s <= MAX_PIXELS)
        .ok_or("Image has too many pixels.")?;
    let mut pixels = vec![0; size];
    let output = reader
        .next_frame(&mut pixels)
        .map_err(|_| "PNG pixels could not be decoded.")?;
    let mut normalized = Vec::new();
    {
        let mut encoder = png::Encoder::new(&mut normalized, output.width, output.height);
        encoder.set_color(output.color_type);
        encoder.set_depth(png::BitDepth::Eight);
        let mut writer = encoder
            .write_header()
            .map_err(|_| "Image could not be prepared.")?;
        writer
            .write_image_data(&pixels[..output.buffer_size()])
            .map_err(|_| "Image could not be prepared.")?;
    }
    if normalized.len() > MAX_FILE {
        return Err("Prepared image exceeds the local size limit.".into());
    }
    Ok(normalized)
}

fn view(bytes: &[u8]) -> View {
    View {
        data_url: Some(format!("data:image/png;base64,{}", STANDARD.encode(bytes))),
        warning: None,
    }
}

pub fn load(path: &Path) -> View {
    if !path.exists() {
        return View::default();
    }
    match read_bounded(path).and_then(|bytes| normalize(&bytes)) {
        Ok(bytes) => view(&bytes),
        Err(_) => View { data_url: None, warning: Some("Local image is unreadable; the original file is preserved. Choose another image or restore the default.".into()) },
    }
}

pub fn import(source: &Path, destination: &Path) -> Result<View, String> {
    let normalized = normalize(&read_bounded(source)?)?;
    let dir = destination
        .parent()
        .ok_or("Local image directory is unavailable.")?;
    fs::create_dir_all(dir).map_err(|_| "Local image directory could not be created.")?;
    let mut file =
        tempfile::NamedTempFile::new_in(dir).map_err(|_| "Image could not be staged.")?;
    file.write_all(&normalized)
        .and_then(|_| file.as_file().sync_all())
        .map_err(|_| "Image could not be saved.")?;
    file.persist(destination)
        .map_err(|_| "Image could not be committed.")?;
    Ok(view(&normalized))
}

pub fn reset(path: &Path) -> Result<View, String> {
    if path.exists() {
        let dir = path
            .parent()
            .ok_or("Local image directory is unavailable.")?;
        let mut backup = tempfile::Builder::new()
            .prefix("avatar-preserved-")
            .suffix(".png")
            .tempfile_in(dir)
            .map_err(|_| "Previous image could not be preserved.")?;
        let mut source =
            fs::File::open(path).map_err(|_| "Previous image could not be preserved.")?;
        std::io::copy(&mut source, &mut backup)
            .and_then(|_| backup.as_file().sync_all())
            .map_err(|_| "Previous image could not be preserved.")?;
        backup
            .keep()
            .map_err(|_| "Previous image could not be preserved.")?;
        fs::remove_file(path).map_err(|_| "Default image could not be restored.")?;
    }
    Ok(View::default())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture(width: u32, height: u32, text: bool) -> Vec<u8> {
        let mut bytes = Vec::new();
        {
            let mut encoder = png::Encoder::new(&mut bytes, width, height);
            encoder.set_color(png::ColorType::Rgba);
            encoder.set_depth(png::BitDepth::Eight);
            if text {
                encoder
                    .add_text_chunk("Comment".into(), "synthetic-private-metadata".into())
                    .unwrap();
            }
            let mut writer = encoder.write_header().unwrap();
            writer
                .write_image_data(&vec![127; (width * height * 4) as usize])
                .unwrap();
        }
        bytes
    }
    #[test]
    fn strips_metadata_preserves_pixels_and_survives_restart() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("synthetic-source.png");
        let destination = dir.path().join("local/avatar.png");
        fs::write(&source, fixture(2, 2, true)).unwrap();
        let imported = import(&source, &destination).unwrap();
        assert_eq!(imported.data_url, load(&destination).data_url);
        let stored = fs::read(&destination).unwrap();
        let mut reader = png::Decoder::new(Cursor::new(stored)).read_info().unwrap();
        assert!(reader.info().uncompressed_latin1_text.is_empty());
        let mut pixels = vec![0; reader.output_buffer_size().unwrap()];
        reader.next_frame(&mut pixels).unwrap();
        assert_eq!(pixels, vec![127; 16]);
        reset(&destination).unwrap();
        assert!(load(&destination).data_url.is_none());
        assert_eq!(
            fs::read_dir(destination.parent().unwrap()).unwrap().count(),
            1
        );
    }
    #[test]
    fn invalid_import_preserves_existing_image_and_corruption_is_not_reset() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("synthetic-source.png");
        let destination = dir.path().join("avatar.png");
        let original = fixture(1, 1, false);
        fs::write(&destination, &original).unwrap();
        fs::write(&source, "<svg>synthetic</svg>").unwrap();
        assert!(import(&source, &destination).is_err());
        assert_eq!(fs::read(&destination).unwrap(), original);
        fs::write(&destination, "broken").unwrap();
        assert!(load(&destination).warning.is_some());
        assert_eq!(fs::read(&destination).unwrap(), b"broken");
        assert!(normalize(&vec![0; MAX_FILE + 1]).is_err());
        assert!(normalize(&fixture(MAX_SIDE + 1, 1, false)).is_err());
        let mut animated = Vec::new();
        {
            let mut encoder = png::Encoder::new(&mut animated, 1, 1);
            encoder.set_animated(1, 0).unwrap();
            let mut writer = encoder.write_header().unwrap();
            writer.write_image_data(&[127]).unwrap();
        }
        assert!(normalize(&animated).is_err());
    }
}
