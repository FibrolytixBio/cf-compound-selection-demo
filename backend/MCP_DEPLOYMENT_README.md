# MCP Server Deployment Guide

This guide explains how to deploy PubChem and ChemBL MCP servers as HTTP endpoints using Modal.

### Test Deployment

```bash
python test_mcp_deployment.py
```

## API Endpoints

### Base URL

Your Modal deployment will provide a base URL like:

```
https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run
```

### Available Endpoints

#### 1. Root Information

```
GET /
```

Returns basic API information and available endpoints.

#### 2. Server Information

```
GET /pubchem/info
GET /chembl/info
```

Returns list of available tools and their descriptions.

#### 3. Tool Execution

```
POST /pubchem/call
POST /chembl/call
```

Request format:

```json
{
  "tool_name": "PUBCHEM__search_compounds",
  "arguments": {
    "query": "aspirin",
    "search_type": "name",
    "max_records": 5
  }
}
```

Response format:

```json
{
  "success": true,
  "result": { ... },
  "error": null
}
```

## How to Use the Deployed MCP Servers

### Base URL

Your deployed MCP servers are available at:

```
https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run
```

### API Request Format

All function calls use the same format:

```json
{
  "tool_name": "FUNCTION_NAME",
  "arguments": {
    "parameter1": "value1",
    "parameter2": "value2"
  }
}
```

### Response Format

All responses follow this structure:

```json
{
  "success": true,
  "result": {
    /* function-specific data */
  },
  "error": null
}
```

## Detailed Usage Examples

### 1. Basic cURL Examples

#### Search for Compounds in PubChem

```bash
curl -X POST "https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run/pubchem/call" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "PUBCHEM__search_compounds",
    "arguments": {
      "query": "aspirin",
      "search_type": "name",
      "max_records": 5
    }
  }'
```

#### Get Compound Properties from PubChem

```bash
curl -X POST "https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run/pubchem/call" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "PUBCHEM__get_compound_properties",
    "arguments": {
      "cid": "2244",
      "properties": ["MolecularWeight", "XLogP", "TPSA", "HBondDonorCount"]
    }
  }'
```

#### Search ChemBL Database

```bash
curl -X POST "https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run/chembl/call" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "CHEMBL__search_compounds",
    "arguments": {
      "query": "aspirin",
      "limit": 3
    }
  }'
```

#### Get Drug Information from ChemBL

```bash
curl -X POST "https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run/chembl/call" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "CHEMBL__get_drug_info",
    "arguments": {
      "chembl_id": "CHEMBL25",
      "max_results": 1
    }
  }'
```

### 2. Python Client Examples

#### Async Python Client

```python
import httpx
import asyncio
import json

BASE_URL = "https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run"

class BiotechMCPClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    async def call_pubchem(self, tool_name: str, **kwargs):
        """Call a PubChem tool"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/pubchem/call",
                json={"tool_name": tool_name, "arguments": kwargs}
            )
            return response.json()

    async def call_chembl(self, tool_name: str, **kwargs):
        """Call a ChemBL tool"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chembl/call",
                json={"tool_name": tool_name, "arguments": kwargs}
            )
            return response.json()

    async def search_compound_everywhere(self, compound_name: str):
        """Search for a compound in both PubChem and ChemBL"""
        pubchem_task = self.call_pubchem(
            "PUBCHEM__search_compounds",
            query=compound_name,
            search_type="name",
            max_records=5
        )

        chembl_task = self.call_chembl(
            "CHEMBL__search_compounds",
            query=compound_name,
            limit=5
        )

        pubchem_result, chembl_result = await asyncio.gather(
            pubchem_task, chembl_task
        )

        return {
            "pubchem": pubchem_result,
            "chembl": chembl_result
        }

# Usage Example
async def main():
    client = BiotechMCPClient()

    # Search for aspirin in both databases
    results = await client.search_compound_everywhere("aspirin")

    if results["pubchem"]["success"]:
        print(f"PubChem found {results['pubchem']['result']['total_found']} compounds")

    if results["chembl"]["success"]:
        molecules = results["chembl"]["result"]["molecules"]
        print(f"ChemBL found {len(molecules)} compounds")

# Run the example
# asyncio.run(main())
```

#### Synchronous Python Client

