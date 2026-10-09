"""check_citations.py - STUDENT IMPLEMENTS `check`.   Runs INSIDE the sandbox (standard library only).

research.py uploads this file to the sandbox and the lead agent runs it with the `execute` tool:
    python3 /tmp/work/research/check_citations.py [report.md] [sources.json]
It must exit 0 and print "OK: ..." when the report is consistent, else print each problem and exit 1.
"""
import json
import re
import sys

REPORT = "/tmp/work/report/report.md"
SOURCES = "/tmp/work/research/sources.json"

_GROUP_RE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\](?!\()")
_CODE_RE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
_REF_HEADING_RE = re.compile(r"(?m)^##[ \t]+References[ \t]*$")
_URL_RE = re.compile(r"https?://[^\s)\]>]+")


def _expand_group(group):
    numbers = []
    for part in re.split(r"\s*,\s*", group):
        if not part:
            continue
        span = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        if span:
            start, end = int(span.group(1)), int(span.group(2))
            numbers.extend(range(start, end + 1) if end >= start else [start, end])
        else:
            numbers.append(int(part))
    return numbers


def _body_of(report_text):
    matches = list(_REF_HEADING_RE.finditer(report_text))
    if not matches:
        return report_text.rstrip()
    return report_text[:matches[-1].start()].rstrip()


def _extract_cited_numbers(body):
    cited = set()
    for chunk in _CODE_RE.split(body):
        if not chunk:
            continue
        if chunk.startswith("`") and chunk.endswith("`"):
            continue
        for match in _GROUP_RE.finditer(chunk):
            cited.update(_expand_group(match.group(1)))
    return cited


def check(report_text, sources):
    """Return a list of problem strings (empty list = OK).

    PSEUDO-CODE:
      problems = []
      if sources is empty: return ["no sources in sources.json"]
      for each source entry:
          n must be an int                       -> problem if not
          url must start with http:// or https://-> problem if not
          the same url must not appear twice     -> problem if duplicated
      split report_text at the heading "## References":
          body = text before it; if the heading is missing -> problem
      cited = set of numbers found as [n] in the BODY only (not in the reference list; use a regex)
      every number in `cited` must exist in sources -> problem "[n] cited but missing from sources.json"
      every source number must be in `cited`        -> problem "source [n] never cited"
      the lines of the References section that start with "[n]" (regex) are the reference lines:
          every source needs exactly ONE reference line (none missing, no number twice, no number that is not a source)
          each reference line holds exactly ONE http(s) URL and it must equal that source's url
          (a line bundling several sources under one number is a problem)
      return problems
    """
    problems = []
    if not isinstance(sources, list):
        return ["sources.json must be a JSON list"]
    if not sources:
        return ["no sources in sources.json"]

    by_number = {}
    seen_urls = {}
    for index, entry in enumerate(sources):
        if not isinstance(entry, dict):
            problems.append(f"source #{index + 1} is not an object")
            continue
        n = entry.get("n")
        if type(n) is not int:
            problems.append(f"source #{index + 1} has non-integer n")
        else:
            if n in by_number:
                problems.append(f"duplicate source number [{n}]")
            by_number[n] = entry

        url = entry.get("url")
        if not isinstance(url, str) or not re.match(r"^https?://", url):
            problems.append(f"source [{n}] url must start with http:// or https://")
        else:
            if url in seen_urls and seen_urls[url] != n:
                problems.append(f"duplicate url in sources.json: {url}")
            seen_urls[url] = n

    ref_heading_matches = list(_REF_HEADING_RE.finditer(report_text))
    if not ref_heading_matches:
        problems.append("missing ## References heading")
    body = _body_of(report_text)
    cited = _extract_cited_numbers(body)

    for number in sorted(cited):
        if number not in by_number:
            problems.append(f"[{number}] cited but missing from sources.json")
    for number in sorted(by_number):
        if number not in cited:
            problems.append(f"source [{number}] never cited")

    if ref_heading_matches:
        ref_start = ref_heading_matches[-1].end()
        ref_text = report_text[ref_start:]
        ref_lines = []
        for line in ref_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = re.match(r"^\[\s*(\d+)\s*\]", stripped)
            if match:
                ref_lines.append((int(match.group(1)), stripped))

        seen_reference_numbers = set()
        for number, line in ref_lines:
            if number in seen_reference_numbers:
                problems.append(f"duplicate reference line [{number}]")
            seen_reference_numbers.add(number)
            if number not in by_number:
                problems.append(f"reference line [{number}] not in sources.json")
                continue
            urls = _URL_RE.findall(line)
            if len(urls) != 1:
                problems.append(f"reference [{number}] must contain exactly one URL")
            else:
                expected_url = by_number[number].get("url")
                if expected_url is None:
                    continue
                normalized = urls[0].rstrip(").,;\"")
                if normalized != expected_url:
                    problems.append(f"reference [{number}] URL does not match sources.json")

        for number in sorted(by_number):
            if number not in seen_reference_numbers:
                problems.append(f"missing reference line for [{number}]")

    return list(dict.fromkeys(problems))


def main(argv):
    report_path = argv[1] if len(argv) > 1 else REPORT
    sources_path = argv[2] if len(argv) > 2 else SOURCES
    try:
        with open(report_path, encoding="utf-8") as f:
            report = f.read()
        with open(sources_path, encoding="utf-8") as f:
            sources = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"cannot read inputs: {exc}")
        return 1
    problems = check(report, sources)
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {len(sources)} sources, all citations resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
