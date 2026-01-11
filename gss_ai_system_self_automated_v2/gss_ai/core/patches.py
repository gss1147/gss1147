from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
import uuid

@dataclass(frozen=True)
class PatchProposal:
    """A *proposal* to modify code/config, never auto-applied by default."""
    target_relpath: str
    unified_diff: str
    rationale: str
    created_ts: float = time.time()
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", uuid.uuid4().hex)

def write_patch(state_dir: Path, proposal: PatchProposal) -> Path:
    patches_dir = state_dir / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    out = patches_dir / f"{proposal.created_ts:.0f}_{proposal.id}_{Path(proposal.target_relpath).name}.diff"
    out.write_text(proposal.unified_diff, encoding="utf-8")
    meta = patches_dir / f"{proposal.created_ts:.0f}_{proposal.id}.json"
    meta.write_text(
        __import__("json").dumps(
            {
                "id": proposal.id,
                "target_relpath": proposal.target_relpath,
                "rationale": proposal.rationale,
                "created_ts": proposal.created_ts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return out
