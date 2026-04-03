from __future__ import annotations

from contextlib import suppress
from inspect import signature
from typing_extensions import Annotated

def _deps():
    try:
        from ddgs import DDGS
        return DDGS, "ddgs"
    except ImportError:
        pass

    try:
        from duckduckgo_search import DDGS
        return DDGS, "duckduckgo_search"
    except ImportError:
        raise ImportError("Please install ddgs or duckduckgo-search: pip install ddgs")


def _make_client(DDGS):
    with suppress(Exception):
        ctor = signature(DDGS)
        if "timeout" in ctor.parameters:
            return DDGS(timeout=20)
    return DDGS()


def _search_once(DDGS, query: str, max_results: int, backend: str | None) -> list[dict]:
    with _make_client(DDGS) as ddgs:
        kwargs = {"max_results": max_results}
        if backend is not None:
            kwargs["backend"] = backend
        return list(ddgs.text(query, **kwargs))


def _format_results(results: list[dict], source_name: str, backend: str | None) -> str:
    formatted = []
    for i, res in enumerate(results, start=1):
        formatted.append(
            f"{i}. {res.get('title')}\n"
            f"   Snippet: {res.get('body')}\n"
            f"   Source: {res.get('href')}"
        )

    backend_label = backend or "default"
    return f"Web Search Results ({source_name}, backend={backend_label}):\n\n" + "\n\n".join(formatted)

async def web_search(
    query: Annotated[str, "The search query to look up on the internet."],
    max_results: Annotated[int, "Maximum number of search results to return."] = 5,
) -> str:
    """Search the web for up-to-date information, news, and facts using DuckDuckGo."""
    DDGS, source_name = _deps()
    max_results = max(1, min(max_results, 10))
    attempted: list[str] = []
    backends = [None, "auto", "html", "lite"] if source_name == "duckduckgo_search" else [None]

    for backend in backends:
        try:
            results = _search_once(DDGS, query=query, max_results=max_results, backend=backend)
        except Exception as exc:
            backend_label = backend or "default"
            attempted.append(f"{backend_label}: {exc}")
            continue

        if results:
            return _format_results(results, source_name=source_name, backend=backend)

    if attempted:
        attempts = " | ".join(attempted)
        return f"ERROR performing web search for '{query}': all backends failed. {attempts}"

    return f"No results found on the web for '{query}'."
