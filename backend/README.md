# Backend for CF Compound Selection

## Set Up Project

```sh
# set up dependencies
uv venv
uv sync
uv pip install -e .
```

## See examples

- [examples/run_agent.ipynb](examples/run_agent.ipynb)

## Use API Server

```sh
# Start server
uv run uvicorn api:app --reload

# Call endpoint
curl -X POST http://localhost:8000/prioritize_compound \
  -H "Content-Type: application/json" \
  -d '{"compound_name": "givinostat"}'
```