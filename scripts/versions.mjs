import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const semver =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)*))?$/;
export function versions(root = ".") {
  const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
  const pkg = JSON.parse(read("package.json"));
  const lock = JSON.parse(read("package-lock.json"));
  const cargoLock = read("src-tauri/Cargo.lock").match(
    /\[\[package\]\]\nname = "near-dot"\nversion = "([^"]+)"/,
  );
  return {
    package: pkg.version,
    npmLock: lock.version,
    npmRoot: lock.packages?.[""]?.version,
    tauri: JSON.parse(read("src-tauri/tauri.conf.json")).version,
    cargo: read("src-tauri/Cargo.toml").match(/^version\s*=\s*"([^"]+)"/m)?.[1],
    cargoLock: cargoLock?.[1],
  };
}
export function checkVersions(root = ".") {
  const all = versions(root);
  if (
    !semver.test(all.package) ||
    Object.values(all).some((v) => v !== all.package)
  )
    throw new Error(
      "Package, Tauri, Cargo and lockfile versions must all match.",
    );
  return all.package;
}
function setVersion(version) {
  if (!semver.test(version))
    throw new Error("Use a semantic version, e.g. 0.3.0-preview.1.");
  checkVersions();
  for (const file of [
    "package.json",
    "package-lock.json",
    "src-tauri/tauri.conf.json",
  ]) {
    const data = JSON.parse(fs.readFileSync(file, "utf8"));
    data.version = version;
    if (file === "package-lock.json") data.packages[""].version = version;
    fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n");
  }
  const cargo = "src-tauri/Cargo.toml";
  fs.writeFileSync(
    cargo,
    fs
      .readFileSync(cargo, "utf8")
      .replace(/^version\s*=\s*"[^"]+"/m, `version = "${version}"`),
  );
  const lock = "src-tauri/Cargo.lock";
  fs.writeFileSync(
    lock,
    fs
      .readFileSync(lock, "utf8")
      .replace(
        /(\[\[package\]\]\nname = "near-dot"\nversion = ")[^"]+"/,
        `$1${version}"`,
      ),
  );
}
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  if (process.argv[2] === "--set") setVersion(process.argv[3] || "");
  console.log(
    `Near Dot v${checkVersions()} — all build and lockfile versions match.`,
  );
}
