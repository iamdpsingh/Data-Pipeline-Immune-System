#!/usr/bin/env python3
import json
import random
from datetime import datetime

def generate_orders(n=50):
    orders = []
    for i in range(n):
        orders.append({
            "order_id": f"ord-{random.randint(10000, 99999)}",
            "customer_id": f"cust-{random.randint(100, 999)}",
            "amount": round(random.uniform(10.0, 500.0), 2),
            "status": "COMPLETED",
            "timestamp": datetime.utcnow().isoformat()
        })
    return orders

if __name__ == "__main__":
    print(json.dumps(generate_orders(5), indent=2))
