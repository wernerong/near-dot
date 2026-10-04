// Release-side check of Tauri's base64 Minisign format using Node's crypto.
// Matches minisign-verify 0.2.5: ED prehash + key ID + trusted-comment signature.
// Installed clients still use the maintained Tauri updater and minisign-verify.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash, createPublicKey, verify } from "node:crypto";

export function verifySignature(bytes, signature, publicKey, expectedVersion) {
  const keyLines = Buffer.from(publicKey, "base64")
    .toString("utf8")
    .trim()
    .split(/\r?\n/);
  const lines = Buffer.from(signature.trim(), "base64")
    .toString("utf8")
    .trim()
    .split(/\r?\n/);
  const key = Buffer.from(keyLines[1] || "", "base64");
  const sig = Buffer.from(lines[1] || "", "base64");
  const global = Buffer.from(lines[3] || "", "base64");
  if (
    keyLines.length !== 2 ||
    !keyLines[0].startsWith("untrusted comment: minisign public key") ||
    key.length !== 42 ||
    key.subarray(0, 2).toString() !== "Ed" ||
    lines.length !== 4 ||
    !lines[0].startsWith("untrusted comment: ") ||
    !lines[2].startsWith("trusted comment: ") ||
    sig.length !== 74 ||
    sig.subarray(0, 2).toString() !== "ED" ||
    global.length !== 64 ||
    !sig.subarray(2, 10).equals(key.subarray(2, 10))
  )
    throw new Error("Invalid updater signature or verification key.");
  const pk = createPublicKey({
    key: Buffer.concat([
      Buffer.from("302a300506032b6570032100", "hex"),
      key.subarray(10),
    ]),
    format: "der",
    type: "spki",
  });
  const signatureBytes = sig.subarray(10);
  if (
    !verify(
      null,
      createHash("blake2b512").update(bytes).digest(),
      pk,
      signatureBytes,
    ) ||
    !verify(
      null,
      Buffer.concat([signatureBytes, Buffer.from(lines[2].slice(17))]),
      pk,
      global,
    )
  )
    throw new Error(
      "Updater signature verification failed; draft release blocked.",
    );
  if (
    expectedVersion &&
    !lines[2].slice(17).split("\t").includes(`version:${expectedVersion}`)
  )
    throw new Error(
      "Updater signature does not bind the reviewed app version.",
    );
}
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const directory = process.argv[2];
  const publicKey = process.env.NEAR_DOT_UPDATER_PUBLIC_KEY;
  if (!directory || !publicKey)
    throw new Error(
      "Provide the artifact directory and verification PUBLIC key.",
    );
  const files = fs
    .readdirSync(directory)
    .filter((file) => file.endsWith(".sig"));
  if (!files.length) throw new Error("No signed release files found.");
  const version = JSON.parse(fs.readFileSync("package.json", "utf8")).version;
  for (const file of files)
    verifySignature(
      fs.readFileSync(path.join(directory, file.slice(0, -4))),
      fs.readFileSync(path.join(directory, file), "utf8"),
      publicKey,
      file.endsWith(".json.sig") ? undefined : version,
    );
  console.log(
    `${files.length} release signatures verified against the shipped public key.`,
  );
}
