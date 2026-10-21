from datetime import datetime

from pydantic import BaseModel

from llm_engineering.registry.keys import subscription_key


class Subscription(BaseModel):
    """User ↔ source link. Many users can subscribe to one source; it is still crawled once."""

    user_id: str
    source_id: str
    created_at: datetime

    @property
    def id(self) -> str:
        return subscription_key(self.user_id, self.source_id)
