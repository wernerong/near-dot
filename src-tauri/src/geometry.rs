#[derive(Clone, Copy, Debug)]
pub struct Rect {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}
pub fn recover(position: (i32, i32), size: (u32, u32), areas: &[Rect]) -> (i32, i32) {
    let Some(area) = areas.iter().min_by_key(|a| {
        let dx = (position.0 as i64 - a.x as i64).clamp(-1_000_000, 1_000_000);
        let dy = (position.1 as i64 - a.y as i64).clamp(-1_000_000, 1_000_000);
        dx * dx + dy * dy
    }) else {
        return position;
    };
    if areas.iter().any(|a| {
        position.0 >= a.x
            && position.1 >= a.y
            && position.0 as i64 + size.0 as i64 <= a.x as i64 + a.width as i64
            && position.1 as i64 + size.1 as i64 <= a.y as i64 + a.height as i64
    }) {
        return position;
    }
    (
        position.0.clamp(
            area.x,
            area.x
                .saturating_add(area.width.saturating_sub(size.0) as i32),
        ),
        position.1.clamp(
            area.y,
            area.y
                .saturating_add(area.height.saturating_sub(size.1) as i32),
        ),
    )
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn disconnected_display_and_taskbar_recovery() {
        let areas = [Rect {
            x: 0,
            y: 0,
            width: 1920,
            height: 1040,
        }];
        assert_eq!(recover((2300, 1200), (200, 200), &areas), (1720, 840));
        assert_eq!(recover((-500, 20), (200, 200), &areas), (0, 20));
        assert_eq!(recover((40, 40), (200, 200), &areas), (40, 40));
    }
    #[test]
    fn negative_monitor_and_scaled_window() {
        let areas = [
            Rect {
                x: -1920,
                y: 0,
                width: 1920,
                height: 1040,
            },
            Rect {
                x: 0,
                y: 0,
                width: 2560,
                height: 1400,
            },
        ];
        assert_eq!(recover((-1800, 200), (312, 352), &areas), (-1800, 200));
        assert_eq!(recover((2500, 1380), (312, 352), &areas), (2248, 1048));
    }
}
