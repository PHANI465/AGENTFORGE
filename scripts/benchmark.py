"""Benchmarks the live API Gateway — real HTTP calls, real Postgres, real LLM
calls (BYOK, gpt-4o-mini). Run against `docker compose up -d` with a real
OPENAI_API_KEY. Numbers get pasted into docs/benchmarks.md, not asserted on —
this is a manual instrument, not a CI gate (LLM latency is provider-dependent
and not something a portfolio project should pretend to guarantee).

Usage:
    uv run python scripts/benchmark.py
"""

import argparse
import statistics
import time

import httpx

BASE_URL = "http://localhost:8000"


def percentile(values: list[float], pct: float) -> float:
    values = sorted(values)
    idx = min(int(len(values) * pct), len(values) - 1)
    return values[idx]


def report(name: str, latencies_ms: list[float]) -> None:
    print(f"\n{name}  (n={len(latencies_ms)})")
    print(f"  mean: {statistics.mean(latencies_ms):.1f}ms")
    print(f"  p50:  {percentile(latencies_ms, 0.50):.1f}ms")
    print(f"  p95:  {percentile(latencies_ms, 0.95):.1f}ms")
    print(f"  min:  {min(latencies_ms):.1f}ms  max: {max(latencies_ms):.1f}ms")


def timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--agent-id", required=True, help="A tool-free agent, e.g. curl-test-agent")
    args = parser.parse_args()

    headers = {"X-API-Key": args.api_key}

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        health_latencies = [timed(lambda: client.get("/health").raise_for_status()) for _ in range(20)]
        report("GET /health (no auth, no DB)", health_latencies)

        list_latencies = [
            timed(lambda: client.get("/api/v1/agents?limit=10").raise_for_status()) for _ in range(20)
        ]
        report("GET /api/v1/agents (Postgres round-trip)", list_latencies)

        cold_latencies = []
        for i in range(5):
            prompt = f"Say the number {i} and nothing else. [bench-{time.time_ns()}]"
            cold_latencies.append(
                timed(
                    lambda p=prompt: client.post(
                        f"/api/v1/agents/{args.agent_id}/run", json={"input": p}
                    ).raise_for_status()
                )
            )
        report("POST .../run — cold (unique input, cache miss, real LLM call)", cold_latencies)

        repeated_prompt = "Say the word 'benchmark' and nothing else."
        repeat_latencies = []
        for _ in range(3):
            repeat_latencies.append(
                timed(
                    lambda: client.post(
                        f"/api/v1/agents/{args.agent_id}/run", json={"input": repeated_prompt}
                    ).raise_for_status()
                )
            )
        print(f"\nPOST .../run — same input x3 (1st = cache miss, 2nd/3rd = cache hit)")
        for i, ms in enumerate(repeat_latencies):
            label = "miss" if i == 0 else "hit"
            print(f"  call {i + 1} ({label}): {ms:.1f}ms")
        if len(repeat_latencies) > 1:
            speedup = repeat_latencies[0] / statistics.mean(repeat_latencies[1:])
            print(f"  cache speedup: {speedup:.1f}x")


if __name__ == "__main__":
    main()
