import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional


@dataclass
class Entry:
    value: str
    expires_at: Optional[float] = None  # absolute monotonic timestamp, None = no expiry

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.monotonic() > self.expires_at


class Store:
    def __init__(self, max_keys: int = 0):
        self._data: OrderedDict[str, Entry] = OrderedDict()
        self._max_keys = max_keys  # 0 = unlimited (no eviction)

    def _get_live(self, key: str) -> Optional[Entry]:
        """Return entry only if it exists and hasn't expired. Deletes expired keys."""
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._data[key]
            return None
        self._data.move_to_end(key)  # mark as most recently used
        return entry

    def _evict_if_needed(self) -> None:
        """Evict least-recently-used keys when over the max_keys limit."""
        if self._max_keys <= 0:
            return
        while len(self._data) > self._max_keys:
            self._data.popitem(last=False)  # remove LRU entry (front of OrderedDict)

    def set(self, key: str, value: str, ex: Optional[int] = None, px: Optional[int] = None) -> None:
        """
        SET key value [EX seconds] [PX milliseconds]
        ex and px are mutually exclusive. ex takes precedence if both provided.
        """
        expires_at = None
        if ex is not None:
            expires_at = time.monotonic() + ex
        elif px is not None:
            expires_at = time.monotonic() + px / 1000
        self._data[key] = Entry(value=str(value), expires_at=expires_at)
        self._data.move_to_end(key)  # most recently used
        self._evict_if_needed()

    def get(self, key: str) -> Optional[str]:
        entry = self._get_live(key)
        return entry.value if entry else None

    def incr(self, key: str) -> int:
        """
        Atomically increment integer value of key by 1.
        If key does not exist, treat as 0 before increment.
        Raises ValueError if existing value is not an integer string.
        Preserves existing TTL — does not reset it.
        """
        return self.incrby(key, 1)

    def incrby(self, key: str, amount: int) -> int:
        """
        Atomically increment integer value of key by amount.
        If key does not exist, treat as 0 before increment.
        Raises ValueError if existing value is not an integer string.
        Preserves existing TTL — does not reset it.
        """
        entry = self._get_live(key)
        current = 0
        expires_at = None
        if entry is not None:
            try:
                current = int(entry.value)
            except ValueError:
                raise ValueError('value is not an integer or out of range')
            expires_at = entry.expires_at
        new_val = current + amount
        self._data[key] = Entry(value=str(new_val), expires_at=expires_at)
        self._data.move_to_end(key)
        self._evict_if_needed()
        return new_val

    def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns count of keys actually deleted."""
        deleted = 0
        for key in keys:
            if self._data.pop(key, None) is not None:
                deleted += 1
        return deleted

    def exists(self, *keys: str) -> int:
        """Returns count of keys that exist (and are not expired)."""
        return sum(1 for k in keys if self._get_live(k) is not None)

    def expire(self, key: str, seconds: int, nx: bool = False) -> int:
        """
        Set TTL on an existing key.
        nx=True means only set expiry if key has NO existing expiry.
        Returns 1 if TTL set, 0 if key does not exist or nx condition not met.
        """
        entry = self._get_live(key)
        if entry is None:
            return 0
        if nx and entry.expires_at is not None:
            return 0
        entry.expires_at = time.monotonic() + seconds
        return 1

    def ttl(self, key: str) -> int:
        """Returns remaining TTL in seconds, -1 if no expiry, -2 if key missing."""
        entry = self._get_live(key)
        if entry is None:
            return -2
        if entry.expires_at is None:
            return -1
        remaining = entry.expires_at - time.monotonic()
        return max(0, int(remaining))

    def dbsize(self) -> int:
        """Return number of live keys, purging expired ones first."""
        expired = [k for k, v in self._data.items() if v.is_expired()]
        for k in expired:
            del self._data[k]
        return len(self._data)

    def flush(self) -> None:
        self._data.clear()
