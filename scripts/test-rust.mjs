// Tauri embeds the app manifest, but its mock-runtime library test executable
// also needs Common Controls v6. Embed it only in that compiled test harness.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = fileURLToPath(new URL("../", import.meta.url));
const args = ["test", "--manifest-path", "src-tauri/Cargo.toml", "--locked"];
function run(command, commandArgs, capture = false) {
  const result = spawnSync(command, commandArgs, {
    cwd: root,
    encoding: "utf8",
    stdio: capture ? ["inherit", "pipe", "inherit"] : "inherit",
    maxBuffer: 32 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  return result;
}

if (process.platform === "win32") {
  const found = run("where.exe", ["mt.exe"], true);
  let tool = found.status === 0 ? found.stdout.trim().split(/\r?\n/)[0] : null;
  if (!tool) {
    const sdk = path.join(
      process.env["ProgramFiles(x86)"],
      "Windows Kits/10/bin",
    );
    tool = fs
      .readdirSync(sdk)
      .sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))
      .map((version) => path.join(sdk, version, "x64/mt.exe"))
      .find((candidate) => fs.existsSync(candidate));
  }
  if (!tool)
    throw new Error(
      "Windows Rust tests require the Windows SDK manifest tool (mt.exe).",
    );
  const build = run(
    "cargo",
    [...args, "--no-run", "--message-format=json"],
    true,
  );
  const artifacts = [];
  for (const line of build.stdout.split(/\r?\n/).filter(Boolean)) {
    const item = JSON.parse(line);
    if (item.reason === "compiler-message" && item.message.rendered)
      process.stderr.write(item.message.rendered);
    if (
      item.reason === "compiler-artifact" &&
      item.target.name === "near_dot_lib" &&
      item.profile.test &&
      item.executable
    )
      artifacts.push(item.executable);
  }
  if (build.status !== 0) process.exit(build.status ?? 1);
  if (artifacts.length !== 1)
    throw new Error(
      "Expected exactly one compiled Near Dot library unit-test executable.",
    );
  const manifest = path.join(root, "src-tauri/examples/update-drill.manifest");
  const embed = run(tool, [
    "-nologo",
    "-manifest",
    manifest,
    `-outputresource:${artifacts[0]};#1`,
  ]);
  if (embed.status !== 0) process.exit(embed.status ?? 1);
  console.log(
    "Common Controls v6 embedded in the Windows library test harness.",
  );
}

process.exit(run("cargo", args).status ?? 1);
