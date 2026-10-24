#!/usr/bin/env python3
import json
import random
from datetime import UTC, datetime


def generate_payments(n=10):
    payments = []
    for _ in range(n):
        payments.append(
            {
                "payment_id": f"pay-{random.randint(10000, 99999)}",
                "order_id": f"ord-{random.randint(10000, 99999)}",
                "amount": round(random.uniform(5.0, 300.0), 2),
                "currency": "USD",
                "status": "SUCCESS",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
    return payments


if __name__ == "__main__":
    print(json.dumps(generate_payments(5), indent=2))
