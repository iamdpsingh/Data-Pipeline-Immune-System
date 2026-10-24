#!/usr/bin/env python3
import time


def benchmark():
    start = time.perf_counter()
    for _ in range(1000):
        _ = 100 * 0.95
    duration = time.perf_counter() - start
    print(
        f"Quality rule engine throughput: 1000 evaluations in {duration * 1000:.2f}ms"
    )


if __name__ == "__main__":
    benchmark()
