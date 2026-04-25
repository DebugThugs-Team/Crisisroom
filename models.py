from openenv.core.env_server.types import Action, Observation
from pydantic import Field
from typing import Dict, List, Optional


class IncidentAction(Action):
    action_type: str = Field(
        ...,
        description=(
            "One of: check_logs, run_diagnostic, restart_service, "
            "rollback_deployment, scale_up, notify_team, escalate, mark_resolved"
        )
    )
    target: str = Field(
        default="",
        description="Service name, diagnostic type, or message text depending on action_type"
    )
    params: Optional[Dict] = Field(
        default=None,
        description="Extra params — e.g. {'version': 'v1.2.3'} for rollback, {'instances': 3} for scale_up"
    )


class IncidentObservation(Observation):
    step: int = Field(default=0)
    max_steps: int = Field(default=10)
    message: str = Field(default="")
    difficulty: Optional[str] = Field(default=None)
    episode_id: Optional[str] = Field(default=None)

                           
    active_alerts: Optional[List[str]] = Field(default=None, description="Current firing alerts")
    service_status: Optional[Dict[str, str]] = Field(default=None, description="Status of each service: healthy/degraded/down")
    log_output: Optional[str] = Field(default=None, description="Output from last check_logs or run_diagnostic action")
    actions_taken: Optional[List[str]] = Field(default=None, description="Actions the agent has taken so far")

                                               
    root_cause_found: Optional[bool] = Field(default=False)
    services_restored: Optional[int] = Field(default=0)
    total_services_affected: Optional[int] = Field(default=0)
    partial_score: Optional[float] = Field(default=None)
    steps_remaining: Optional[int] = Field(default=None)