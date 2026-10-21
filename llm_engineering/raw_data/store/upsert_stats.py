from dataclasses import dataclass


@dataclass
class UpsertStats:
    inserted: int = 0
    matched: int = 0  # already stored; content refreshed, topics/provenance merged

    def __iadd__(self, other: "UpsertStats") -> "UpsertStats":
        self.inserted += other.inserted
        self.matched += other.matched
        return self