```python
import requests
import json

BASE_URL = "https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run"

def call_pubchem_sync(tool_name: str, **kwargs):
    """Synchronous PubChem call"""
    response = requests.post(
        f"{BASE_URL}/pubchem/call",
        json={"tool_name": tool_name, "arguments": kwargs},
        timeout=30
    )
    return response.json()

def call_chembl_sync(tool_name: str, **kwargs):
    """Synchronous ChemBL call"""
    response = requests.post(
        f"{BASE_URL}/chembl/call",
        json={"tool_name": tool_name, "arguments": kwargs},
        timeout=30
    )
    return response.json()

# Example: Get molecular properties
def analyze_compound(compound_name: str):
    # First, search for the compound in PubChem
    search_result = call_pubchem_sync(
        "PUBCHEM__search_compounds",
        query=compound_name,
        search_type="name",
        max_records=1
    )

    if not search_result["success"]:
        return {"error": "Compound not found"}

    # Get the CID
    properties = search_result["result"]["details"]["PropertyTable"]["Properties"][0]
    cid = properties["CID"]

    # Get detailed properties
    props_result = call_pubchem_sync(
        "PUBCHEM__get_compound_properties",
        cid=str(cid),
        properties=[
            "MolecularWeight", "XLogP", "TPSA",
            "HBondDonorCount", "HBondAcceptorCount", "RotatableBondCount"
        ]
    )

    return {
        "basic_info": properties,
        "detailed_properties": props_result["result"] if props_result["success"] else None
    }

# Usage
# result = analyze_compound("aspirin")
# print(json.dumps(result, indent=2))
```

### 3. OpenAI Integration Examples

#### Define Tools for OpenAI

```python
import openai
import json
import httpx

BASE_URL = "https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run"

# Tool definitions for OpenAI
PUBCHEM_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_pubchem_compounds",
        "description": "Search PubChem database for chemical compounds",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Compound name, SMILES, or chemical identifier"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["name", "smiles", "formula"],
                    "default": "name",
                    "description": "Type of search to perform"
                },
                "max_records": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Maximum number of results"
                }
            },
            "required": ["query"]
        }
    }
}

CHEMBL_DRUG_INFO_TOOL = {
    "type": "function",
    "function": {
        "name": "get_chembl_drug_info",
        "description": "Get drug information from ChemBL database",
        "parameters": {
            "type": "object",
            "properties": {
                "chembl_id": {
                    "type": "string",
                    "description": "ChemBL ID (e.g., CHEMBL25)"
                }
            },
            "required": ["chembl_id"]
        }
    }
}

# Tool execution functions
async def execute_pubchem_search(query: str, search_type: str = "name", max_records: int = 5):
    """Execute PubChem search via HTTP API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/pubchem/call",
            json={
                "tool_name": "PUBCHEM__search_compounds",
                "arguments": {
                    "query": query,
                    "search_type": search_type,
                    "max_records": max_records
                }
            }
        )
        result = response.json()
        if result["success"]:
            return json.dumps(result["result"])
        else:
            return f"Error: {result['error']}"

async def execute_chembl_drug_info(chembl_id: str):
    """Execute ChemBL drug info via HTTP API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chembl/call",
            json={
                "tool_name": "CHEMBL__get_drug_info",
                "arguments": {"chembl_id": chembl_id, "max_results": 1}
            }
        )
        result = response.json()
        if result["success"]:
            return json.dumps(result["result"])
        else:
            return f"Error: {result['error']}"

# OpenAI Chat with Tools
async def chat_with_biotech_tools(user_message: str):
    """Chat with OpenAI using biotech MCP tools"""

    # Tool execution mapping
    tool_functions = {
        "search_pubchem_compounds": execute_pubchem_search,
        "get_chembl_drug_info": execute_chembl_drug_info
    }

    # Initial chat completion
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a expert in chemistry and drug discovery. Use the available tools to help answer questions about compounds, drugs, and molecular properties."},
            {"role": "user", "content": user_message}
        ],
        tools=[PUBCHEM_SEARCH_TOOL, CHEMBL_DRUG_INFO_TOOL],
        tool_choice="auto"
    )

    # Handle tool calls
    if response.choices[0].message.tool_calls:
        messages = [
            {"role": "system", "content": "You are a expert in chemistry and drug discovery."},
            {"role": "user", "content": user_message},
            response.choices[0].message
        ]

        for tool_call in response.choices[0].message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # Execute the tool
            if function_name in tool_functions:
                function_result = await tool_functions[function_name](**function_args)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_result
                })

        # Get final response
        final_response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        return final_response.choices[0].message.content
    else:
        return response.choices[0].message.content

# Usage
# result = await chat_with_biotech_tools("Tell me about aspirin's molecular properties and drug information")
```

### 4. Error Handling Best Practices

```python
import httpx
import asyncio
from typing import Optional, Dict, Any

async def safe_mcp_call(
    endpoint: str,
    tool_name: str,
    arguments: Dict[str, Any],
    max_retries: int = 3,
    timeout: float = 30.0
) -> Optional[Dict[str, Any]]:
    """Make a safe MCP call with error handling and retries"""

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    endpoint,
                    json={"tool_name": tool_name, "arguments": arguments}
                )

                if response.status_code == 200:
                    result = response.json()
                    if result["success"]:
                        return result["result"]
                    else:
                        print(f"API Error: {result['error']}")
                        return None
                else:
                    print(f"HTTP Error {response.status_code}: {response.text}")

        except httpx.TimeoutException:
            print(f"Timeout on attempt {attempt + 1}")
        except httpx.RequestError as e:
            print(f"Request error on attempt {attempt + 1}: {e}")
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    return None

# Usage
# result = await safe_mcp_call(
#     f"{BASE_URL}/pubchem/call",
#     "PUBCHEM__search_compounds",
#     {"query": "aspirin", "search_type": "name", "max_records": 5}
# )
```

