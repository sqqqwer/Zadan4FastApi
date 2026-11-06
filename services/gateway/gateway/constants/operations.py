OPERATION_PATHS = {
    service: {operation: f"/{operation}" for operation in ("health", "ready", "outbox", "consumer-lag")}
    for service in ("auth", "org", "tasks", "saga")
}
OPERATION_PATHS["saga"]["stalled"] = "/saga/api/v1/stalled"
