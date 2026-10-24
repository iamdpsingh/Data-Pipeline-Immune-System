# Typed Enums and Dataclasses for Agent States
from enum import Enum


class IncidentSeverity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class RemediationActionType(str, Enum):
    RETRY_TASK = "RETRY_TASK"
    QUARANTINE_RECORD = "QUARANTINE_RECORD"
    QUARANTINE_PARTITION = "QUARANTINE_PARTITION"
    TRIGGER_BACKFILL = "TRIGGER_BACKFILL"
    HALT_PIPELINE = "HALT_PIPELINE"
