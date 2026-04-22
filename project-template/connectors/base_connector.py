from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    @abstractmethod
    def search(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch(self, url: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
