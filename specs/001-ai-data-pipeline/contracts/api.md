# Pipeline Contract

## Core Interface
The pipeline exposes a primary entrypoint for backend integration.

### `run_pipeline(payload: dict) -> dict`

**Input (`payload`)**:
```json
{
  "id": "uuid-string",
  "raw_text": "data to process",
  "metadata": {
    "source": "api"
  }
}
```

**Output (Success)**:
```json
{
  "status": "success",
  "id": "uuid-string",
  "results": {
    "mermaid_graph": "graph TD; A-->B;",
    "analysis": "...",
    "audit_report": {
      "is_secure": true,
      "vulnerabilities": [],
      "recommendations": []
    }
  },
  "metrics": {
    "tokens_used": 1450,
    "latency_ms": 3200
  }
}
```

**Output (Error)**:
```json
{
  "status": "error",
  "id": "uuid-string",
  "error_message": "Rate limit exceeded on failover",
  "error_code": "ERR_FAILOVER_EXHAUSTED"
}
```
