#!/usr/bin/env python3
"""
Modal deployment for MCP servers as HTTP endpoints
"""

import modal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

# Modal setup
image = (
    modal.Image.debian_slim()
    .pip_install_from_pyproject("pyproject.toml")
    .add_local_python_source("agentic_system")
)

app = modal.App("biotech-mcp-servers", image=image)

# We don't need global MCP server variables anymore

# Request/Response models for the API
class MCPToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

class MCPToolResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ServerInfoResponse(BaseModel):
    server_name: str
    tools: list

# No longer need initialization function

# Create FastAPI apps for each server
def create_fastapi_app():
    """Create FastAPI app with CORS enabled"""
    fastapi_app = FastAPI(
        title="Biotech MCP Servers",
        description="HTTP endpoints for PubChem and ChemBL MCP servers",
        version="1.0.0"
    )
    
    # Enable CORS for all origins (adjust in production)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @fastapi_app.get("/")
    async def root():
        return {
            "message": "Biotech MCP Servers API",
            "endpoints": {
                "pubchem": "/pubchem",
                "chembl": "/chembl"
            }
        }
    
    @fastapi_app.get("/pubchem/info")
    async def pubchem_info():
        """Get information about available PubChem tools"""
        from agentic_system.tools import pubchem_mcp_server
        import inspect
        
        tools = []
        for name in dir(pubchem_mcp_server):
            if name.startswith("PUBCHEM__") and callable(getattr(pubchem_mcp_server, name)):
                func = getattr(pubchem_mcp_server, name)
                tools.append({
                    "name": name,
                    "description": func.__doc__ or "No description available"
                })
        return ServerInfoResponse(server_name="PubChem", tools=tools)
    
    @fastapi_app.get("/chembl/info")
    async def chembl_info():
        """Get information about available ChemBL tools"""
        from agentic_system.tools import chembl_mcp_server
        import inspect
        
        tools = []
        for name in dir(chembl_mcp_server):
            if name.startswith("CHEMBL__") and callable(getattr(chembl_mcp_server, name)):
                func = getattr(chembl_mcp_server, name)
                tools.append({
                    "name": name,
                    "description": func.__doc__ or "No description available"
                })
        return ServerInfoResponse(server_name="ChemBL", tools=tools)
    
    @fastapi_app.post("/pubchem/call")
    async def call_pubchem_tool(request: MCPToolRequest):
        """Call a PubChem MCP tool"""
        
        try:
            # Import tools dynamically to get access to the functions
            from agentic_system.tools import pubchem_mcp_server
            
            # Get the tool function by name
            if not hasattr(pubchem_mcp_server, request.tool_name):
                raise HTTPException(
                    status_code=404, 
                    detail=f"Tool '{request.tool_name}' not found in PubChem server"
                )
            
            tool_func = getattr(pubchem_mcp_server, request.tool_name)
            
            # Create the appropriate request model from the tool's signature
            import inspect
            sig = inspect.signature(tool_func)
            param_name = list(sig.parameters.keys())[0]  # First parameter is the request model
            param_type = sig.parameters[param_name].annotation
            
            # Create request object
            request_obj = param_type(**request.arguments)
            result = await tool_func(request_obj)
            
            return MCPToolResponse(success=True, result=result)
            
        except Exception as e:
            return MCPToolResponse(success=False, error=str(e))
    
    @fastapi_app.post("/chembl/call")
    async def call_chembl_tool(request: MCPToolRequest):
        """Call a ChemBL MCP tool"""
        
        try:
            # Import tools dynamically to get access to the functions
            from agentic_system.tools import chembl_mcp_server
            
            # Get the tool function by name
            if not hasattr(chembl_mcp_server, request.tool_name):
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{request.tool_name}' not found in ChemBL server"
                )
            
            tool_func = getattr(chembl_mcp_server, request.tool_name)
            
            # Create the appropriate request model from the tool's signature
            import inspect
            sig = inspect.signature(tool_func)
            param_name = list(sig.parameters.keys())[0]  # First parameter is the request model
            param_type = sig.parameters[param_name].annotation
            
            # Create request object
            request_obj = param_type(**request.arguments)
            result = await tool_func(request_obj)
            
            return MCPToolResponse(success=True, result=result)
            
        except Exception as e:
            return MCPToolResponse(success=False, error=str(e))
    
    return fastapi_app

# Deploy the FastAPI app on Modal
@app.function(
    image=image,
    scaledown_window=300,  # Keep warm for 5 minutes
    cpu=2,
    memory=1024,
    timeout=60,
)
@modal.asgi_app()
def biotech_mcp_api():
    return create_fastapi_app()

if __name__ == "__main__":
    print("Deploying Biotech MCP Servers to Modal...")
    print("This will host PubChem and ChemBL MCP servers as HTTP endpoints")