import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { compile } from "json-schema-to-typescript";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptDirectory, "..");
const schemaDirectory = resolve(webRoot, "../../packages/schemas");
const outputDirectory = resolve(webRoot, "src/lib/types/generated");
const checkOnly = process.argv.includes("--check");

const schemaNames = (await readdir(schemaDirectory))
  .filter((name) => name.endsWith(".json"))
  .sort();

const generated = new Map<string, string>();
for (const schemaName of schemaNames) {
  const schema = JSON.parse(await readFile(resolve(schemaDirectory, schemaName), "utf8")) as object;
  const source = await compile(schema, basename(schemaName, ".json"), {
    bannerComment: "/* Generated from packages/schemas. Do not edit by hand. */",
    additionalProperties: false,
    format: true,
    style: { singleQuote: false },
  });
  generated.set(`${basename(schemaName, ".json")}.ts`, source);
}

const indexSource = [
  "/* Generated from packages/schemas. Do not edit by hand. */",
  ...schemaNames.map(
    (schemaName) => `export type * from "./${basename(schemaName, ".json")}";`,
  ),
  "",
].join("\n");
generated.set("index.ts", indexSource);

if (checkOnly) {
  const stale: string[] = [];
  for (const [filename, expected] of generated) {
    const path = resolve(outputDirectory, filename);
    const actual = await readFile(path, "utf8").catch(() => "");
    if (actual !== expected) {
      stale.push(filename);
    }
  }
  if (stale.length > 0) {
    throw new Error(`Generated schema types are stale: ${stale.join(", ")}. Run npm run codegen.`);
  }
  console.log(`Generated schema types are current (${generated.size - 1} schemas).`);
} else {
  await mkdir(outputDirectory, { recursive: true });
  for (const [filename, source] of generated) {
    await writeFile(resolve(outputDirectory, filename), source, "utf8");
  }
  console.log(`Generated ${generated.size - 1} schema type files and index.ts.`);
}
