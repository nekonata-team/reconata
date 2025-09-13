from dataclasses import dataclass


@dataclass
class RecordingMetrics:
    files: int
    queue_size: int
    queue_max: int
    bytes_total: int
    last_packet: float
    closed: bool
