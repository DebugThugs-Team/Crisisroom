from uuid import uuid4
import json
import random

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from models import IncidentAction, IncidentObservation


INCIDENTS = {
    "easy": [
        {
            "id": "db-conn-pool",
            "title": "Payment service returning 500 errors",
            "root_cause": "db_connection_pool_exhausted",
            "affected_services": ["payment-service"],
            "initial_alerts": ["ALERT: payment-service HTTP 500 rate > 40% for 5 minutes"],
            "initial_status": {"payment-service": "degraded", "auth-service": "healthy", "inventory-service": "healthy"},
            "logs": {
                "payment-service": "ERROR: could not obtain connection from pool — pool size 10, waiting 30s timeout\nERROR: HikariPool-1 — Connection is not available, request timed out after 30000ms\nWARN: DB connection pool exhausted, consider increasing pool size",
                "auth-service": "INFO: all systems normal",
                "inventory-service": "INFO: all systems normal",
            },
            "diagnostics": {
                "db_connections": "Active: 10/10 (pool full). Waiting queue: 47 requests. Oldest wait: 28s.",
                "cpu": "payment-service CPU: 12%. DB server CPU: 78%.",
                "memory": "All services within normal memory bounds.",
            },
            "fix_action": "restart_service",
            "fix_target": "payment-service",
            "fix_hint": "Restarting the service will flush the connection pool.",
        },
        {
            "id": "cert-expiry",
            "title": "API gateway returning SSL errors",
            "root_cause": "ssl_certificate_expired",
            "affected_services": ["api-gateway"],
            "initial_alerts": ["ALERT: api-gateway SSL handshake failures > 95%"],
            "initial_status": {"api-gateway": "down", "backend-service": "healthy"},
            "logs": {
                "api-gateway": "ERROR: SSL certificate has expired — notAfter=Apr 20 00:00:00 2026 GMT\nERROR: unable to verify the first certificate\nWARN: certificate expiry was flagged 7 days ago, no action taken",
                "backend-service": "INFO: all systems normal",
            },
            "diagnostics": {
                "ssl_check": "Certificate CN=api.example.com expired 1 day ago. Renewal pending.",
                "cpu": "Normal across all services.",
                "memory": "Normal across all services.",
            },
            "fix_action": "mark_resolved",
            "fix_target": "ssl_certificate_expired",
            "fix_hint": "Run ssl_check diagnostic to confirm expiry, then mark_resolved with root cause ssl_certificate_expired.",
        },
    ],
    "medium": [
        {
            "id": "redis-oom",
            "title": "Checkout, auth, and inventory all degraded",
            "root_cause": "redis_out_of_memory",
            "affected_services": ["checkout-service", "auth-service", "inventory-service"],
            "initial_alerts": [
                "ALERT: checkout-service latency p99 > 8s",
                "ALERT: auth-service cache miss rate 100%",
                "ALERT: inventory-service stale data warnings",
            ],
            "initial_status": {
                "checkout-service": "degraded",
                "auth-service": "degraded",
                "inventory-service": "degraded",
                "redis-cluster": "down",
            },
            "logs": {
                "checkout-service": "WARN: session store unavailable, falling back to DB\nERROR: DB overloaded due to cache bypass",
                "auth-service": "ERROR: Redis NOAUTH — OOM command not allowed when used memory > maxmemory\nWARN: falling back to stateless auth — degraded performance",
                "inventory-service": "WARN: cache read failed, serving stale inventory data\nERROR: write-through cache unavailable",
                "redis-cluster": "FATAL: OOM — used_memory 8192MB maxmemory 8192MB\nERROR: eviction policy noeviction — refusing writes",
            },
            "diagnostics": {
                "memory": "Redis: 8192MB / 8192MB (100%). No eviction policy set. 3 large keys detected: session_data (2.1GB), product_cache (3.4GB), cart_data (1.8GB).",
                "cpu": "redis-cluster CPU: 94%. All app services CPU normal.",
                "db_connections": "DB connection count spiked from 20 to 340 in last 10 minutes due to cache bypass.",
            },
            "fix_action": "restart_service",
            "fix_target": "redis-cluster",
            "fix_hint": "Redis OOM requires restart to flush memory, then scale_up to add memory capacity.",
        },
        {
            "id": "bad-deploy-memory-leak",
            "title": "Order service slowly degrading after deployment",
            "root_cause": "memory_leak_in_deployment_v2.4.1",
            "affected_services": ["order-service"],
            "initial_alerts": [
                "ALERT: order-service memory usage > 90%",
                "ALERT: order-service response time increasing (p50: 2s, was 200ms)",
            ],
            "initial_status": {"order-service": "degraded", "payment-service": "healthy"},
            "logs": {
                "order-service": "WARN: heap usage 91% — GC pressure high\nWARN: GC pause time 4.2s — service nearly unresponsive\nINFO: deployed v2.4.1 at 14:32 UTC (2h ago)",
                "payment-service": "INFO: all systems normal",
            },
            "diagnostics": {
                "memory": "order-service heap: 14.2GB / 16GB. Memory growing at ~120MB/min since v2.4.1 deploy.",
                "cpu": "order-service CPU: 67% (GC pressure). payment-service normal.",
                "db_connections": "Normal.",
            },
            "fix_action": "rollback_deployment",
            "fix_target": "order-service",
            "fix_hint": "Memory leak started after v2.4.1 deploy. Rollback to v2.4.0 to restore service.",
        },
    ],
    "hard": [
        {
            "id": "silent-data-corruption",
            "title": "Customers reporting wrong order amounts — no obvious alerts",
            "root_cause": "floating_point_bug_in_v3.1.0_pricing_service",
            "affected_services": ["pricing-service"],
            "initial_alerts": [
                "ALERT: customer complaint rate up 340% in last 2 hours",
                "INFO: all services reporting healthy",
            ],
            "initial_status": {
                "pricing-service": "healthy",
                "checkout-service": "healthy",
                "payment-service": "healthy",
            },
            "logs": {
                "pricing-service": "INFO: deployed v3.1.0 at 09:15 UTC\nINFO: processed 14,203 pricing requests — no errors\nDEBUG: price_calculation using float32 arithmetic (changed from float64 in v3.1.0)",
                "checkout-service": "INFO: all transactions completing successfully",
                "payment-service": "INFO: all payments processed",
            },
            "diagnostics": {
                "memory": "All services normal.",
                "cpu": "All services normal.",
                "db_connections": "Normal.",
                "data_integrity": "Sampled 100 recent orders: 67 show price discrepancy of 0.01–2.34 USD vs expected. Discrepancies correlate with items priced above $99.99. Pattern matches float32 precision loss.",
            },
            "fix_action": "rollback_deployment",
            "fix_target": "pricing-service",
            "fix_hint": "No infrastructure alerts — must run data_integrity diagnostic to find the bug, then rollback pricing-service.",
        },
        {
            "id": "cascading-dns",
            "title": "Intermittent failures across multiple services — no clear pattern",
            "root_cause": "dns_resolver_misconfiguration_after_infra_change",
            "affected_services": ["api-gateway", "microservice-mesh","dns-resolver"],
            "initial_alerts": [
                "ALERT: api-gateway intermittent connection refused (30% requests)",
                "ALERT: service mesh health checks flapping",
            ],
            "initial_status": {
                "api-gateway": "degraded",
                "auth-service": "flapping",
                "checkout-service": "flapping",
                "dns-resolver": "degraded",
            },
            "logs": {
                "api-gateway": "ERROR: dial tcp: lookup checkout-service on 10.0.0.2:53: no such host\nERROR: dial tcp: lookup auth-service on 10.0.0.2:53: no such host\nWARN: retrying with fallback resolver 8.8.8.8 — success",
                "auth-service": "WARN: periodic connection timeouts to downstream services\nINFO: self-checks passing",
                "dns-resolver": "ERROR: CoreDNS config updated at 11:02 UTC — missing forward zone for .internal\nERROR: NXDOMAIN for all .internal hostnames",
            },
            "diagnostics": {
                "cpu": "All normal.",
                "memory": "All normal.",
                "db_connections": "Normal.",
                "dns_check": "Internal DNS failing for *.internal domains since 11:02 UTC. External DNS (8.8.8.8) functional. CoreDNS configmap missing 'forward . 10.0.0.1' entry. RECOMMENDED ACTION: restart_service dns-resolver to reload config.",
            },
            "fix_action": "restart_service",
            "fix_target": "dns-resolver",
            "fix_hint": "Intermittent failures with no memory/CPU cause — must run dns_check diagnostic to find root cause.",
        },
    ],
}

