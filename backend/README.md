# Backend for CF Compound Selection

## Set Up Project

```sh
# set up dependencies
uv sync

# for development import of package
uv pip install -e .

# configure jupyter notebook
source .venv/bin/activate
python -m ipykernel install --user --name=cf-compound-selection-backend --display-name "Python (cf-compound-selection-backend)"
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