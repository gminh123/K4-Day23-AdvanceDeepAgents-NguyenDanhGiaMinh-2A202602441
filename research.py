"""research.py - STUDENT IMPLEMENTS.  The main script.   Guide: GUIDE.md, part 3.

Usage:  python research.py "survey about world model"
Result: reports/<slug>.md   reports/<slug>.sources.json   reports/<slug>.meta.json
"""
import json
import os
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from agents import (
    FINALIZER_PATH,
    REPORT_PATH,
    SOURCES_PATH,
    VALIDATOR_PATH,
    WORKDIR,
    build_lead_agent,
)
from model import make_model
from sandbox import download, open_sandbox, upload

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
VALIDATOR_SOURCE = ROOT / "check_citations.py"
FINALIZER_SOURCE = ROOT / "finalize_citations.py"   # provided: uploaded next to your validator


def slugify(topic):
    """Turn a topic into a safe file name: lower case, runs of non-word characters become one "-", max 60 chars,
    never empty (fall back to "topic"). The topic is user input: "../../x" must not escape reports/."""
    slug = re.sub(r"[^\w]+", "-", topic.strip().lower(), flags=re.UNICODE).strip("-")
    return slug[:60].rstrip("-") or "topic"


def build_prompt(topic):
    """The user message sent to the lead agent."""
    return (
        f"Research topic: {topic.strip()}\n\n"
        "Produce a concise, evidence-based survey report in English using the available "
        "research tools and subagents. Follow the required report structure and citation "
        "workflow in your system instructions. Save the report and sources to the specified "
        "sandbox paths, then run the citation finalizer and validator until validation "
        "succeeds."
    )


def summarize(messages, elapsed, model_name):
    """Return {"model", "elapsed_s", "subagent_calls", "tool_calls": {name: count}, "tokens": {"input", "output"}}.

    PSEUDO-CODE: walk the lead's messages; for every message with tool_calls count call["name"] (subagent_calls = the
    count of "task"); add the input/output token counts from each message's usage_metadata when present.
    (Lead messages only: subagent tokens are not included, so this undercounts the real cost.)
    elapsed_s rounded to 0.1.
    """
    tool_calls = Counter()
    input_tokens = 0
    output_tokens = 0

    for message in messages or []:
        if isinstance(message, dict):
            calls = message.get("tool_calls") or []
            usage = message.get("usage_metadata") or {}
        else:
            calls = getattr(message, "tool_calls", None) or []
            usage = getattr(message, "usage_metadata", None) or {}
        if not calls and isinstance(message, dict):
            calls = (message.get("additional_kwargs") or {}).get("tool_calls", [])
        elif not calls:
            calls = (
                getattr(message, "additional_kwargs", None) or {}
            ).get("tool_calls", [])

        for call in calls:
            if isinstance(call, dict):
                name = call.get("name")
                if not name and isinstance(call.get("function"), dict):
                    name = call["function"].get("name")
            else:
                name = getattr(call, "name", None)
            if name:
                tool_calls[str(name)] += 1

        if isinstance(usage, dict):
            input_tokens += int(usage.get("input_tokens", 0) or 0)
            output_tokens += int(usage.get("output_tokens", 0) or 0)

    return {
        "model": model_name,
        "elapsed_s": round(float(elapsed), 1),
        "subagent_calls": tool_calls.get("task", 0),
        "tool_calls": dict(sorted(tool_calls.items())),
        "tokens": {"input": input_tokens, "output": output_tokens},
    }


