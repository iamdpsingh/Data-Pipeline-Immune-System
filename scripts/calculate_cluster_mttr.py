#!/usr/bin/env python3
def calculate_mttr(incident_durations_minutes: list[float]) -> float:
    if not incident_durations_minutes:
        return 0.0
    return sum(incident_durations_minutes) / len(incident_durations_minutes)


if __name__ == "__main__":
    sample = [0.4, 0.6, 0.5, 0.8, 0.4]
    print(f"Calculated Cluster MTTR: {calculate_mttr(sample):.2f} minutes")
