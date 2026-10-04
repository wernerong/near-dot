import { it, expect } from "vitest";
import {
  mkdtempSync,
  mkdirSync,
  copyFileSync,
  writeFileSync,
  existsSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

function fixture() {
  const dir = mkdtempSync(join(tmpdir(), "near-dot-release-test-"));
  mkdirSync(join(dir, "src-tauri"));
  copyFileSync(resolve("scripts/release-config.mjs"), join(dir, "config.mjs"));
  copyFileSync(resolve("scripts/versions.mjs"), join(dir, "versions.mjs"));
  writeFileSync(
    join(dir, "package-lock.json"),
    JSON.stringify({
      version: "0.1.0",
      packages: { "": { version: "0.1.0" } },
    }),
  );
  writeFileSync(
    join(dir, "src-tauri/Cargo.lock"),
    '[[package]]\nname = "near-dot"\nversion = "0.1.0"\n',
  );
  writeFileSync(
    join(dir, "package.json"),
    JSON.stringify({ version: "0.1.0" }),
  );
  writeFileSync(
    join(dir, "src-tauri/tauri.conf.json"),
    JSON.stringify({ version: "0.1.0" }),
  );
  writeFileSync(
    join(dir, "src-tauri/Cargo.toml"),
    '[package]\nversion = "0.1.0"\n',
  );
  return dir;
}
const publicBytes = Buffer.alloc(42);
publicBytes.write("Ed");
const syntheticPublic = Buffer.from(
  `untrusted comment: minisign public key synthetic\n${publicBytes.toString("base64")}\n`,
).toString("base64");
function run(dir: string, key: string) {
  return spawnSync(process.execPath, ["config.mjs"], {
    cwd: dir,
    encoding: "utf8",
    env: {
      NEAR_DOT_UPDATE_REPO: "example/near-dot",
      NEAR_DOT_UPDATER_PUBLIC_KEY: key,
    },
  });
}
it("release generator writes only a public verification key and pinned HTTPS feed", () => {
  const dir = fixture();
  try {
    expect(run(dir, syntheticPublic).status).toBe(0);
    const config = JSON.parse(
      readFileSync(join(dir, "release-config.json"), "utf8"),
    );
    expect(config.plugins.updater.pubkey).toBe(syntheticPublic);
    expect(config.plugins.updater.requireSignedVersion).toBe(true);
    expect(config.plugins.updater.endpoints).toEqual([
      "https://raw.githubusercontent.com/example/near-dot/main/channels/stable.json",
    ]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
it("release generator rejects secret-key-shaped input before writing config", () => {
  const dir = fixture();
  try {
    const syntheticSecret = Buffer.from(
      "untrusted comment: minisign encrypted secret key\nsynthetic\n",
    ).toString("base64");
    expect(run(dir, syntheticSecret).status).not.toBe(0);
    expect(existsSync(join(dir, "release-config.json"))).toBe(false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
it("release generator blocks mismatched build versions", () => {
  const dir = fixture();
  try {
    writeFileSync(
      join(dir, "src-tauri/tauri.conf.json"),
      JSON.stringify({ version: "0.2.0" }),
    );
    expect(run(dir, syntheticPublic).status).not.toBe(0);
    expect(existsSync(join(dir, "release-config.json"))).toBe(false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
it("release generator also blocks stale lockfiles", () => {
  const dir = fixture();
  try {
    writeFileSync(
      join(dir, "src-tauri/Cargo.lock"),
      '[[package]]\nname = "near-dot"\nversion = "0.0.9"\n',
    );
    expect(run(dir, syntheticPublic).status).not.toBe(0);
    expect(existsSync(join(dir, "release-config.json"))).toBe(false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
