"""Extract question-like utterances from ChatDev WareHouse logs.

The extractor is intentionally conservative about sources: it reads only
``*.log`` files under a ChatDev ``WareHouse`` directory and writes one
deduplicated question per line for the classifier's plain-text loader.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


TIMESTAMP_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [A-Z]+\]")
ROLE_TURN_RE = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) [A-Z]+\] "
    r"(?P<speaker>[^:]+): \*\*"
    r"(?P<assistant_role>[^*<]+)<->(?P<user_role>[^*]+?) on : "
    r"(?P<phase>[^,]+), turn (?P<turn>\d+)\*\*"
)
SYSTEM_TABLE_RE = re.compile(r"^\| \*\*(?:assistant|user|phase|chat|model|task|placeholders|memory|need|with)_", re.I)
QUESTION_RE = re.compile(r"([^?]{8,500}\?)")
CODE_OR_URL_RE = re.compile(
    r"(https?://|www\.|\\n|def |class |import |return |self\.|f\"|file_path|"
    r"messagebox\.|re\.match|^\s*[#|]|```|<[^>]+>)",
    re.I,
)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_natural_question(text: str, role: str) -> bool:
    if role.casefold() == "system":
        return False
    if CODE_OR_URL_RE.search(text):
        return False
    if len(text) > 300:
        return False
    alpha_count = sum(ch.isalpha() for ch in text)
    if alpha_count < 8:
        return False
    return True


def iter_dialogue_blocks(log_path: Path):
    meta = None
    block: list[str] = []

    for raw_line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = ROLE_TURN_RE.match(raw_line)
        if match:
            if meta and block:
                yield meta, "\n".join(block)
            meta = {
                "timestamp": match.group("timestamp").strip(),
                "speaker": match.group("speaker").strip(),
                "assistant_role": match.group("assistant_role").strip(),
                "user_role": match.group("user_role").strip(),
                "phase": match.group("phase").strip(),
                "turn": match.group("turn").strip(),
            }
            block = [ROLE_TURN_RE.sub("", raw_line).strip()]
            continue

        if meta and TIMESTAMP_RE.match(raw_line):
            if block:
                yield meta, "\n".join(block)
            meta = None
            block = []
            continue

        if meta:
            if SYSTEM_TABLE_RE.match(raw_line):
                continue
            block.append(raw_line)

    if meta and block:
        yield meta, "\n".join(block)


def iter_questions(warehouse_dir: Path):
    for log_path in sorted(warehouse_dir.glob("*/*.log")):
        sample = log_path.parent.name
        for meta, block in iter_dialogue_blocks(log_path):
            for line in block.splitlines():
                for question in QUESTION_RE.findall(line):
                    cleaned = normalize_space(question)
                    if len(cleaned) < 12 or not is_natural_question(cleaned, meta["speaker"]):
                        continue
                    yield {
                        "question": cleaned,
                        "source_log": str(log_path),
                        "project": sample,
                        **meta,
                    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse-dir", required=True, type=Path)
    parser.add_argument("--out-txt", required=True, type=Path)
    parser.add_argument("--out-csv", required=True, type=Path)
    args = parser.parse_args()

    seen: set[str] = set()
    rows = []
    for row in iter_questions(args.warehouse_dir):
        key = row["question"].casefold()
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    args.out_txt.parent.mkdir(parents=True, exist_ok=True)
    args.out_txt.write_text("\n".join(row["question"] for row in rows) + "\n", encoding="utf-8")

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question",
                "source_log",
                "project",
                "timestamp",
                "speaker",
                "assistant_role",
                "user_role",
                "phase",
                "turn",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"logs_scanned={len(list(args.warehouse_dir.glob('*/*.log')))}")
    print(f"questions={len(rows)}")
    print(f"out_txt={args.out_txt}")
    print(f"out_csv={args.out_csv}")


if __name__ == "__main__":
    main()
