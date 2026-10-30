"""
Check the software engineering docs: links, Mermaid diagrams, and traceability.

Usage (from the repo root):
    uv run python -m tools.docs_check              # all three checks
    uv run python -m tools.docs_check --no-render  # links + traceability only (no Node.js needed)

Checks, over software_engineering/:
  links     every relative markdown link points to an existing file, and its #anchor to an existing heading
  render    every ```mermaid block and every .mmd file renders with mermaid-cli (npx, system Chrome if found)
  trace     every user story belongs to exactly one use case, and every requirement id cited anywhere exists

Exits 1 if any check fails.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DOCS = Path("software_engineering")
REQUIREMENTS = DOCS / "requirements" / "requirements.md"
USER_STORIES = DOCS / "user_stories" / "user_stories.md"
MMDC = os.environ.get("MMDC", "npx -y -p @mermaid-js/mermaid-cli@11.17.0 mmdc").split()

FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
MERMAID = re.compile(r"^```mermaid\n(.*?)^```", re.MULTILINE | re.DOTALL)
FR_PREFIXES = [
    "CFG",
    "REG",
    "ETL",
    "MED",
    "GH",
    "LI",
    "OBS",
    "ART",
    "STO",
    "ORC",
    "VER",
    "TRG",
    "UI",
    "FEA",
    "DS",
    "FT",
    "EVAL",
    "INF",
    "OPS",
    "PRV",
]
NFR_PREFIXES = ["PERF", "REL", "SCL", "SEC", "PRIV", "MNT", "OBSV", "CMP", "COST"]
REQ_ID = re.compile(
    r"\b(?:(FR|NFR)-)?([A-Z]{2,5})-(\d{3})((?:\.\.\d{3})?)((?:/\d{3})*)",
)


def github_slug(heading: str) -> str:
    """The anchor GitHub gives a heading."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    seen: Counter[str] = Counter()
    found = set()
    for heading in re.findall(
        r"^#{1,6} (.+)$",
        FENCE.sub("", path.read_text()),
        re.MULTILINE,
    ):
        slug = github_slug(
            re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading),
        )  # a linked heading keeps its text
        found.add(f"{slug}-{seen[slug]}" if seen[slug] else slug)
        seen[slug] += 1
    return found


def check_links() -> list[str]:
    errors = []
    for md in sorted(DOCS.rglob("*.md")):
        prose = re.sub(r"`[^`\n]*`", "", FENCE.sub("", md.read_text()))
        for link in re.findall(r"\]\(([^)\s]+)\)", prose):
            if re.match(r"[a-z]+:", link):
                continue
            path, _, fragment = link.partition("#")
            target = (md.parent / path) if path else md
            if not target.exists():
                errors.append(f"{md}: missing file {link}")
            elif (
                fragment and target.suffix == ".md" and fragment not in anchors(target)
            ):
                errors.append(f"{md}: missing anchor {link}")
    return errors


def diagrams() -> list[tuple[str, str]]:
    found = [
        (f"{md}#{i}", block)
        for md in sorted(DOCS.rglob("*.md"))
        for i, block in enumerate(MERMAID.findall(md.read_text()))
    ]
    return found + [(str(mmd), mmd.read_text()) for mmd in sorted(DOCS.rglob("*.mmd"))]


def check_render() -> list[str]:
    if not shutil.which(MMDC[0]):
        return [
            f"render: {MMDC[0]} not found (install Node.js, or set MMDC, or use --no-render)",
        ]
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp, "puppeteer.json")
        chrome = next(
            (
                c
                for c in ("google-chrome", "chromium", "chromium-browser")
                if shutil.which(c)
            ),
            None,
        )
        config.write_text(
            json.dumps(
                {
                    "executablePath": shutil.which(chrome),
                    "args": ["--no-sandbox", "--headless=new"],
                }
                if chrome
                else {"args": ["--no-sandbox"]},
            ),
        )

        def render(item: tuple[int, tuple[str, str]]) -> str | None:
            i, (name, source) = item
            src, out = Path(tmp, f"d{i}.mmd"), Path(tmp, f"d{i}.svg")
            src.write_text(source)
            result = subprocess.run(  # noqa: S603  (fixed command, temp file paths)
                [*MMDC, "-q", "-i", str(src), "-o", str(out), "-p", str(config)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode or not out.exists():
                return (
                    f"{name}: does not render\n    "
                    # the parser's message, not the stack trace under it
                    + next(
                        (
                            line.strip()
                            for line in result.stderr.splitlines()
                            if "rror" in line
                        ),
                        result.stderr.strip()[-200:],
                    )
                )
            return None

        with ThreadPoolExecutor(max_workers=4) as pool:
            return [e for e in pool.map(render, enumerate(diagrams())) if e]


def requirement_ids(text: str) -> set[str]:
    """Requirement ids in text, with ranges (ETL-001..009) and lists (REG-011/014) expanded."""
    ids = set()
    for kind, prefix, num, span, more in REQ_ID.findall(text):
        group = (
            "FR"
            if prefix in FR_PREFIXES and kind != "NFR"
            else "NFR"
            if prefix in NFR_PREFIXES and kind != "FR"
            else None
        )
        if not group:
            continue
        nums = list(range(int(num), int(span[2:]) + 1)) if span else [int(num)]
        nums += [int(n) for n in more.split("/") if n]
        ids |= {f"{group}-{prefix}-{n:03d}" for n in nums}
    return ids


def check_trace() -> list[str]:
    errors = []
    stories = set(
        re.findall(
            r"^\| (US-\d{3}) \|",
            USER_STORIES.read_text().split("## Traceability")[0],
            re.MULTILINE,
        ),
    )
    in_use_cases: Counter[str] = Counter()
    for md in (DOCS / "use_cases").glob("[0-9]*.md"):
        for row in re.findall(
            r"^\| User stories \| (.+) \|$",
            md.read_text(),
            re.MULTILINE,
        ):
            in_use_cases.update(re.findall(r"US-\d{3}", row))
    for story in sorted(stories):
        if in_use_cases[story] != 1:
            errors.append(
                f"trace: {story} is in {in_use_cases[story]} use cases (expected 1)",
            )
    for story in sorted(set(in_use_cases) - stories):
        errors.append(f"trace: use cases cite {story}, which is not in the backlog")

    known = set(
        re.findall(
            r"^\| ((?:FR|NFR)-[A-Z]+-\d{3}) \|",
            REQUIREMENTS.read_text(),
            re.MULTILINE,
        ),
    )
    for path in sorted(
        [
            *DOCS.glob("*_diagrams/*.md"),
            *DOCS.rglob("*.mmd"),
            *DOCS.glob("use_cases/*.md"),
            USER_STORIES,
        ],
    ):
        for unknown in sorted(requirement_ids(path.read_text()) - known):
            errors.append(
                f"trace: {path} cites {unknown}, which is not in requirements.md",
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="skip rendering the Mermaid diagrams",
    )
    args = parser.parse_args()

    failed = 0
    checks = [("links", check_links), ("trace", check_trace)]
    if not args.no_render:
        checks.append(("render", check_render))
    for name, check in checks:
        errors = check()
        detail = f"{len(diagrams())} diagrams" if name == "render" else ""
        print(
            f"{'✗' if errors else '✓'} {name:<7} {len(errors)} problem(s) {detail}".rstrip(),
        )
        for error in errors:
            print(f"    {error}")
        failed += bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
