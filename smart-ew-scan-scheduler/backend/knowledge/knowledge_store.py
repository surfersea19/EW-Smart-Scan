"""Local JSON storage for persistent, evidence-only band knowledge."""

import json
from pathlib import Path
from typing import Optional, Union

from pydantic import ValidationError

from .knowledge_schema import PersistentKnowledge


class PersistentKnowledgeStore:
    """Read and write one versioned persistent-knowledge JSON document."""

    _FILENAME = "persistent_knowledge.json"

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        self._data_dir = (
            Path(data_dir) if data_dir is not None else Path(__file__).parent / "data"
        )
        self._path = self._data_dir / self._FILENAME

    def save(self, knowledge: PersistentKnowledge) -> None:
        """Persist validated knowledge as readable UTF-8 JSON."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as knowledge_file:
            json.dump(knowledge.model_dump(mode="json"), knowledge_file, indent=2)
            knowledge_file.write("\n")

    def load(self) -> Optional[PersistentKnowledge]:
        """Load and validate persisted knowledge, if it exists."""
        if not self._path.exists():
            return None

        try:
            with self._path.open("r", encoding="utf-8") as knowledge_file:
                data = json.load(knowledge_file)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Persistent knowledge file contains invalid JSON: {self._path}"
            ) from error

        try:
            return PersistentKnowledge.model_validate(data)
        except ValidationError as error:
            raise ValueError(
                f"Persistent knowledge file does not match the required schema: {self._path}"
            ) from error

    def clear(self) -> None:
        """Remove persisted knowledge when it is present."""
        if self._path.exists():
            self._path.unlink()

    def exists(self) -> bool:
        """Return whether the persistent knowledge file exists."""
        return self._path.exists()
