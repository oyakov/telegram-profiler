# Skill: Robust Host-Side Mass Processing

## Problem
Processing 1M+ embeddings or performing deep history sync from a Windows host environment often leads to several bottlenecks:
1. **Console Buffering:** Silent stdout make monitoring impossible for long-running scripts.
2. **Connectivity:** `host.docker.internal` (used in container configs) is unreachable from the host.
3. **Stability:** Small local LLM/Embedding servers (like LM Studio) often time out or drop connections when hit with rapid-fire batches.

## Solution

### 1. Unbuffered Output
Always run critical background scripts with the `-u` flag:
```powershell
python -u scripts/mass_index_multi_db.py
```
This ensures that `print` statements reach the terminal immediately, allowing for real-time progress monitoring.

### 2. Host-Side Network Overrides
Detect the execution environment and adjust base URLs dynamically.
```python
if os.getenv("LMSTUDIO_BASE_URL") == "http://host.docker.internal:1234/v1":
    os.environ["LMSTUDIO_BASE_URL"] = "http://localhost:1234/v1"
```
This allows the same codebase to run seamlessly inside Docker and on the local Windows host.

### 3. Error-Tolerant Batching
Use smaller batches (e.g., 5-20 messages) and high timeouts (300s) for local embedding generation.
- Wrap batch generation in `try...except` to prevent a single timeout from crashing a million-record sync.
- Use `~exists` in SQLAlchemy queries to efficiently skip already-processed records on massive tables.

## Implementation Details
See [mass_index_multi_db.py](file:///c:/Projects/telegram-profiler/scripts/mass_index_multi_db.py) for the "Slow & Steady" indexing pattern.
