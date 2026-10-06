import { readFileSync, readdirSync } from "node:fs";
import { dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { walkFiles } from "./test/walkFiles";

/**
 * Enforces the layer rules described in `web/CLAUDE.md` across every non-test source
 * file. Reads `src/` off the filesystem -- a file added later is covered without being
 * listed. Test files are excluded: a test legitimately mocks `api/client` (`vi.mock`),
 * and a `queryFn` in a fixture is not a layering breach.
 *
 * Threshold is 5 at scaffold time (nine non-test files exist: main.tsx, App.tsx,
 * api/client.ts, api/errors.ts, api/queryKeys.ts, api/schema.d.ts, routes/NotFound.tsx,
 * test/walkFiles.ts, hooks/useHealth.ts). Raised each time a route is added until the
 * test is no longer the binding constraint.
 */

const SRC = dirname(fileURLToPath(import.meta.url));

const allFiles = walkFiles(
  SRC,
  (name) => /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name),
);

/** Relative path from `src/`, forward-slash normalised, for readable failure messages. */
function rel(filePath: string): string {
  return relative(SRC, filePath).split("\\").join("/");
}

/** True when `filePath` is inside `src/<section>/` (not deeper subdirectories of section). */
function inSection(filePath: string, section: string): boolean {
  return rel(filePath).startsWith(section + "/");
}

/**
 * Forbidden import targets per source section, mirroring `web/CLAUDE.md`'s layer rule.
 * `api/client` is deliberately not a target here -- rule 1 already covers every file
 * outside `hooks/` and `api/`, more strictly, so a duplicate clause could never fire on
 * its own.
 *
 * Scaffold contains four sections: `api`, `hooks`, `routes`, `test`. A new directory
 * added without a row here fails the "every top-level directory has a row" check below
 * rather than going unruled -- an empty row is still a row, so a directory with nothing
 * to forbid names that on purpose instead of by omission.
 */
const MAY_NOT_IMPORT: Record<string, readonly string[]> = {
  api: ["hooks", "routes", "components"],
  hooks: ["routes", "components"],
  routes: [],
  test: ["hooks", "routes", "components"],
};

/**
 * The sections `web/CLAUDE.md` calls pure: the only ones whose `import type` from
 * `hooks/` or `routes/` is allowed. At scaffold time `test` is the only pure section
 * present; `lib`, `domain`, `theme` are added here and to MAY_NOT_IMPORT when they
 * arrive -- their exemption behaviour is the same as `test`'s.
 */
const PURE_SECTIONS = new Set(["test"]);

type LayerRule = {
  name: string;
  applies: (filePath: string) => boolean;
  title: (relPath: string) => string;
  offends: (src: string, filePath: string) => string[];
};

const RULES: LayerRule[] = [
  {
    name: "layer rule 1: api/client is only imported by hooks/ and api/",
    applies: (fp) => !inSection(fp, "hooks") && !inSection(fp, "api"),
    title: (r) => `${r} does not import api/client`,
    offends: (src, _fp) =>
      src.split("\n").filter((line) => /from\s+['"][^'"]*api\/client['"]/.test(line)),
  },
  {
    name: "layer rule 2: queryFn is only declared inside hooks/ and api/",
    applies: (fp) => !inSection(fp, "hooks") && !inSection(fp, "api"),
    title: (r) => `${r} does not declare queryFn`,
    // A queryFn: outside hooks/ or api/ means a route calls the API directly -- the cache
    // key is then undiscoverable from any hook that would invalidate it.
    offends: (src, _fp) => {
      const uncommented = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*/g, "");
      return uncommented.split("\n").filter((line) => /queryFn\s*:/.test(line));
    },
  },
  {
    name: "layer rule 3: a section imports only where MAY_NOT_IMPORT allows",
    applies: (fp) => (MAY_NOT_IMPORT[rel(fp).split("/")[0]] ?? []).length > 0,
    title: (r) => `${r} does not import from ${MAY_NOT_IMPORT[r.split("/")[0]].join(", ")}`,
    offends: (src, fp) => {
      const section = rel(fp).split("/")[0];
      const targets = MAY_NOT_IMPORT[section] ?? [];
      const sourceIsPure = PURE_SECTIONS.has(section);
      return src.split("\n").filter((line) => {
        const isTypeImport = /^\s*import\s+type\b/.test(line);
        return targets.some((target) => {
          if (!new RegExp(`from\\s+['"][^'"]*\\/${target}\\/`).test(line)) return false;
          const exemptTarget = target === "hooks" || target === "routes";
          const exempt = isTypeImport && sourceIsPure && exemptTarget;
          return !exempt;
        });
      });
    },
  },
  {
    // A route module is an entry point; exporting helpers or types from it makes the layer
    // boundary invisible to readers and importers alike. Counts every top-level `export`
    // statement -- named, default, type, re-export -- not a fixed keyword list, so a form
    // like `export { helper }` or `export default` cannot slip past uncounted.
    name: "layer rule 4: a route module has at most one export",
    applies: (fp) => inSection(fp, "routes"),
    title: (r) => `${r} has at most one export`,
    offends: (src, _fp) => {
      const uncommented = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*/g, "");
      const exports = uncommented.split("\n").filter((line) => /^export\b/.test(line));
      // Return all export lines when there is more than one, so the failure message names them.
      return exports.length > 1 ? exports : [];
    },
  },
];

