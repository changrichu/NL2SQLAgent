# Contributing to AskData

Thanks for your interest in improving AskData! 🎉

## Ground Rules

1. **Be respectful.** Assume good intent.
2. **No fabrication.** Never add fake benchmarks or fictitious case studies.
3. **Keep API keys out of code.** Use `.env`, and `.env` must stay in `.gitignore`.

## Local Development

```bash
git clone https://github.com/changrichu/AskData.git
cd AskData
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
make test
```

## Pull Request Flow

1. Fork the repo and create a branch: `git checkout -b feat/awesome-thing`
2. Make your changes; add tests when relevant.
3. Run `make lint` and `make test` — both must pass.
4. Open a PR with a clear description (problem → approach → trade-offs).

## Adding a New Connector

1. Subclass `BaseConnector` in `src/askdata/connectors/<name>.py`.
2. Register it in `src/askdata/connectors/__init__.py` (`CONNECTOR_REGISTRY`).
3. Document the connection params in `config/datasources.yaml`.
4. Add a smoke test under `tests/`.

## Adding a New LLM Provider

1. Add an entry to `LLMClient.PROVIDERS` in `src/askdata/llm_client.py`.
2. Add the corresponding `*_API_KEY` field to `config.py` and `.env.example`.

## Reporting Issues

Use GitHub Issues. Please include:
- Repro steps
- Expected vs actual behavior
- Python / OS version
- Relevant logs (redact secrets!)
