import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

interface RuleFixture {
  id: string;
  citation: string;
  description: string;
  href: string;
}

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptDirectory, "..");
const rulesPath = resolve(webRoot, "../api/bridgeline/rules/RULES.md");
const outputDirectory = resolve(webRoot, "mock/generated");
const outputPath = resolve(outputDirectory, "rules.json");
const checkOnly = process.argv.includes("--check");

const markdown = await readFile(rulesPath, "utf8");
const version = /^Rules version: `([^`]+)`$/m.exec(markdown)?.[1];
if (version === undefined) {
  throw new Error("RULES.md does not contain a rules version.");
}

const blockPattern = /^## `([^`]+)`\n\n- Citation: \[`([^`]+)`\]\(([^)]+)\)\n- Description: (.+)$/gm;
const rules: RuleFixture[] = Array.from(markdown.matchAll(blockPattern), (match) => ({
  id: requiredCapture(match[1], "rule id"),
  citation: requiredCapture(match[2], "citation"),
  href: requiredCapture(match[3], "citation URL"),
  description: requiredCapture(match[4], "description"),
}));
if (rules.length === 0) {
  throw new Error("RULES.md did not yield any registry entries.");
}

const source = `${JSON.stringify({ rules_version: version, rules }, null, 2)}\n`;
if (checkOnly) {
  const current = await readFile(outputPath, "utf8").catch(() => "");
  if (current !== source) {
    throw new Error("Generated rule fixture is stale. Run npm run fixtures.");
  }
  console.log(`Generated rule fixture is current (${rules.length} rules).`);
} else {
  await mkdir(outputDirectory, { recursive: true });
  await writeFile(outputPath, source, "utf8");
  console.log(`Generated Riverside mock registry with ${rules.length} exact rules.`);
}

function requiredCapture(value: string | undefined, label: string): string {
  if (value === undefined || value.length === 0) {
    throw new Error(`RULES.md contains an empty ${label}.`);
  }
  return value;
}
