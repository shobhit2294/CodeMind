# Validation report

## Executed checks

- Backend: **32 tests passed**, **1 skipped** (real Docker execution requires the engine and sandbox image).
- Frontend: TypeScript check and Vite production build passed. Monaco creates a large bundle; the build reports a size advisory.
- Browser (headless Microsoft Edge): repository demo, architecture map, source viewer, search, scripted repair, patch download, desktop and mobile layouts passed. Final run recorded **zero page JavaScript errors**.
- Actual GitHub import: `shobhit2294/model-forge-ai`, commit `1bcf4faf1832c66f6551f90f982fdbdac2ff8a5d`; 25 files, 55 chunks, 56 symbols; no parse errors. Keyword/graph retrieval returned relevant source.
- Real CPU semantic inference: FastEmbed/ONNX MiniLM model downloaded and exercised. Four-query fixture: BM25 MRR 0.875, semantic MRR 0.875, hybrid MRR 0.875; all three recall@5 = 1.0. This tiny dataset does not demonstrate that hybrid retrieval is better, or measure general coding performance.
- The API integration test confirms original source is unchanged after patch generation and that missing Docker leads to an unverified verdict.

## Still unverified

- Live Groq authentication and the full planning → retrieval → diagnosis → patch workflow now passed with `openai/gpt-oss-20b`. A real model-generated patch was produced in one attempt. It remains **unverified** because Docker is off; no tested repair success is claimed. Evidence: `artifacts/groq-live-check.json`.
- Real Docker baseline/candidate execution and Compose build: Docker Desktop's engine was not running. The real integration test is included and deliberately skipped until available.
- Other repositories' test environments require their dependencies in the trusted sandbox image. No arbitrary installation commands are run by the agent.

## Evidence

- `artifacts/backend-tests.txt`
- `artifacts/frontend-build.log`
- `artifacts/browser-check.json`
- `artifacts/github-import.json`
- `artifacts/semantic-benchmark.json`
- `artifacts/home.png`, `repository.png`, `repair.png`, `mobile.png`

Artifacts are local and ignored by Git. `requirements-lock.txt` records the installed Windows environment; `requirements.txt` and `requirements-semantic.txt` are the portable install entry points. The tests emit upstream TestClient deprecation warnings.
