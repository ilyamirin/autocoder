from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AreaPolicy:
    instructions: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentPolicy:
    global_instructions: tuple[str, ...]
    area_policies: dict[str, AreaPolicy]

    def instructions_for_area(self, area: str) -> tuple[str, ...]:
        area_policy = self.area_policies.get(area)
        if not area_policy:
            return self.global_instructions
        return self.global_instructions + area_policy.instructions

    def metadata_for_area(self, area: str) -> dict[str, str]:
        area_policy = self.area_policies.get(area)
        if not area_policy:
            return {}
        return dict(area_policy.metadata)


def load_agent_policy(policy_path: Path) -> AgentPolicy:
    if not policy_path.exists():
        raise FileNotFoundError(f"Agent policy file is missing: {policy_path}")

    current_section: tuple[str, str | None] | None = None
    global_instructions: list[str] = []
    area_data: dict[str, dict[str, list[str] | dict[str, str]]] = {}

    for raw_line in policy_path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            continue
        if line == "## Global":
            current_section = ("global", None)
            continue
        if line.startswith("## Area:"):
            area_name = line.split(":", 1)[1].strip()
            current_section = ("area", area_name)
            area_data.setdefault(area_name, {"instructions": [], "metadata": {}})
            continue
        if not line.startswith("- ") or current_section is None:
            continue

        payload = line[2:]
        if ":" not in payload:
            continue
        key, value = payload.split(":", 1)
        key = key.strip()
        value = value.strip()

        if current_section[0] == "global":
            if key == "instruction":
                global_instructions.append(value)
            continue

        area_name = current_section[1]
        if area_name is None:
            continue
        area_bucket = area_data[area_name]
        if key == "instruction":
            instructions = area_bucket["instructions"]
            assert isinstance(instructions, list)
            instructions.append(value)
        else:
            metadata = area_bucket["metadata"]
            assert isinstance(metadata, dict)
            metadata[key] = value

    area_policies = {
        area_name: AreaPolicy(
            instructions=tuple(data["instructions"]),  # type: ignore[arg-type]
            metadata=dict(data["metadata"]),  # type: ignore[arg-type]
        )
        for area_name, data in area_data.items()
    }
    return AgentPolicy(
        global_instructions=tuple(global_instructions),
        area_policies=area_policies,
    )
