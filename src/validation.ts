export function destinationError(raw: string): string | null {
  if (raw.length > 2048 || /[\s\\]/u.test(raw))
    return "Use a plain HTTPS link without spaces.";
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return "Enter a valid HTTPS link.";
  }
  if (u.protocol !== "https:" || u.hostname !== "chatgpt.com" || u.port)
    return "Only HTTPS links on chatgpt.com are allowed.";
  if (u.username || u.password || u.search || u.hash)
    return "Remove credentials, query parameters and fragments.";
  if (
    /\.(exe|msi|bat|cmd|ps1|sh|scr|com|app|dmg|pkg|jar|vbs)\/?$/i.test(
      u.pathname,
    )
  )
    return "Executable or installer links are not conversation destinations.";
  if (
    u.pathname === "/" ||
    u.pathname.includes("%") ||
    u.pathname
      .toLowerCase()
      .split("/")
      .some((p) => ["share", "auth", "api", "backend-api", "login"].includes(p))
  )
    return "Use your private conversation link, not a share, login or API link.";
  return null;
}
export function shouldDrag(origin: [number, number], point: [number, number]) {
  return Math.hypot(point[0] - origin[0], point[1] - origin[1]) >= 6;
}
