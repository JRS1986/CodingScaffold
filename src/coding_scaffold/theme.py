from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    voice: str
    palette: dict[str, str]
    layout: dict[str, str]
    motifs: list[str]
    reference_bits: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


FESTO_TN_AI = Theme(
    name="Festo TN-AI",
    voice=(
        "Second-person coding adventure with industrial precision: the user is pulled into a "
        "digital archive, guided by a small AI companion, and asked to repair corrupted setup "
        "crystals one practical task at a time. Each section should open with a cinematic beat, "
        "then land on a clear command, file, or decision."
    ),
    palette={
        "festo_blue": "#0099FF",
        "signal_blue": "#8DD1FF",
        "clean_surface": "#F7FCFF",
        "graphite": "#1F2933",
        "steel": "#7B8794",
        "success": "#21A67A",
        "warning": "#F5A623",
        "fault": "#D64545",
    },
    layout={
        "shell": "Light gray app background, white top bar, compact max-width content, generous vertical rhythm.",
        "sections": "Use timeline eras: Digital Hub, Birth of Local Models, Routing Revolution, Future Frontier.",
        "tables": "Prefer challenge lists over tables; use tables only for dense provider diagnostics.",
        "badges": "Use small state marks: blue chevron for active, hollow ring for pending, lock for gated.",
    },
    motifs=[
        "coding challenge timeline",
        "archive portal illustrations",
        "locked future levels",
        "predictive maintenance",
        "predictive quality",
        "predictive energy",
        "edge-to-cloud control",
        "shop-floor telemetry",
        "human-in-the-loop checkpoints",
        "model routing as a valve manifold",
    ],
    reference_bits=[
        "ROUTE-42 is the sanity check when The Glitch distorts model routing.",
        "Great Scott! marks a timeline-sensitive refactor gate.",
        "Protocol-droid clarity means every handoff states assumptions and next steps.",
        "This is the way: small change, fast test, clear rollback.",
    ],
)

