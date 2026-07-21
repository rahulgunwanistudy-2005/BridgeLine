# Orchestrator deferrals — cx/03

The cx/03 runtime ends after deterministic Rules derivation. `BriefFanOutStage`
is deliberately declared as an interface only and is not part of the runtime DAG:
cx/04 owns provider-backed teacher-brief generation and its bounded fan-out.

Also deferred from cx/03: run-history/replay endpoints and process-restart
recovery. Status events are already persisted for SSE resume; these features can
build on that durable log without changing the event contract.