### 5. Batch Processing Example

```python
import asyncio
import httpx
from typing import List, Dict, Any

async def batch_compound_analysis(compound_names: List[str]) -> Dict[str, Any]:
    """Analyze multiple compounds in parallel"""

    async def analyze_single_compound(compound_name: str):
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search PubChem
            pubchem_response = await client.post(
                f"{BASE_URL}/pubchem/call",
                json={
                    "tool_name": "PUBCHEM__search_compounds",
                    "arguments": {
                        "query": compound_name,
                        "search_type": "name",
                        "max_records": 1
                    }
                }
            )

            # Search ChemBL
            chembl_response = await client.post(
                f"{BASE_URL}/chembl/call",
                json={
                    "tool_name": "CHEMBL__search_compounds",
                    "arguments": {
                        "query": compound_name,
                        "limit": 1
                    }
                }
            )

            return {
                "compound": compound_name,
                "pubchem": pubchem_response.json(),
                "chembl": chembl_response.json()
            }

    # Process all compounds in parallel
    tasks = [analyze_single_compound(name) for name in compound_names]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "total_processed": len(compound_names),
        "results": results
    }

# Usage
# compounds = ["aspirin", "ibuprofen", "acetaminophen"]
# batch_results = await batch_compound_analysis(compounds)
```

### 6. Real Example Responses

#### PubChem Search Response

```json
{
  "success": true,
  "result": {
    "query": "aspirin",
    "search_type": "name",
    "total_found": 1,
    "details": {
      "PropertyTable": {
        "Properties": [
          {
            "CID": 2244,
            "MolecularFormula": "C9H8O4",
            "MolecularWeight": "180.16",
            "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "IUPACName": "2-acetyloxybenzoic acid"
          }
        ]
      }
    }
  }
}
```

#### ChemBL Search Response

```json
{
  "success": true,
  "result": {
    "molecules": [
      {
        "chembl_id": "CHEMBL25",
        "pref_name": "ASPIRIN",
        "max_phase": 4,
        "molecule_type": "Small molecule",
        "first_approval": 1950,
        "oral": true,
        "topical": false,
        "black_box_warning": false,
        "natural_product": false,
        "first_in_class": false,
        "chirality": 0,
        "prodrug": false,
        "inorganic_flag": false,
        "usan_year": 1962,
        "availability_type": 1,
        "usan_stem": null,
        "polymer_flag": false,
        "usan_substem": null,
        "usan_stem_definition": null,
        "indication_class": "Analgesics; Anti-inflammatory Agents, Non-Steroidal; Antirheumatic Agents; Cyclooxygenase Inhibitors; Platelet Aggregation Inhibitors"
      }
    ]
  }
}
```

## Available Tools

### PubChem Tools (with PUBCHEM\_\_ prefix)

- `PUBCHEM__search_compounds` - Search for compounds by name/SMILES/etc.
- `PUBCHEM__get_compound_info` - Get detailed compound information
- `PUBCHEM__search_by_smiles` - Search by SMILES string
- `PUBCHEM__get_compound_properties` - Get molecular properties
- `PUBCHEM__get_bioassay_results` - Get bioassay data
- `PUBCHEM__get_toxicity_data` - Get toxicity information
- And many more...

### ChemBL Tools (with CHEMBL\_\_ prefix)

- `CHEMBL__search_compounds` - Search ChemBL database
- `CHEMBL__get_compound_bioactivities` - Get bioactivity data
- `CHEMBL__get_molecule_info` - Get molecule information
- `CHEMBL__get_target_information` - Get target information
- `CHEMBL__get_drug_info` - Get drug information
- And many more...

## Benefits

1. **No Local Deployment**: Servers run on Modal's infrastructure
2. **Auto-scaling**: Modal handles scaling based on demand
3. **HTTP Access**: Easy integration with any HTTP client
4. **OpenAI Compatible**: Works with OpenAI function calling
5. **Cross-Platform**: Accessible from any programming language
6. **Persistent**: Servers stay available without manual deployment

## Costs

Modal provides $30 free credits, which should be plenty for development and testing. Production usage will depend on your request volume.

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure your `pyproject.toml` includes all dependencies
2. **Function Not Found**: Check that function names include the correct prefix
3. **Timeout Issues**: Increase timeout for complex queries
4. **Rate Limits**: Add retry logic for external API calls

### Testing

Use the test script to validate everything works:

```bash
python test_mcp_deployment.py
```

## Security Considerations

For production deployment, consider:

- Adding API key authentication
- Rate limiting per user
- Request size limits
- Logging and monitoring
- HTTPS enforcement (Modal provides this by default)
