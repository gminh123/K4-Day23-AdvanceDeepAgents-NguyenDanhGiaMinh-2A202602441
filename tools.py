"""tools.py - STUDENT IMPLEMENTS.  Source tools for the research agents.   Guide: GUIDE.md, part 1.

Rules for every tool:
  * runs on the HOST (not in the sandbox): API keys must never enter the sandbox;
  * returns a STRING (JSON text of compact records) and NEVER raises:
        "NO RESULTS"  when the source answers with nothing,
        "ERROR: ..."  when the source keeps failing after the retries (the agent then tries another source);
  * the docstring is the tool description the LLM reads: keep it precise (what it does, what it returns, when to use it).
Try your tools without any agent:   python tools.py
"""
import json
import os
import random
import re
import threading
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import TypeVar
from urllib.parse import quote

import httpx
from langchain_core.tools import tool

# ---- constants (given) ----
ARXIV_URL = "https://export.arxiv.org/api/query"  # https only: http answers 301
HF_DAILY_URL = "https://huggingface.co/api/daily_papers"
HF_SEARCH_URL = "https://huggingface.co/api/papers/search"
EXA_URL = "https://mcp.exa.ai/mcp"
_ARXIV_NAMESPACE = "{http://www.w3.org/2005/Atom}"
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_ARXIV_INTERVAL = 3.0
_ARXIV_LOCK = threading.Lock()
_ARXIV_LAST_REQUEST = 0.0
_Result = TypeVar("_Result")


class RetryableError(Exception):
    """Given. Raise it inside a call to ask with_retry to wait and try again (retry_after in seconds, optional)."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


# ---- TODO 1: retry helper ----
def with_retry(
    fn: Callable[[], _Result], *, attempts: int = 5, base: float = 1.0, cap: float = 30.0
) -> _Result:
    """Call fn(); when it raises RetryableError, wait and call it again.

    PSEUDO-CODE:
      for attempt in 0 .. attempts-1:
          try: return fn()
          except RetryableError as e:
              if this was the last attempt: raise
              delay = e.retry_after if the server told us, else exponential backoff base * 2**attempt
              cap the delay at `cap` seconds; add random jitter to the exponential case
              sleep(delay)
    Use it to wrap EVERY network call below. Also treat these as retryable: HTTP 429/500/502/503/504,
    httpx.TransportError (timeouts, connection resets). Read the Retry-After header when present.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if base < 0 or cap < 0:
        raise ValueError("base and cap must not be negative")

    for attempt in range(attempts):
        try:
            return fn()
        except RetryableError as exc:
            if attempt == attempts - 1:
                raise

            if exc.retry_after is not None:
                delay = min(cap, max(0.0, float(exc.retry_after)))
            else:
                delay = min(cap, base * (2**attempt))
                jitter_limit = min(base, cap - delay)
                if jitter_limit > 0:
                    delay += random.uniform(0.0, jitter_limit)
            time.sleep(delay)

    raise RuntimeError("retry loop exited unexpectedly")


def _retry_after_value(value):
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _http_get(url, *, params=None, timeout=30.0, before_request=None):
    if before_request is not None:
        before_request()
    try:
        response = httpx.get(url, params=params, timeout=timeout)
    except httpx.TransportError as exc:
        raise RetryableError(str(exc)) from exc
    if response.status_code in _RETRYABLE_STATUS_CODES:
        raise RetryableError(
            f"HTTP {response.status_code}: {response.text[:500]}",
            retry_after=_retry_after_value(response.headers.get("Retry-After")),
        )
    response.raise_for_status()
    return response


def _wait_for_arxiv_slot():
    global _ARXIV_LAST_REQUEST
    with _ARXIV_LOCK:
        elapsed = time.monotonic() - _ARXIV_LAST_REQUEST
        if elapsed < _ARXIV_INTERVAL:
            time.sleep(_ARXIV_INTERVAL - elapsed)
        _ARXIV_LAST_REQUEST = time.monotonic()


def _clean_text(value):
    return " ".join(str(value or "").split())


def _error_result(exc, secret=None):
    message = str(exc)
    if secret:
        message = message.replace(secret, "[REDACTED]")
        encoded_secret = quote(secret, safe="")
        if encoded_secret != secret:
            message = message.replace(encoded_secret, "[REDACTED]")
    return f"ERROR: {type(exc).__name__}: {message}"


def _http_json(url, *, params):
    response = _http_get(url, params=params)
    return response.json()