DIFFICULTY_CONFIG = {
    "easy":   {"max_steps": 8,  "visible_logs": True,  "visible_diagnostics": False},
    "medium": {"max_steps": 10, "visible_logs": True,  "visible_diagnostics": False},
    "hard":   {"max_steps": 12, "visible_logs": False, "visible_diagnostics": False},
}

_SESSION = {
    "episode_id": None,
    "step_count": 0,
    "max_steps": 8,
    "incident": None,
    "difficulty": None,
    "actions_taken": [],
    "logs_checked": set(),
    "diagnostics_run": set(),
    "root_cause_confirmed": False,
    "services_restored": 0,
    "team_notified": False,
    "escalated": False,
    "resolved": False,
    "wrong_restarts": 0,
}


def pick_incident(difficulty):
    return random.choice(INCIDENTS[difficulty])


class CrisisRoomEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = False

    def __init__(self):
        pass

    def reset(self, difficulty=None) -> IncidentObservation:
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = random.choice(["easy", "medium", "hard"])

        incident = pick_incident(difficulty)
        cfg = DIFFICULTY_CONFIG[difficulty]

        _SESSION.update({
            "episode_id": str(uuid4()),
            "step_count": 0,
            "max_steps": cfg["max_steps"],
            "incident": incident,
            "difficulty": difficulty,
            "actions_taken": [],
            "logs_checked": set(),
            "diagnostics_run": set(),
            "root_cause_confirmed": False,
            "services_restored": 0,
            "team_notified": False,
            "escalated": False,
            "resolved": False,
            "wrong_restarts": 0,
        })

        context = None
        if cfg["visible_logs"]:
            context = "Available logs: " + ", ".join(incident["logs"].keys())

        return IncidentObservation(
            step=0,
            max_steps=cfg["max_steps"],
            message=f"[{difficulty.upper()}] INCIDENT: {incident['title']}\n{context or 'Run check_logs or run_diagnostic to investigate.'}",
            difficulty=difficulty,
            episode_id=_SESSION["episode_id"],
            active_alerts=incident["initial_alerts"],
            service_status=incident["initial_status"],
            log_output=None,
            actions_taken=[],
            root_cause_found=False,
            services_restored=0,
            total_services_affected=len(incident["affected_services"]),
            partial_score=0.0,
            steps_remaining=cfg["max_steps"],
            done=False,
            reward=0.0,
        )

    def step(self, action: IncidentAction) -> IncidentObservation:
        s = _SESSION
        incident = s["incident"]
        action.target = (action.target or "")[:500]

        recent = s["actions_taken"][-3:] if len(s["actions_taken"]) >= 3 else []
        if len(recent) == 3 and len(set(recent)) == 1:
            s["wrong_restarts"] += 1

        if s["step_count"] >= s["max_steps"] or s["resolved"]:
            reward = _compute_reward()
            return _obs(reward=reward, done=True, message=f"Episode over. Final reward: {reward:.3f}")

        s["step_count"] += 1
        s["actions_taken"].append(f"{action.action_type}:{action.target}")
        log_out = None
        msg = ""

        if action.action_type == "check_logs":
            svc = action.target
            if svc in incident["logs"]:
                s["logs_checked"].add(svc)
                log_out = incident["logs"][svc]
                msg = f"Logs for {svc} retrieved."
            else:
                log_out = f"No logs found for '{svc}'. Available: {list(incident['logs'].keys())}"
                msg = "Service not found."

        elif action.action_type == "run_diagnostic":
            diag = action.target
            if diag in incident["diagnostics"]:
                s["diagnostics_run"].add(diag)
                log_out = incident["diagnostics"][diag]
                if diag == incident.get("fix_target") or diag in ("data_integrity", "dns_check", "ssl_check"):
                    s["root_cause_confirmed"] = True
                msg = f"Diagnostic '{diag}' complete."
            else:
                available = list(incident["diagnostics"].keys())
                log_out = f"Unknown diagnostic '{diag}'. Available: {available}"
                msg = "Diagnostic not found."

        elif action.action_type == "restart_service":
            svc = action.target
            if svc in incident["affected_services"]:
                if incident["fix_action"] == "restart_service" and incident["fix_target"] == svc:
                    s["services_restored"] += 1
                    s["resolved"] = True
                    msg = f"{svc} restarted and recovered."
                else:
                    s["wrong_restarts"] += 1
                    msg = f"{svc} restarted but issue persists — may not be the root cause."
            else:
                s["wrong_restarts"] += 1
                msg = f"{svc} is not affected. Unnecessary restart."

        elif action.action_type == "rollback_deployment":
            svc = action.target
            if incident["fix_action"] == "rollback_deployment" and incident["fix_target"] == svc:
                s["services_restored"] += 1
                s["resolved"] = True
                msg = f"{svc} rolled back. Service restored."
            else:
                s["wrong_restarts"] += 1
                msg = f"Rollback of {svc} did not resolve the issue."

        elif action.action_type == "scale_up":
            svc = action.target
            msg = f"Scaled up {svc}. May reduce pressure but root cause not addressed."

        elif action.action_type == "notify_team":
            if s["team_notified"]:
                s["wrong_restarts"] += 1
                msg = "Team already notified. Redundant call penalized."
            else:
                s["team_notified"] = True
                msg = f"Team notified: {action.target}"

        elif action.action_type == "escalate":
            if s["escalated"]:
                s["wrong_restarts"] += 1
                msg = "Already escalated. Redundant call penalized."
            else:
                s["escalated"] = True
                msg = f"Escalated to on-call lead: {action.target}"

        elif action.action_type == "mark_resolved":
            stated_cause = action.target
            if stated_cause == incident["root_cause"]:
                s["root_cause_confirmed"] = True
                s["services_restored"] = len(incident["affected_services"])
            s["resolved"] = True
            msg = f"Marked resolved. Stated cause: {stated_cause}"

        else:
            s["wrong_restarts"] += 1
            msg = f"Unknown action '{action.action_type}'. Valid: check_logs, run_diagnostic, restart_service, rollback_deployment, scale_up, notify_team, escalate, mark_resolved"

        reward = _compute_reward()
        done = s["resolved"] or s["step_count"] >= s["max_steps"]

        if done and not s["resolved"]:
            msg += f" | Time limit reached. Final reward: {reward:.3f}"

        return _obs(reward=reward, done=done, message=msg, log_output=log_out)

    @property
    def state(self) -> State:
        return State(episode_id=_SESSION["episode_id"], step_count=_SESSION["step_count"])


