#!/usr/bin/env python3
"""
Test script for MCP server deployment
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Test data for PubChem
PUBCHEM_TEST_DATA = {
    "PUBCHEM__search_compounds": {
        "query": "aspirin",
        "search_type": "name",
        "max_records": 5
    },
    "PUBCHEM__get_compound_info": {
        "cid": "2244",
        "format": "json"
    },
    "PUBCHEM__search_by_smiles": {
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"
    }
}

# Test data for ChemBL
CHEMBL_TEST_DATA = {
    "CHEMBL__search_compounds": {
        "query": "aspirin",
        "limit": 5
    },
    "CHEMBL__get_molecule_info": {
        "chembl_id": "CHEMBL25",
        "max_results": 1
    }
}

async def test_local_functions():
    """Test the MCP functions directly (without HTTP)"""
    print("🧪 Testing MCP functions locally...")
    
    try:
        # Test PubChem
        from agentic_system.tools.pubchem_mcp_server import PUBCHEM__search_compounds, SearchCompoundsRequest
        
        request = SearchCompoundsRequest(query="aspirin", search_type="name", max_records=3)
        result = await PUBCHEM__search_compounds(request)
        print(f"✅ PubChem search_compounds: Found {result.get('total_found', 0)} compounds")
        
        # Test ChemBL
        from agentic_system.tools.chembl_mcp_server import CHEMBL__search_compounds, CompoundSearchRequest
        
        request = CompoundSearchRequest(query="aspirin", limit=3)
        result = await CHEMBL__search_compounds(request)
        print(f"✅ ChemBL search_compounds: Found {len(result.get('molecules', []))} compounds")
        
    except Exception as e:
        print(f"❌ Local test failed: {e}")

async def test_http_endpoint(base_url: str):
    """Test the HTTP endpoints"""
    print(f"🌐 Testing HTTP endpoints at {base_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{base_url}/")
            print(f"✅ Root endpoint: {response.status_code}")
            
            response = await client.get(f"{base_url}/pubchem/info")
            if response.status_code == 200:
                tools = response.json()["tools"]
                print(f"✅ PubChem info: Found {len(tools)} tools")
            else:
                print(f"❌ PubChem info failed: {response.status_code}")
            
            # Test ChemBL info
            response = await client.get(f"{base_url}/chembl/info")
            if response.status_code == 200:
                tools = response.json()["tools"]
                print(f"✅ ChemBL info: Found {len(tools)} tools")
            else:
                print(f"❌ ChemBL info failed: {response.status_code}")
            
            # Test PubChem call
            for tool_name, args in PUBCHEM_TEST_DATA.items():
                try:
                    response = await client.post(
                        f"{base_url}/pubchem/call",
                        json={"tool_name": tool_name, "arguments": args}
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result["success"]:
                            print(f"✅ PubChem {tool_name}: Success")
                        else:
                            print(f"❌ PubChem {tool_name}: {result['error']}")
                    else:
                        print(f"❌ PubChem {tool_name}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"❌ PubChem {tool_name}: {e}")
            
            # Test ChemBL call
            for tool_name, args in CHEMBL_TEST_DATA.items():
                try:
                    response = await client.post(
                        f"{base_url}/chembl/call",
                        json={"tool_name": tool_name, "arguments": args}
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result["success"]:
                            print(f"✅ ChemBL {tool_name}: Success")
                        else:
                            print(f"❌ ChemBL {tool_name}: {result['error']}")
                    else:
                        print(f"❌ ChemBL {tool_name}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"❌ ChemBL {tool_name}: {e}")
                    
        except Exception as e:
            print(f"❌ HTTP test failed: {e}")

async def test_deployment():
    """Test both local and HTTP deployment"""
    print("🚀 Testing MCP Server Deployment\n")
    
    # Test local functions first
    await test_local_functions()
    print()
    
    # Test HTTP endpoint with the actual deployed URL
    await test_http_endpoint("https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run")

if __name__ == "__main__":
    asyncio.run(test_deployment()) 