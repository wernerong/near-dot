import { it, expect } from "vitest";
import {
  createHash,
  generateKeyPairSync,
  randomBytes,
  sign,
} from "node:crypto";
import {
  mkdtempSync,
  mkdirSync,
  writeFileSync,
  copyFileSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { verifySignature } from "../scripts/verify-signatures.mjs";

function signedFixture(bytes: Buffer) {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const id = randomBytes(8);
  const pk = Buffer.concat([
    Buffer.from("Ed"),
    id,
    publicKey.export({ format: "der", type: "spki" }).subarray(-32),
  ]);
  const sig = sign(
    null,
    createHash("blake2b512").update(bytes).digest(),
    privateKey,
  );
  const trusted = "timestamp:1\tversion:0.3.0-preview.1";
  const global = sign(
    null,
    Buffer.concat([sig, Buffer.from(trusted)]),
    privateKey,
  );
  return {
    key: Buffer.from(
      `untrusted comment: minisign public key synthetic\n${pk.toString("base64")}\n`,
    ).toString("base64"),
    signature: Buffer.from(
      `untrusted comment: synthetic test\n${Buffer.concat([Buffer.from("ED"), id, sig]).toString("base64")}\ntrusted comment: ${trusted}\n${global.toString("base64")}\n`,
    ).toString("base64"),
  };
}
it("release verifier rejects altered packages, wrong keys and signed version substitution", () => {
  const bytes = Buffer.from(
    "synthetic installer bytes for signature testing only",
  );
  const { key, signature } = signedFixture(bytes);
  expect(() =>
    verifySignature(bytes, signature, key, "0.3.0-preview.1"),
  ).not.toThrow();
  expect(() =>
    verifySignature(Buffer.from("altered"), signature, key),
  ).toThrow();
  expect(() =>
    verifySignature(bytes, signature, signedFixture(bytes).key),
  ).toThrow();
  expect(() => verifySignature(bytes, signature, key, "0.4.0")).toThrow();
  const alteredComment = Buffer.from(signature, "base64")
    .toString()
    .replace("timestamp:1", "timestamp:2");
  expect(() =>
    verifySignature(bytes, Buffer.from(alteredComment).toString("base64"), key),
  ).toThrow();
});
it("combined feed requires all desktop installers and binds architecture, version and checksums", () => {
  const dir = mkdtempSync(join(tmpdir(), "near-dot-feed-test-"));
  try {
    mkdirSync(join(dir, "scripts"));
    mkdirSync(join(dir, "src-tauri"));
    mkdirSync(join(dir, "docs/releases"), { recursive: true });
    mkdirSync(join(dir, "artifacts"));
    for (const name of ["make-feed.mjs", "versions.mjs"])
      copyFileSync(resolve("scripts", name), join(dir, "scripts", name));
    for (const name of [
      "package.json",
      "package-lock.json",
      "src-tauri/tauri.conf.json",
      "src-tauri/Cargo.toml",
      "src-tauri/Cargo.lock",
    ])
      copyFileSync(resolve(name), join(dir, name));
    const version = JSON.parse(
      readFileSync(join(dir, "package.json"), "utf8"),
    ).version;
    writeFileSync(
      join(dir, `docs/releases/${version}.md`),
      "Synthetic release notes.",
    );
    const run = () =>
      spawnSync(
        process.execPath,
        [
          "scripts/make-feed.mjs",
          "artifacts",
          "example/near-dot",
          "preview",
          "0",
          "--require-all",
        ],
        { cwd: dir, encoding: "utf8" },
      );
    const add = (target: string) => {
      const name = `NearDot-${version}-${target}${target.startsWith("windows") ? ".exe" : ".app.tar.gz"}`;
      const bytes = Buffer.from(`Explicitly synthetic ${target} package`);
      writeFileSync(join(dir, "artifacts", name), bytes);
      writeFileSync(
        join(dir, "artifacts", `${name}.sig`),
        signedFixture(bytes).signature,
      );
      if (target.startsWith("darwin"))
        writeFileSync(
          join(dir, "artifacts", `NearDot-${version}-${target}.dmg`),
          "Synthetic installer",
        );
      return createHash("sha256").update(bytes).digest("hex");
    };
    const hash = add("windows-x86_64");
    expect(run().status).not.toBe(0);
    add("darwin-aarch64");
    add("darwin-x86_64");
    expect(run().status).toBe(0);
    const feed = JSON.parse(
      readFileSync(join(dir, "artifacts/preview.json"), "utf8"),
    );
    expect(feed).toMatchObject({
      version,
      channel: "preview",
      paused: true,
      rollout: 0,
    });
    expect(Object.keys(feed.platforms).sort()).toEqual([
      "darwin-aarch64",
      "darwin-x86_64",
      "windows-x86_64",
    ]);
    expect(feed.platforms["windows-x86_64"].sha256).toBe(hash);
    expect(feed.platforms["darwin-aarch64"].url).toContain(
      `/v${version}/NearDot-${version}-darwin-aarch64.app.tar.gz`,
    );
    writeFileSync(
      join(dir, "artifacts", "WrongVersion-windows-x86_64.exe"),
      "Synthetic substitution",
    );
    expect(run().status).not.toBe(0);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