def save_outputs(backend, topic, messages, elapsed, model_name, reports_dir=REPORTS):
    """Download the report from the sandbox and write the three files into reports_dir. Return the report path.

    PSEUDO-CODE:
      files = download(backend, [REPORT_PATH, SOURCES_PATH])
      if the report is missing/empty or sources.json is missing/invalid JSON: raise RuntimeError and WRITE NOTHING
          (a failed run must never leave an empty or half-written report behind)
      write <slug>.sources.json, <slug>.meta.json (topic + summarize(...) + n_sources + source_families: the sorted
      distinct "source" values of sources.json) and <slug>.md
    """
    files = download(backend, [REPORT_PATH, SOURCES_PATH])
    report_bytes = files.get(REPORT_PATH)
    sources_bytes = files.get(SOURCES_PATH)
    if not report_bytes:
        raise RuntimeError("report.md is missing or empty in the sandbox")
    if not sources_bytes:
        raise RuntimeError("sources.json is missing or empty in the sandbox")

    try:
        report = (
            report_bytes.decode("utf-8")
            if isinstance(report_bytes, bytes)
            else str(report_bytes)
        )
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"report.md is not valid UTF-8: {exc}") from exc
    if not report.strip():
        raise RuntimeError("report.md is missing or empty in the sandbox")

    try:
        sources_text = (
            sources_bytes.decode("utf-8")
            if isinstance(sources_bytes, bytes)
            else str(sources_bytes)
        )
        sources = json.loads(sources_text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError(f"sources.json is missing or invalid JSON: {exc}") from exc
    if not isinstance(sources, list) or any(not isinstance(source, dict) for source in sources):
        raise RuntimeError("sources.json must contain a JSON list of source objects")
    if not sources:
        raise RuntimeError("sources.json contains no sources")

    metadata = summarize(messages, elapsed, model_name)
    metadata["topic"] = topic
    metadata["n_sources"] = len(sources)
    metadata["source_families"] = sorted(
        {source["source"] for source in sources if isinstance(source.get("source"), str)}
    )

    reports_dir = Path(reports_dir)
    stem = slugify(topic)
    report_path = reports_dir / f"{stem}.md"
    sources_path = reports_dir / f"{stem}.sources.json"
    metadata_path = reports_dir / f"{stem}.meta.json"
    output_contents = {
        report_path.name: report,
        sources_path.name: json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
        metadata_path.name: json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=reports_dir) as staging_dir:
        staged_paths = []
        for filename, content in output_contents.items():
            staged_path = Path(staging_dir) / filename
            staged_path.write_text(content, encoding="utf-8")
            staged_paths.append((staged_path, reports_dir / filename))
        for staged_path, target_path in staged_paths:
            os.replace(staged_path, target_path)
    return report_path


def main(topic):
    """Return the process exit code (0 ok, 1 failed run, 2 no topic).

    PSEUDO-CODE:
      empty topic -> print usage to stderr, return 2
      model = make_model(); start = time.monotonic()
      with open_sandbox() as backend:                # the sandbox is always cleaned up, even on errors
          backend.execute("mkdir -p <WORKDIR>/research/notes <WORKDIR>/report")
          upload(backend, {VALIDATOR_PATH: VALIDATOR_SOURCE.read_bytes(), FINALIZER_PATH: FINALIZER_SOURCE.read_bytes()})
          agent = build_lead_agent(backend, model)
          result = agent.invoke({"messages": [{"role": "user", "content": build_prompt(topic)}]},
                                config={"recursion_limit": 1000})
          save_outputs(...); on RuntimeError print "FAILED: ..." to stderr and return 1
      print where the report was saved; return 0
    """
    if not topic or not topic.strip():
        print('Usage: python research.py "<topic>"', file=sys.stderr)
        return 2

    topic = topic.strip()
    try:
        model = make_model()
        model_name = (
            getattr(model, "model_name", None)
            or getattr(model, "name", None)
            or os.getenv("LAB_MODEL")
            or os.getenv("OPENAI_DEPLOYMENT_MODEL")
            or type(model).__name__
        )
        start = time.monotonic()
        with open_sandbox() as backend:
            setup = backend.execute(
                f"mkdir -p {WORKDIR}/research/notes {WORKDIR}/report"
            )
            if getattr(setup, "exit_code", 0) != 0:
                raise RuntimeError(
                    f"cannot create sandbox work directories: {getattr(setup, 'output', setup)}"
                )

            upload(
                backend,
                {
                    VALIDATOR_PATH: VALIDATOR_SOURCE.read_bytes(),
                    FINALIZER_PATH: FINALIZER_SOURCE.read_bytes(),
                },
            )
            agent = build_lead_agent(backend, model)
            result = agent.invoke(
                {"messages": [{"role": "user", "content": build_prompt(topic)}]},
                config={"recursion_limit": 1000},
            )
            elapsed = time.monotonic() - start
            if not isinstance(result, dict) or not isinstance(result.get("messages"), list):
                raise RuntimeError("lead agent returned no message history")
            report_path = save_outputs(
                backend,
                topic,
                result["messages"],
                elapsed,
                str(model_name),
            )
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"Report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(" ".join(sys.argv[1:])))
