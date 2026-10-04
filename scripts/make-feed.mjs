import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
const [directory, repo, channel = "stable", rolloutText = "0"] =
  process.argv.slice(2);
if (!directory || !repo || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo))
  throw new Error(
    "Usage: node scripts/make-feed.mjs DIRECTORY OWNER/REPO stable|preview ROLLOUT",
  );
if (!["stable", "preview"].includes(channel))
  throw new Error("Unknown channel.");
const version = JSON.parse(fs.readFileSync("package.json", "utf8")).version;
if (channel === "stable" && version.includes("-"))
  throw new Error("Stable channel requires a stable version.");
const rollout = Number(rolloutText);
if (!Number.isInteger(rollout) || rollout < 0 || rollout > 100)
  throw new Error("Invalid rollout.");
const platforms = {};
for (const file of fs.readdirSync(directory)) {
  const target = ["windows-x86_64", "darwin-aarch64", "darwin-x86_64"].find(
    (t) => file.includes(t),
  );
  if (!target || !/\.(exe|tar\.gz)$/.test(file)) continue;
  const artifact = path.join(directory, file);
  platforms[target] = {
    url: `https://github.com/${repo}/releases/download/v${version}/${encodeURIComponent(file)}`,
    signature: fs.readFileSync(artifact + ".sig", "utf8").trim(),
    sha256: createHash("sha256")
      .update(fs.readFileSync(artifact))
      .digest("hex"),
  };
}
if (!Object.keys(platforms).length)
  throw new Error("No signed architecture-specific packages found.");
const notes = fs.readFileSync(`docs/releases/${version}.md`, "utf8");
const feed = { version, notes, channel, paused: true, rollout, platforms };
fs.writeFileSync(
  path.join(directory, `${channel}.json`),
  JSON.stringify(feed, null, 2) + "\n",
);
console.log("Paused feed generated. Sign it after final rollout review.");
