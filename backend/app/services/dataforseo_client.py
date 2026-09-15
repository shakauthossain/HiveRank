"""DataForSEO v3 REST client.

Calls https://api.dataforseo.com/v3 with HTTP Basic Auth. That is the official
API — there is no Bearer API-key scheme. Use the API Access login and generated
API password from https://app.dataforseo.com/api-access, not the website
account password. We never log into the dashboard.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

API_BASE = "https://api.dataforseo.com/v3"


class DataForSeoError(RuntimeError):
    pass


def _credentials() -> tuple[str, str]:
    login = (
        os.getenv("DATAFORSEO_API_LOGIN")
        or os.getenv("DATAFORSEO_LOGIN")
        or ""
    ).strip()
    password = (
        os.getenv("DATAFORSEO_API_PASSWORD")
        or os.getenv("DATAFORSEO_PASSWORD")
        or ""
    ).strip()
    if not login or not password:
        raise DataForSeoError(
            "Set DATAFORSEO_API_LOGIN and DATAFORSEO_API_PASSWORD from "
            "https://app.dataforseo.com/api-access (API password, not the website password)."
        )
    return login, password


def first_result(payload: dict) -> Optional[dict]:
    results = all_results(payload)
    return results[0] if results else None


def all_results(payload: dict) -> list:
    tasks = payload.get("tasks") or []
    if not tasks:
        return []
    results = tasks[0].get("result") or []
    return results if isinstance(results, list) else []


def task_ok(payload: dict) -> bool:
    if (payload.get("status_code") or 0) >= 40000:
        return False
    tasks = payload.get("tasks") or []
    if not tasks:
        return False
    return (tasks[0].get("status_code") or 0) < 40000


class DataForSeoClient:
    def __init__(self, client: httpx.AsyncClient):
        self._http = client
        self.usage: list[dict[str, Any]] = []
        self.total_cost = 0.0

    @classmethod
    def from_env(cls, client: httpx.AsyncClient) -> "DataForSeoClient":
        _credentials()
        return cls(client)

    async def get(self, path: str, timeout: float = 30.0) -> dict:
        login, password = _credentials()
        url = f"{API_BASE}/{path.lstrip('/')}"
        try:
            response = await self._http.get(
                url, auth=(login, password), timeout=timeout
            )
        except httpx.HTTPError as exc:
            raise DataForSeoError(f"{path} request failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise DataForSeoError(f"{path} returned non-JSON") from exc
        if response.status_code >= 400:
            raise DataForSeoError(
                f"{path} HTTP {response.status_code}: {data.get('status_message') or response.text[:200]}"
            )
        return data

    async def user_data(self) -> dict:
        """Cheap credential check: remaining prepaid balance, no crawl."""
        return await self.get("appendix/user_data")

    async def lighthouse_live(
        self,
        url: str,
        *,
        for_mobile: bool = True,
        categories: Optional[list] = None,
        timeout: float = 90.0,
    ) -> dict:
        """Live Lighthouse JSON (~$0.005). Returns PSI-shaped {lighthouseResult: ...}."""
        task: dict[str, Any] = {
            "url": url,
            "for_mobile": bool(for_mobile),
            "categories": categories or ["performance"],
        }
        payload = await self.post(
            "on_page/lighthouse/live/json",
            [task],
            timeout=timeout,
        )
        result = first_result(payload)
        if not isinstance(result, dict) or not result.get("categories"):
            raise DataForSeoError(
                f"lighthouse/live/json returned no categories for {url} "
                f"({'mobile' if for_mobile else 'desktop'})"
            )
        # Match Google PageSpeed Insights envelope so extract_psi() works unchanged.
        return {"lighthouseResult": result, "id": url}

    async def post(self, path: str, payload: list, timeout: float = 120.0) -> dict:
        login, password = _credentials()
        url = f"{API_BASE}/{path.lstrip('/')}"
        try:
            response = await self._http.post(
                url,
                json=payload,
                auth=(login, password),
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            self.usage.append(
                {"endpoint": path, "cost": 0, "ok": False, "error": str(exc)}
            )
            raise DataForSeoError(f"{path} request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            self.usage.append(
                {
                    "endpoint": path,
                    "cost": 0,
                    "ok": False,
                    "error": f"HTTP {response.status_code}",
                }
            )
            raise DataForSeoError(f"{path} returned non-JSON") from exc

        cost = float(data.get("cost") or 0)
        self.total_cost += cost
        ok = response.status_code < 400 and task_ok(data)
        entry = {
            "endpoint": path,
            "cost": round(cost, 6),
            "ok": ok,
            "http_status": response.status_code,
            "status_code": data.get("status_code"),
            "status_message": data.get("status_message"),
        }
        if not ok:
            tasks = data.get("tasks") or []
            if tasks:
                entry["task_message"] = tasks[0].get("status_message")
            elif response.text:
                entry["error"] = response.text[:300]
        self.usage.append(entry)
        if response.status_code >= 400:
            raise DataForSeoError(
                f"{path} HTTP {response.status_code}: {data.get('status_message') or response.text[:200]}"
            )
        return data

    async def domain_rank_overview(
        self,
        domain: str,
        location_code: Optional[int] = None,
        language_code: Optional[str] = None,
    ) -> dict:
        """Omit location/language to pull every Labs market, then we sum traffic."""
        task: dict[str, Any] = {"target": domain, "limit": 1000}
        if location_code:
            task["location_code"] = location_code
        if language_code:
            task["language_code"] = language_code
        return await self.post(
            "dataforseo_labs/google/domain_rank_overview/live",
            [task],
        )

    async def ranked_keywords(
        self, domain: str, location_code: int, language_code: str, limit: int = 20
    ) -> dict:
        return await self.post(
            "dataforseo_labs/google/ranked_keywords/live",
            [
                {
                    "target": domain,
                    "location_code": location_code,
                    "language_code": language_code,
                    "limit": limit,
                    "filters": [
                        ["ranked_serp_element.serp_item.rank_group", ">=", 4],
                        "and",
                        ["ranked_serp_element.serp_item.rank_group", "<=", 15],
                    ],
                    "order_by": ["keyword_data.keyword_info.search_volume,desc"],
                    "item_types": ["organic"],
                }
            ],
        )

    async def ranked_keywords_by_traffic(
        self, domain: str, location_code: int, language_code: str, limit: int = 10
    ) -> dict:
        return await self.post(
            "dataforseo_labs/google/ranked_keywords/live",
            [
                {
                    "target": domain,
                    "location_code": location_code,
                    "language_code": language_code,
                    "limit": limit,
                    "order_by": ["ranked_serp_element.serp_item.etv,desc"],
                    "item_types": ["organic"],
                }
            ],
        )

    async def competitors_domain(
        self, domain: str, location_code: int, language_code: str, limit: int = 5
    ) -> dict:
        return await self.post(
            "dataforseo_labs/google/competitors_domain/live",
            [
                {
                    "target": domain,
                    "location_code": location_code,
                    "language_code": language_code,
                    "limit": limit,
                    "item_types": ["organic"],
                }
            ],
        )

    async def domain_intersection(
        self,
        domain_a: str,
        domain_b: str,
        location_code: int,
        language_code: str,
        intersections: bool,
        limit: int = 15,
    ) -> dict:
        return await self.post(
            "dataforseo_labs/google/domain_intersection/live",
            [
                {
                    "targets": {"1": domain_a, "2": domain_b},
                    "location_code": location_code,
                    "language_code": language_code,
                    "intersections": intersections,
                    "limit": limit,
                    "item_types": ["organic"],
                    "order_by": ["keyword_data.keyword_info.search_volume,desc"],
                }
            ],
        )

    async def backlinks_summary(self, domain: str) -> dict:
        return await self.post(
            "backlinks/summary/live",
            [
                {
                    "target": domain,
                    "internal_list_limit": 1,
                    "backlinks_status_type": "live",
                    "include_subdomains": True,
                    "rank_scale": "one_hundred",
                }
            ],
        )

    async def referring_domains(self, domain: str, limit: int = 8) -> dict:
        return await self.post(
            "backlinks/referring_domains/live",
            [
                {
                    "target": domain,
                    "limit": limit,
                    "order_by": ["rank,desc"],
                }
            ],
        )

    async def bulk_ranks(self, domains: list[str]) -> dict:
        targets = [d for d in domains if d][:20]
        if not targets:
            return {"tasks": [{"result": []}]}
        return await self.post(
            "backlinks/bulk_ranks/live",
            [{"targets": targets, "rank_scale": "one_hundred"}],
        )

    async def onpage_task_post(self, target_url: str, max_pages: int = 100) -> dict:
        return await self.post(
            "on_page/task_post",
            [
                {
                    "target": target_url,
                    "max_crawl_pages": max_pages,
                    "load_resources": False,
                    "enable_javascript": False,
                    "enable_browser_rendering": False,
                    "store_raw_html": False,
                    "allow_subdomains": False,
                }
            ],
            timeout=60.0,
        )

    async def onpage_summary(self, task_id: str) -> dict:
        """OnPage summary is GET /on_page/summary/{id} — not POST."""
        path = f"on_page/summary/{task_id}"
        data = await self.get(path, timeout=60.0)
        cost = float(data.get("cost") or 0)
        self.total_cost += cost
        self.usage.append(
            {
                "endpoint": path,
                "cost": round(cost, 6),
                "ok": task_ok(data),
                "http_status": 200,
                "status_code": data.get("status_code"),
                "status_message": data.get("status_message"),
            }
        )
        return data

    async def onpage_pages(self, task_id: str, limit: int = 10) -> dict:
        return await self.post(
            "on_page/pages",
            [
                {
                    "id": task_id,
                    "limit": limit,
                    "order_by": ["onpage_score,asc"],
                    "filters": ["resource_type", "=", "html"],
                }
            ],
        )
