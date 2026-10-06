import { readdirSync } from "node:fs";
import { join } from "node:path";

/**
 * Recursively collect every file under `dir` whose name satisfies `predicate`, full path.
 *
 * Shared by `layering.test.ts` and any future test that needs a filesystem walk, so a
 * directory walk read off the filesystem -- and therefore covering a file added later
 * without being listed -- is written once rather than many times.
 */
export function walkFiles(dir: string, predicate: (name: string) => boolean): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return walkFiles(path, predicate);
    return predicate(entry.name) ? [path] : [];
  });
}
