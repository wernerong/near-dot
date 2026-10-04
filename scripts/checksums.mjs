import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
const dir = process.argv[2];
const lines = fs
  .readdirSync(dir)
  .filter(
    (f) => f !== "SHA256SUMS.txt" && fs.statSync(path.join(dir, f)).isFile(),
  )
  .sort()
  .map(
    (f) =>
      `${createHash("sha256")
        .update(fs.readFileSync(path.join(dir, f)))
        .digest("hex")}  ${f}`,
  );
fs.writeFileSync(path.join(dir, "SHA256SUMS.txt"), lines.join("\n") + "\n");
