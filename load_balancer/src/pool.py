import time
from dataclasses import dataclass, field
from enum import Enum


class ServerStatus(Enum):
    HEALTHY = 'healthy'
    UNHEALTHY = 'unhealthy'
    DRAINING = 'draining'


@dataclass(unsafe_hash=True)
class BackendServer:
    host: str
    port: int
    weight: int = 1
    status: ServerStatus = ServerStatus.HEALTHY
    active_connections: int = 0
    consecutive_failures: int = 0
    last_check: float = field(default_factory=time.monotonic)

    @property
    def address(self) -> str:
        return f'http://{self.host}:{self.port}'

    @property
    def is_healthy(self) -> bool:
        return self.status == ServerStatus.HEALTHY

    def mark_failure(self, threshold: int = 3) -> None:
        self.consecutive_failures += 1
        self.last_check = time.monotonic()
        if self.consecutive_failures >= threshold:
            self.status = ServerStatus.UNHEALTHY

    def mark_success(self, recovery_threshold: int = 1) -> None:
        self.consecutive_failures = 0
        self.last_check = time.monotonic()
        self.status = ServerStatus.HEALTHY
