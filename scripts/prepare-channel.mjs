import fs from "node:fs";
import { verifySignature } from "./verify-signatures.mjs";
const [source, output, version, channel, rolloutText, pausedText] =
  process.argv.slice(2);
const publicKey = process.env.NEAR_DOT_UPDATER_PUBLIC_KEY;
const repo = process.env.NEAR_DOT_UPDATE_REPO;
if (
  !publicKey ||
  !repo ||
  !["stable", "preview"].includes(channel) ||
  !["true", "false"].includes(pausedText)
)
  throw new Error("Invalid channel control request.");
const rollout = Number(rolloutText);
if (!Number.isInteger(rollout) || rollout < 0 || rollout > 100)
  throw new Error("Rollout must be 0–100.");
const bytes = fs.readFileSync(source);
verifySignature(bytes, fs.readFileSync(`${source}.sig`, "utf8"), publicKey);
const feed = JSON.parse(bytes);
if (feed.version !== version || (channel === "stable" && version.includes("-")))
  throw new Error("Release/channel version mismatch.");
for (const [target, artifact] of Object.entries(feed.platforms)) {
  const extension = target === "windows-x86_64" ? ".exe" : ".app.tar.gz";
  if (
    !["windows-x86_64", "darwin-aarch64", "darwin-x86_64"].includes(target) ||
    artifact.url !==
      `https://github.com/${repo}/releases/download/v${version}/NearDot-${version}-${target}${extension}`
  )
    throw new Error("Release package identity mismatch.");
}
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(
  `${output}/${channel}.json`,
  JSON.stringify(
    { ...feed, channel, rollout, paused: pausedText === "true" },
    null,
    2,
  ) + "\n",
);
console.log(
  "Verified release feed transformed. Sign before committing channel controls.",
);