def _compute_reward() -> float:
    s = _SESSION
    incident = s["incident"]
    if not incident:
        return 0.0

    total_affected = len(incident["affected_services"])

                                                     
    resolution_score = 0.0
    if s["resolved"] and s["services_restored"] > 0:
        resolution_score = s["services_restored"] / max(total_affected, 1)

                                                       
    investigation_score = 0.0
    if s["logs_checked"] or s["diagnostics_run"]:
        relevant_logs = set(incident["logs"].keys()) & s["logs_checked"]
        relevant_diags = set(incident["diagnostics"].keys()) & s["diagnostics_run"]
        investigation_score = min(1.0, (len(relevant_logs) + len(relevant_diags)) / max(len(incident["logs"]) + len(incident["diagnostics"]), 1))

                                             
    max_steps = s["max_steps"]
    steps_used = s["step_count"]
    efficiency = max(0.0, 1.0 - (steps_used / max_steps))

                              
    comms_score = 0.5 if s["team_notified"] else 0.0
    comms_score += 0.5 if s["escalated"] and s["difficulty"] == "hard" else 0.0

               
    penalty = 0.1 * s["wrong_restarts"]

    raw = (0.4 * resolution_score) + (0.3 * investigation_score) + (0.2 * efficiency) + (0.1 * comms_score) - penalty
    return round(max(0.0, min(1.0, raw)), 4)


def _obs(reward, done, message, log_output=None) -> IncidentObservation:
    s = _SESSION
    incident = s["incident"]
    return IncidentObservation(
        step=s["step_count"],
        max_steps=s["max_steps"],
        message=message,
        difficulty=s["difficulty"],
        episode_id=s["episode_id"],
        active_alerts=incident["initial_alerts"] if incident else [],
        service_status=incident["initial_status"] if incident else {},
        log_output=log_output,
        actions_taken=s["actions_taken"],
        root_cause_found=s["root_cause_confirmed"],
        services_restored=s["services_restored"],
        total_services_affected=len(incident["affected_services"]) if incident else 0,
        partial_score=reward,
        steps_remaining=s["max_steps"] - s["step_count"],
        done=done,
        reward=reward,
    )