describe("src/ has files to check", () => {
  it("finds at least five non-test source files", () => {
    // Without this, the rule loops pass vacuously if the walk is ever broken.
    // Threshold is 5 at scaffold time; raise it as routes are added.
    expect(allFiles.length).toBeGreaterThanOrEqual(5);
  });

  it("gives every top-level directory a row in MAY_NOT_IMPORT", () => {
    // A directory `MAY_NOT_IMPORT` does not list is silently unruled in both directions:
    // nothing says what it may import, and nothing says whether it may be imported. Reads
    // `src/` off the filesystem, so a directory added later fails here rather than going
    // unruled -- an empty row is still a row, so a directory with nothing to forbid names
    // that on purpose instead of by omission.
    const dirs = readdirSync(SRC, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name);
    const unlisted = dirs.filter((name) => !(name in MAY_NOT_IMPORT));
    expect(unlisted).toEqual([]);
  });
});

describe("layer rule 3's import-type exemption", () => {
  // rel(fp) reads the section off the path, so a fabricated path under SRC exercises the
  // predicate without needing a file on disk for every case.
  const probe = (section: string) => `${SRC}/${section}/probe.ts`;

  it("exempts a pure section's type-only import into hooks/", () => {
    // test/ is the pure section present at scaffold time.
    const offending = RULES[2].offends(
      'import type { SessionContext } from "../hooks/useSession";\n',
      probe("test"),
    );
    expect(offending).toHaveLength(0);
  });

  it("still flags a pure section's runtime import into hooks/", () => {
    const offending = RULES[2].offends(
      'import { useSessionContext } from "../hooks/useSession";\n',
      probe("test"),
    );
    expect(offending).toHaveLength(1);
  });

  it("flags a type-only upward import from api/ into hooks/", () => {
    // api/ is not a pure section, so the exemption does not apply.
    const offending = RULES[2].offends(
      'import type { SessionContext } from "../hooks/useSession";\n',
      probe("api"),
    );
    expect(offending).toHaveLength(1);
  });

  it("flags a type-only upward import from api/ into routes/", () => {
    // api/ is not a pure section, so type-only imports from routes/ are still forbidden.
    const offending = RULES[2].offends(
      'import type { Foo } from "../routes/Account";\n',
      probe("api"),
    );
    expect(offending).toHaveLength(1);
  });

  it("exempts a pure section's type-only import into routes/", () => {
    // test/ is pure; type-only imports into routes/ are allowed (e.g. to reference a
    // component's prop type without depending on its runtime).
    const offending = RULES[2].offends(
      'import type { Foo } from "../routes/NotFound";\n',
      probe("test"),
    );
    expect(offending).toHaveLength(0);
  });
});

for (const rule of RULES) {
  describe(rule.name, () => {
    for (const filePath of allFiles) {
      if (!rule.applies(filePath)) continue;
      it(rule.title(rel(filePath)), () => {
        const src = readFileSync(filePath, "utf8");
        const offending = rule.offends(src, filePath);
        expect(offending).toHaveLength(0);
      });
    }
  });
}
