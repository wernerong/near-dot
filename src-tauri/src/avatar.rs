use base64::{engine::general_purpose::STANDARD, Engine};
use serde::{Deserialize, Serialize};
use std::{
    fs,
    io::{Cursor, Read, Write},
    path::Path,
};

const MAX_FILE: usize = 4 * 1024 * 1024;
const MAX_SIDE: u32 = 1024;
const MAX_PIXELS: usize = 4 * 1024 * 1024;
const MAX_PET_FILE: usize = 20 * 1024 * 1024;
const PET_WIDTH: u32 = 1536;
const PET_HEIGHTS: [u32; 2] = [1872, 2288];
const CELL_WIDTH: u32 = 192;
const CELL_HEIGHT: u32 = 208;

#[derive(Clone, Copy, Default, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    #[default]
    Image,
    Pet,
}
impl Kind {
    fn file_limit(self) -> usize {
        match self {
            Self::Image => MAX_FILE,
            Self::Pet => MAX_PET_FILE,
        }
    }
}

#[derive(Clone, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct View {
    pub data_url: Option<String>,
    pub warning: Option<String>,
}

fn read_bounded(path: &Path, kind: Kind) -> Result<Vec<u8>, String> {
    let file = fs::File::open(path).map_err(|_| "Image could not be opened.")?;
    if !file
        .metadata()
        .map_err(|_| "Image could not be checked.")?
        .is_file()
    {
        return Err("Choose a regular PNG image file.".into());
    }
    let mut bytes = Vec::new();
    file.take((kind.file_limit() + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|_| "Image could not be read.")?;
    if bytes.len() > kind.file_limit() {
        return Err("PNG file exceeds the size limit for this import option.".into());
    }
    Ok(bytes)
}

// Decode and re-encode pixels only. No text, EXIF, ICC profile, path or URL reaches the UI.
fn normalize(bytes: &[u8]) -> Result<Vec<u8>, String> {
    normalize_kind(bytes, Kind::Image)
}

// Pet import is an explicit local operation: take the original first idle cell,
// never redraw artwork, infer dot activity or access an account.
fn normalize_kind(bytes: &[u8], kind: Kind) -> Result<Vec<u8>, String> {
    if bytes.len() > kind.file_limit() || !bytes.starts_with(b"\x89PNG\r\n\x1a\n") {
        return Err("Choose a valid PNG file within the selected size limit.".into());
    }
    let mut decoder = png::Decoder::new(Cursor::new(bytes));
    decoder.set_limits(png::Limits {
        bytes: MAX_PET_FILE,
    });
    decoder.set_ignore_text_chunk(true);
    decoder.set_ignore_iccp_chunk(true);
    decoder.set_transformations(png::Transformations::EXPAND | png::Transformations::STRIP_16);
    let mut reader = decoder
        .read_info()
        .map_err(|_| "PNG image could not be decoded.")?;
    let info = reader.info();
    match kind {
        Kind::Image => {
            if info.width == 0
                || info.height == 0
                || info.width > MAX_SIDE
                || info.height > MAX_SIDE
            {
                return Err("Choose an image up to 1024 by 1024 pixels.".into());
            }
        }
        Kind::Pet => {
            if info.width != PET_WIDTH || !PET_HEIGHTS.contains(&info.height) {
                return Err(
                    "Choose a PNG pet sheet sized 1536 × 1872 or 1536 × 2288 pixels.".into(),
                );
            }
        }
    }
    if info.animation_control.is_some() {
        return Err("Choose a still PNG image; animated files are unsupported.".into());
    }
    let size = reader
        .output_buffer_size()
        .filter(|s| {
            *s <= match kind {
                Kind::Image => MAX_PIXELS,
                Kind::Pet => MAX_PET_FILE,
            }
        })
        .ok_or("Image has too many pixels.")?;
    let mut pixels = vec![0; size];
    let output = reader
        .next_frame(&mut pixels)
        .map_err(|_| "PNG pixels could not be decoded.")?;
    let (width, height, encoded_pixels) = match kind {
        Kind::Image => (
            output.width,
            output.height,
            pixels[..output.buffer_size()].to_vec(),
        ),
        Kind::Pet => {
            let samples = output.color_type.samples();
            let stride = output.width as usize * samples;
            let row_size = CELL_WIDTH as usize * samples;
            let mut cell = Vec::with_capacity(row_size * CELL_HEIGHT as usize);
            for row in 0..CELL_HEIGHT as usize {
                cell.extend_from_slice(&pixels[row * stride..row * stride + row_size]);
            }
            (CELL_WIDTH, CELL_HEIGHT, cell)
        }
    };
    let mut normalized = Vec::new();
    {
        let mut encoder = png::Encoder::new(&mut normalized, width, height);
        encoder.set_color(output.color_type);
        encoder.set_depth(png::BitDepth::Eight);
        let mut writer = encoder
            .write_header()
            .map_err(|_| "Image could not be prepared.")?;
        writer
            .write_image_data(&encoded_pixels)
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
    match read_bounded(path, Kind::Image).and_then(|bytes| normalize(&bytes)) {
        Ok(bytes) => view(&bytes),
        Err(_) => View { data_url: None, warning: Some("Local image is unreadable; the original file is preserved. Choose another image or restore the default.".into()) },
    }
}

pub fn import(source: &Path, destination: &Path, kind: Kind) -> Result<View, String> {
    let normalized = normalize_kind(&read_bounded(source, kind)?, kind)?;
    let dir = destination
        .parent()
        .ok_or("Local image directory is unavailable.")?;
    fs::create_dir_all(dir).map_err(|_| "Local image directory could not be created.")?;
    let mut file =
        tempfile::NamedTempFile::new_in(dir).map_err(|_| "Image could not be staged.")?;
    file.write_all(&normalized)
        .and_then(|_| file.as_file().sync_all())
        .map_err(|_| "Image could not be saved.")?;
    preserve(destination)?;
    file.persist(destination)
        .map_err(|_| "Image could not be committed.")?;
    Ok(view(&normalized))
}

fn preserve(path: &Path) -> Result<(), String> {
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
    }
    Ok(())
}

pub fn reset(path: &Path) -> Result<View, String> {
    preserve(path)?;
    if path.exists() {
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
        let imported = import(&source, &destination, Kind::Image).unwrap();
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
    fn pet_import_extracts_original_idle_cell_for_both_layouts() {
        for height in PET_HEIGHTS {
            let mut original = vec![0; (PET_WIDTH * height * 4) as usize];
            let mut expected = Vec::new();
            for y in 0..CELL_HEIGHT {
                for x in 0..CELL_WIDTH {
                    let pixel = [x as u8, y as u8, 37, if x % 2 == 0 { 255 } else { 0 }];
                    let offset = ((y * PET_WIDTH + x) * 4) as usize;
                    original[offset..offset + 4].copy_from_slice(&pixel);
                    expected.extend_from_slice(&pixel);
                }
            }
            let mut sheet = Vec::new();
            {
                let mut encoder = png::Encoder::new(&mut sheet, PET_WIDTH, height);
                encoder.set_color(png::ColorType::Rgba);
                encoder
                    .add_text_chunk("Comment".into(), "synthetic-metadata".into())
                    .unwrap();
                encoder
                    .write_header()
                    .unwrap()
                    .write_image_data(&original)
                    .unwrap();
            }
            let normalized = normalize_kind(&sheet, Kind::Pet).unwrap();
            let mut reader = png::Decoder::new(Cursor::new(&normalized))
                .read_info()
                .unwrap();
            assert_eq!(
                (reader.info().width, reader.info().height),
                (CELL_WIDTH, CELL_HEIGHT)
            );
            assert!(reader.info().uncompressed_latin1_text.is_empty());
            let mut pixels = vec![0; reader.output_buffer_size().unwrap()];
            reader.next_frame(&mut pixels).unwrap();
            assert_eq!(pixels, expected);
            let dir = tempfile::tempdir().unwrap();
            let source = dir.path().join("synthetic-pet.png");
            let destination = dir.path().join("avatar.png");
            fs::write(&source, &sheet).unwrap();
            let previous = fixture(1, 1, false);
            fs::write(&destination, &previous).unwrap();
            let imported = import(&source, &destination, Kind::Pet).unwrap();
            assert_eq!(imported.data_url, load(&destination).data_url);
            let backup = fs::read_dir(dir.path())
                .unwrap()
                .filter_map(Result::ok)
                .find(|entry| {
                    entry
                        .file_name()
                        .to_string_lossy()
                        .starts_with("avatar-preserved-")
                })
                .unwrap();
            assert_eq!(fs::read(backup.path()).unwrap(), previous);
        }
    }

    #[test]
    fn rejected_pet_sheet_does_not_replace_existing_avatar() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("synthetic-pet.png");
        let destination = dir.path().join("avatar.png");
        let original = fixture(2, 2, false);
        fs::write(&destination, &original).unwrap();
        for invalid in [
            fixture(1536, 2080, false),
            fixture(2, 2, false),
            b"not a PNG".to_vec(),
            vec![0; MAX_PET_FILE + 1],
        ] {
            fs::write(&source, invalid).unwrap();
            assert!(import(&source, &destination, Kind::Pet).is_err());
            assert_eq!(fs::read(&destination).unwrap(), original);
        }
        assert_eq!(fs::read_dir(dir.path()).unwrap().count(), 2);
    }

    #[test]
    fn invalid_import_preserves_existing_image_and_corruption_is_not_reset() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("synthetic-source.png");
        let destination = dir.path().join("avatar.png");
        let original = fixture(1, 1, false);
        fs::write(&destination, &original).unwrap();
        fs::write(&source, "<svg>synthetic</svg>").unwrap();
        assert!(import(&source, &destination, Kind::Image).is_err());
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
