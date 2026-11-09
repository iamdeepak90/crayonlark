"""Small load check for the public site (no extra tools needed).

Inside the stack (hits the web container directly, no proxy in between):
    docker compose cp scripts/loadcheck.py worker:/tmp/loadcheck.py
    docker compose exec -T worker python /tmp/loadcheck.py http://web:3000 20 30
From your laptop against the live site:
    uv run --with httpx python scripts/loadcheck.py https://crayonlark.com 20 30
args: base URL, concurrent users, seconds. Prints requests/s, latency percentiles and errors.
"""

from __future__ import annotations

import asyncio
import statistics
import sys
import time

import httpx

PATHS = ["/", "/books", "/blog", "/free-printables", "/about", "/sitemap.xml"]


async def user(client: httpx.AsyncClient, paths: list[str], until: float, out: list, errors: list) -> None:
    i = 0
    while time.monotonic() < until:
        path = paths[i % len(paths)]
        i += 1
        t = time.monotonic()
        try:
            r = await client.get(path)
            if r.status_code >= 400:
                errors.append(f"{r.status_code} {path}")
        except httpx.HTTPError as exc:
            errors.append(f"{type(exc).__name__} {path}")
        out.append(time.monotonic() - t)


async def main(base: str, users: int, seconds: int) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=30, headers={"Host": "crayonlark.com"}) as c:
        paths = list(PATHS)
        try:  # add the first book page, if any
            books = (await c.get("/api/public/books")).json().get("books", [])
            paths += [f"/books/{b['slug']}" for b in books[:3]]
        except Exception:
            pass
        times: list[float] = []
        errors: list[str] = []
        until = time.monotonic() + seconds
        await asyncio.gather(*(user(c, paths[k:] + paths[:k], until, times, errors) for k in range(users)))
    ms = sorted(t * 1000 for t in times)
    pct = lambda p: ms[min(len(ms) - 1, int(len(ms) * p))]  # noqa: E731
    print(f"{len(ms)} requests in {seconds}s = {len(ms) / seconds:.0f} req/s with {users} users")
    print(f"latency ms: p50 {statistics.median(ms):.0f}  p95 {pct(0.95):.0f}  p99 {pct(0.99):.0f}  max {ms[-1]:.0f}")
    print(f"errors: {len(errors)}" + (f" e.g. {errors[:5]}" if errors else ""))


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://web:3000"
    users = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    secs = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    asyncio.run(main(base, users, secs))
