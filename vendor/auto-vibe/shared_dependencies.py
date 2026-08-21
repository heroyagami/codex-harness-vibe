import os
from pathlib import Path


class SharedDependenciesError(ValueError):
    pass


def link_shared_node_modules(project_dir, shared_node_modules):
    project_dir = Path(project_dir).resolve()
    shared_node_modules = Path(shared_node_modules).resolve()
    local_node_modules = project_dir / "node_modules"

    if not shared_node_modules.is_dir():
        raise SharedDependenciesError(
            f"Shared node_modules directory not found: {shared_node_modules}"
        )
    if local_node_modules.exists() or local_node_modules.is_symlink():
        raise SharedDependenciesError(
            f"node_modules already exists: {local_node_modules}"
        )

    local_node_modules.mkdir()
    (local_node_modules / ".cache").mkdir()

    linked_entries = 0
    for source in shared_node_modules.iterdir():
        if source.name in {".cache", ".DS_Store"}:
            continue
        relative_source = os.path.relpath(source, start=local_node_modules)
        (local_node_modules / source.name).symlink_to(
            relative_source,
            target_is_directory=source.is_dir(),
        )
        linked_entries += 1

    if linked_entries == 0:
        raise SharedDependenciesError(
            f"Shared node_modules directory is empty: {shared_node_modules}"
        )

    relative_shared_directory = os.path.relpath(
        shared_node_modules,
        start=project_dir,
    )
    (local_node_modules / ".shared-dependencies").write_text(
        f"{relative_shared_directory}\n",
        encoding="utf-8",
    )
