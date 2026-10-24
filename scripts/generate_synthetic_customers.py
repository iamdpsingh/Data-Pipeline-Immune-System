#!/usr/bin/env python3
import json
import random
from datetime import datetime

def generate_customers(n=10):
    customers = []
    for i in range(n):
        customers.append({
            "customer_id": f"cust-{random.randint(100, 999)}",
            "email": f"user{i}@example.com",
            "country": random.choice(["US", "DE", "IN", "GB"]),
            "tier": random.choice(["STANDARD", "PREMIUM"]),
            "signup_timestamp": datetime.utcnow().isoformat()
        })
    return customers

if __name__ == "__main__":
    print(json.dumps(generate_customers(5), indent=2))