def _hf_records(data, *, prefer_ai_summary=False, keyword=""):
    if not isinstance(data, list):
        raise ValueError("Hugging Face API response must be a JSON list")

    records = []
    needle = keyword.casefold().strip()
    for item in data:
        if not isinstance(item, dict):
            continue
        paper = item.get("paper")
        if not isinstance(paper, dict):
            continue
        paper_id = paper.get("id")
        if not paper_id:
            continue

        title = _clean_text(paper.get("title") or item.get("title"))
        summary_value = (
            paper.get("ai_summary") or item.get("ai_summary")
            if prefer_ai_summary
            else None
        )
        summary = _clean_text(
            summary_value or item.get("summary") or paper.get("summary")
        )[:600]
        if needle and needle not in f"{title} {summary}".casefold():
            continue

        records.append(
            {
                "id": str(paper_id),
                "url": f"https://huggingface.co/papers/{paper_id}",
                "published": paper.get("publishedAt") or item.get("publishedAt"),
                "title": title,
                "summary": summary,
                "upvotes": paper.get("upvotes", 0) or 0,
                "github": paper.get("githubRepo") or item.get("githubRepo"),
                "stars": paper.get("githubStars", item.get("githubStars")),
            }
        )
    return records


def _is_rate_limited(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = re.sub(r"[^a-z]", "", str(key).casefold())
            if "rate" in normalized_key and "limit" in normalized_key and nested:
                return True
            if _is_rate_limited(nested):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_is_rate_limited(item) for item in value)
    if isinstance(value, str):
        return bool(
            re.search(
                r"rate[\s_-]*limit(?:[\s_-]*(?:has been )?(?:exceeded|reached))"
                r"|(?:exceeded|reached).{0,40}rate[\s_-]*limit"
                r"|too many requests|quota exceeded|throttl"
                r"|free tier.{0,40}(?:limit|quota)",
                value,
                re.IGNORECASE,
            )
        )
    return False


def _exa_payload(response):
    response_text = response.text
    data_lines = [
        line.lstrip()[5:].strip()
        for line in response_text.splitlines()
        if line.lstrip().startswith("data:")
    ]
    candidates = data_lines or [response_text]
    for data in candidates:
        if not data or data == "[DONE]":
            continue
        message = json.loads(data)
        if not isinstance(message, dict):
            continue
        if "error" in message:
            raise RuntimeError(f"Exa MCP error: {message['error']}")

        result = message.get("result")
        if not isinstance(result, dict):
            continue
        if _is_rate_limited(result.get("_meta")) or _is_rate_limited(
            result.get("content", [])
        ):
            raise RetryableError("Exa rate limit signaled in MCP response")
        texts = [
            part["text"]
            for part in result.get("content", [])
            if isinstance(part, dict)
            and part.get("type") == "text"
            and isinstance(part.get("text"), str)
        ]
        return "\n".join(texts).strip()
    return ""


def _exa_call(name, arguments, api_key):
    endpoint = EXA_URL
    if api_key:
        endpoint = f"{endpoint}?exaApiKey={quote(api_key, safe='')}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }

    def request():
        try:
            response = httpx.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                timeout=60.0,
            )
        except httpx.TransportError as exc:
            raise RetryableError(str(exc)) from exc
        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise RetryableError(
                f"HTTP {response.status_code}: {response.text[:500]}",
                retry_after=_retry_after_value(response.headers.get("Retry-After")),
            )
        response.raise_for_status()
        result = _exa_payload(response)
        if _is_rate_limited(result):
            raise RetryableError("Exa rate limit signaled in MCP response")
        return result

    return with_retry(request, attempts=8, base=2.0, cap=60.0)


