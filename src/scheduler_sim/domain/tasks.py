from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class ValidationResult:
    is_ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TaskGraph:
    nodes: list[str]
    edges: list[tuple[str, str]] = field(default_factory=list)

    def validate(self) -> ValidationResult:
        node_set = set(self.nodes)
        errors: list[str] = []

        for source, target in self.edges:
            if source not in node_set:
                errors.append(f"edge source '{source}' is not a declared node")
            if target not in node_set:
                errors.append(f"edge target '{target}' is not a declared node")

        if errors:
            return ValidationResult(is_ok=False, errors=errors)

        inbound_count = {node: 0 for node in self.nodes}
        adjacency: dict[str, list[str]] = {node: [] for node in self.nodes}
        for source, target in self.edges:
            adjacency[source].append(target)
            inbound_count[target] += 1

        ready = deque(node for node, count in inbound_count.items() if count == 0)
        visited_count = 0

        while ready:
            node = ready.popleft()
            visited_count += 1
            for target in adjacency[node]:
                inbound_count[target] -= 1
                if inbound_count[target] == 0:
                    ready.append(target)

        if visited_count != len(self.nodes):
            errors.append("task graph contains a cycle")

        return ValidationResult(is_ok=not errors, errors=errors)
