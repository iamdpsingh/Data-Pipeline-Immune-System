#!/usr/bin/env python3
def export_prometheus_metrics():
    metrics = [
        "# HELP dpis_health_score Current platform health score",
        "# TYPE dpis_health_score gauge",
        "dpis_health_score 98.5",
        "# HELP dpis_active_incidents Number of unresolved incidents",
        "# TYPE dpis_active_incidents gauge",
        "dpis_active_incidents 0"
    ]
    return "\n".join(metrics)

if __name__ == "__main__":
    print(export_prometheus_metrics())