# ---- TODO 2: arXiv ----
@tool
def arxiv_search(query: str, max_results: int = 10) -> str:
    """Search arXiv papers by keywords, newest first. Returns a JSON list of {id, url, published, title, summary}."""
    try:
        terms = [
            term
            for term in re.findall(r"(?:[^\W_]|-)+", query, flags=re.UNICODE)
            if term.casefold() not in {"and", "or"} and re.search(r"[^\W_]", term)
        ]
        if not terms:
            return "NO RESULTS"

        params = {
            "search_query": " AND ".join(f"all:{term}" for term in terms),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max(1, min(30, int(max_results))),
            "start": 0,
        }
        response = with_retry(
            lambda: _http_get(
                ARXIV_URL,
                params=params,
                before_request=_wait_for_arxiv_slot,
            ),
            attempts=8,
            base=2.0,
            cap=60.0,
        )
        root = ET.fromstring(response.text)
        records = []
        for entry in root.findall(f"{_ARXIV_NAMESPACE}entry"):
            raw_id = entry.findtext(f"{_ARXIV_NAMESPACE}id", default="").strip()
            paper_id = raw_id.rsplit("/abs/", 1)[-1]
            paper_id = re.sub(r"v\d+$", "", paper_id)
            if not paper_id:
                continue
            published = entry.findtext(
                f"{_ARXIV_NAMESPACE}published", default=""
            ).strip()
            records.append(
                {
                    "id": paper_id,
                    "url": f"https://arxiv.org/abs/{paper_id}",
                    "published": published[:10],
                    "title": _clean_text(
                        entry.findtext(f"{_ARXIV_NAMESPACE}title", default="")
                    ),
                    "summary": _clean_text(
                        entry.findtext(f"{_ARXIV_NAMESPACE}summary", default="")
                    )[:600],
                }
            )
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return _error_result(exc)


# ---- TODO 3: Hugging Face ----
@tool
def hf_daily_papers(limit: int = 30, date: str = "", keyword: str = "") -> str:
    """Hugging Face Daily Papers = what is trending in AI research. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars} sorted by upvotes. `date` is YYYY-MM-DD (empty = latest).
    `keyword` filters title/summary; there is no topic search on this endpoint (use hf_search_papers for a topic)."""
    try:
        params = {"limit": max(1, min(100, int(limit)))}
        if date:
            params["date"] = date
        data = with_retry(lambda: _http_json(HF_DAILY_URL, params=params))
        records = _hf_records(data, keyword=keyword)
        records.sort(key=lambda record: int(record["upvotes"] or 0), reverse=True)
        return json.dumps(records, ensure_ascii=False) if records else "NO RESULTS"
    except Exception as exc:
        return _error_result(exc)


@tool
def hf_search_papers(query: str, limit: int = 10) -> str:
    """Search Hugging Face papers by topic. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars}."""
    try:
        params = {"q": query, "limit": max(1, min(50, int(limit)))}
        data = with_retry(lambda: _http_json(HF_SEARCH_URL, params=params))
        records = _hf_records(data, prefer_ai_summary=True)
        return json.dumps(records, ensure_ascii=False) if records else "NO RESULTS"
    except Exception as exc:
        return _error_result(exc)


# ---- TODO 4: web search / fetch through the Exa MCP endpoint ----
@tool
def web_search(query: str, objective: str = "", num_results: int = 5) -> str:
    """Search the web (Exa). Describe the ideal page in natural language. Returns clean text of the top results with URLs."""
    api_key = os.getenv("EXA_API_KEY", "")
    try:
        actual_objective = objective.strip() or f"Find useful, reliable webpages about: {query}"
        arguments = {
            "query": query,
            "objective": actual_objective,
            "numResults": max(1, min(10, int(num_results))),
        }
        result = _exa_call("web_search_exa", arguments, api_key)
        return result or "NO RESULTS"
    except Exception as exc:
        return _error_result(exc, api_key)


@tool
def web_fetch(url: str) -> str:
    """Read the full content of one web page (e.g. an arXiv abstract page) as markdown. Long pages are truncated."""
    api_key = os.getenv("EXA_API_KEY", "")
    try:
        result = _exa_call("web_fetch_exa", {"urls": [url]}, api_key)
        return result[:12000] if result else "NO RESULTS"
    except Exception as exc:
        return _error_result(exc, api_key)


# ---- TODO 5: registry (the researcher subagent gets exactly these) ----
SOURCE_TOOLS = [arxiv_search, hf_daily_papers, hf_search_papers, web_search, web_fetch]


if __name__ == "__main__":
    for name, fn, args in [
        ("arxiv_search", arxiv_search, {"query": "world model", "max_results": 3}),
        ("hf_daily_papers", hf_daily_papers, {"limit": 20}),
        ("hf_search_papers", hf_search_papers, {"query": "world model", "limit": 3}),
        ("web_search", web_search, {"query": "survey paper on world models", "num_results": 2}),
        ("web_fetch", web_fetch, {"url": "https://arxiv.org/abs/1803.10122"}),
    ]:
        try:
            print(f"== {name}\n{fn.invoke(args)[:400]}\n")
        except NotImplementedError as exc:
            print(f"== {name}: not implemented yet ({exc})\n")
