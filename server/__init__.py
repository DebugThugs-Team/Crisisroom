"""Crisis Room environment server components."""

__all__ = []

# Keep package import lightweight for environments without openenv-core installed.
# The spec-compliant implementation used by `server.server` lives in `server.environment`.
try:  # pragma: no cover
    from .crisis_room_environment import CrisisRoomEnvironment as OpenEnvCrisisRoomEnvironment  # type: ignore

    __all__.append("OpenEnvCrisisRoomEnvironment")
except Exception:
    pass
