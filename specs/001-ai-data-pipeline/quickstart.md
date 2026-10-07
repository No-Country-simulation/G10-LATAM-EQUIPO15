# Quickstart: AI Data Processing Pipeline Validation

## Prerequisites
- Ollama installed and `hermes3:8b` pulled locally.
- `.env` configured with API keys for Gemini and Groq.
- Python dependencies installed (`pip install -r requirements.txt`).

## Validation Scenario 1: Successful Pipeline Execution
This proves that the pipeline ingests data, processes it via the AI agents, audits the result with Hermes, and outputs the correct contract.

1. Ensure Ollama is running.
2. Run the test script:
   ```bash
   python tests/test_ai_pipeline_end_to_end.py
   ```
3. **Expected Outcome**: The test passes, logging the generated mermaid graph and the `is_secure: True` audit flag from Hermes in under 10 seconds.

## Validation Scenario 2: Security Rejection
This proves that Hermes correctly identifies logic or security flaws.

1. Inject a simulated prompt-injection payload into the test suite.
2. Run the test script:
   ```bash
   python tests/test_hermes_audit.py
   ```
3. **Expected Outcome**: The test passes by successfully failing the payload, returning `is_secure: False` and listing the caught vulnerabilities.
