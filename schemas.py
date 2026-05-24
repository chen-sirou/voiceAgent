from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime


@dataclass
class VisitorRegistration:
    plate_number: Optional[str] = None
    target_company: Optional[str] = None
    phone: Optional[str] = None
    visit_reason: Optional[str] = None
    entry_time: Optional[str] = None

    confirmed: bool = False

    def required_complete(self) -> bool:
        return all([
            self.plate_number,
            self.target_company,
            self.phone,
            self.visit_reason,
        ])

    def ready_to_save(self) -> bool:
        return self.required_complete() and self.confirmed

    def fill_entry_time(self):
        if not self.entry_time:
            self.entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("confirmed", None)
        return data


@dataclass
class ConversationState:
    turn_count: int = 0
    silence_count: int = 0
    correction_count: int = 0
    last_agent_question: Optional[str] = None
    waiting_for_confirmation: bool = False
    finished: bool = False
    history: list = field(default_factory=list)