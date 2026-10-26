from typing import Any

from features.autonomous_worker.domain.models import Phase, Task


class DAGResolver:
    @staticmethod
    def validate_and_order(phases: list[Phase]) -> tuple[bool, list[str], list[str]]:
        task_map: dict[str, Task] = {}
        for phase in phases:
            for task in phase.tasks:
                task_map[task.id] = task

        in_degree: dict[str, int] = {tid: 0 for tid in task_map}
        adj: dict[str, list[str]] = {tid: [] for tid in task_map}

        errors: list[str] = []
        for tid, task in task_map.items():
            for dep in task.depends_on:
                if dep not in task_map:
                    errors.append(f"Task «{task.title}» ({tid}) dipende da id sconosciuto «{dep}»")
                else:
                    adj[dep].append(tid)
                    in_degree[tid] += 1

        if errors:
            return False, [], errors

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        ordered: list[str] = []

        while queue:
            curr = queue.pop(0)
            ordered.append(curr)
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(task_map):
            cycle_tasks = [tid for tid, deg in in_degree.items() if deg > 0]
            return False, [], [f"Rilevato ciclo di dipendenze (deadlock) tra i task: {', '.join(cycle_tasks)}"]

        return True, ordered, []

    @staticmethod
    def get_parallel_ready(phases: list[Phase], done_task_ids: set[str], running_task_ids: set[str]) -> list[Task]:
        ready: list[Task] = []
        for phase in phases:
            for task in phase.tasks:
                if task.id in done_task_ids or task.id in running_task_ids:
                    continue
                if all(dep in done_task_ids for dep in task.depends_on):
                    ready.append(task)
        return ready

    @staticmethod
    def export_graph_data(phases: list[Phase]) -> dict[str, Any]:
        nodes = []
        edges = []
        for phase in phases:
            for task in phase.tasks:
                nodes.append({
                    "id": task.id,
                    "phase_id": phase.id,
                    "title": task.title,
                    "role": task.specialist_role,
                    "status": task.status.value if hasattr(task.status, "value") else str(task.status),
                    "round": getattr(task, "round", 1),
                })
                for dep in task.depends_on:
                    edges.append({"from": dep, "to": task.id})
        return {"nodes": nodes, "edges": edges, "count": len(nodes)}


dag_resolver = DAGResolver()
