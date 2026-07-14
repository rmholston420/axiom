"""SearXNG provider — async search adapter with JSON-first and HTML fallback."""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from axiom_core.settings import settings


class SearchResult:
    __slots__ = ("title", "url", "snippet")

    def __init__(self, title: str, url: str, snippet: str) -> None:
        self.title = title
        self.url = url
        self.snippet = snippet

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SearchResult title={self.title!r}>"


class _SearxHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.results: list[SearchResult] = []
        self._in_result = False
        self._in_link = False
        self._in_content = False
        self._href = ""
        self._title_parts: list[str] = []
        self._content_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        class_attr = attrs_dict.get("class") or ""

        if tag == "article" and "result" in class_attr.split():
            self._in_result = True
            self._href = ""
            self._title_parts = []
            self._content_parts = []

        if not self._in_result:
            return

        if tag == "a" and "result__url" not in class_attr:
            href = attrs_dict.get("href")
            if href and not self._href:
                self._in_link = True
                self._href = urljoin(self.base_url, href)

        if tag in {"p", "div"} and (
            "content" in class_attr or "result-content" in class_attr or "result__content" in class_attr
        ):
            self._in_content = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_link = False
        if tag in {"p", "div"}:
            self._in_content = False
        if tag == "article" and self._in_result:
            title = " ".join(" ".join(self._title_parts).split())
            snippet = " ".join(" ".join(self._content_parts).split())
            if self._href and title:
                self.results.append(SearchResult(title=title, url=self._href, snippet=snippet))
            self._in_result = False

    def handle_data(self, data: str) -> None:
        if self._in_result and self._in_link:
            self._title_parts.append(data)
        elif self._in_result and self._in_content:
            self._content_parts.append(data)


class SearxngProvider:
    """Async client for the local SearXNG instance."""

    def __init__(self) -> None:
        self._base = settings.axiom_searxng_url.rstrip("/")
        self._headers = {
            "User-Agent": "AxiomResearchBot/0.1 (+local-cli; rmholston420/axiom)",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(
        self,
        query: str,
        num_results: int | None = None,
    ) -> list[SearchResult]:
        """Run a web search and return up to *num_results* results."""
        limit = num_results or settings.axiom_max_results_per_query

        async with httpx.AsyncClient(timeout=30.0, headers=self._headers, follow_redirects=True) as client:
            json_params = {
                "q": query,
                "format": "json",
                "language": "en",
            }
            resp = await client.get(f"{self._base}/search", params=json_params)

            if resp.status_code == 403:
                html_params = {
                    "q": query,
                    "language": "en",
                }
                html_resp = await client.get(f"{self._base}/search", params=html_params)
                html_resp.raise_for_status()
                parser = _SearxHTMLParser(self._base)
                parser.feed(html_resp.text)
                return parser.results[:limit]

            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", [])[:limit]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                )
            )
        return results
