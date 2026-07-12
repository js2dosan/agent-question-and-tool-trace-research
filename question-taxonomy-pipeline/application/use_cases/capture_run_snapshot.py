"""Application use case for capturing and saving run snapshots."""

from application.ports.artifact_store import ArtifactStore, RunSnapshotRequest


def capture_run_snapshot(store: ArtifactStore, request: RunSnapshotRequest) -> None:
    """
    Capture and persist a snapshot of the experiment run.

    Args:
        store: Artifact store implementation for persisting the snapshot
        request: Snapshot request containing all run metadata and configuration
    """
    store.save_run_snapshot(request)
