# -*- encoding: utf-8 -*-

import json
import requests
from typing import NamedTuple
from odoo.exceptions import UserError


class Provider(NamedTuple):
    name: str
    display_name: str
    embedding_model: str
    llms: list[tuple[str, str]]


# Claude provider configuration - Updated based on official models overview
# Reference: https://docs.claude.com/en/docs/about-claude/models/overview
CLAUDE_PROVIDER = Provider(
    "claude",
    "Anthropic",
    "claude-3-5-sonnet-20241022",  # Using Sonnet 3.5 for embeddings (most stable)
    [
        # Latest Claude 4 models (as per official documentation)
        ("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5"),  # Best for complex agents and coding
        ("claude-opus-4-1-20250805", "Claude Opus 4.1"),      # Exceptional for specialized complex tasks
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),      # High-performance model
        ("claude-opus-4-20250514", "Claude Opus 4"),          # Previous flagship model
        
        # Claude 3.7 models
        ("claude-3-7-sonnet-20250219", "Claude Sonnet 3.7"), # High-performance with extended thinking
        
        # Claude 3.5 models
        ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),  # Latest 3.5 model
        ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku"),   # Fastest model
        
        # Claude 3 models (legacy)
        ("claude-3-sonnet-20240229", "Claude 3 Sonnet"),     # Balanced performance
        ("claude-3-haiku-20240307", "Claude 3 Haiku"),       # Fast and compact
        
        # Model aliases for convenience (as per documentation)
        ("claude-sonnet-4-5", "Claude Sonnet 4.5 (Alias)"),
        ("claude-opus-4-1", "Claude Opus 4.1 (Alias)"),
        ("claude-sonnet-4-0", "Claude Sonnet 4 (Alias)"),
        ("claude-opus-4-0", "Claude Opus 4 (Alias)"),
        ("claude-3-7-sonnet-latest", "Claude Sonnet 3.7 (Alias)"),
        ("claude-3-5-haiku-latest", "Claude Haiku 3.5 (Alias)"),
    ],
)


def get_provider_for_embedding_model(env, embedding_model):
    """Get provider name for embedding model."""
    if embedding_model == CLAUDE_PROVIDER.embedding_model:
        return CLAUDE_PROVIDER.name
    raise UserError(env._("No provider found for the embedding model"))


def get_provider(env, llm_model):
    """Get provider name for LLM model."""
    if llm_model in [m[0] for m in CLAUDE_PROVIDER.llms]:
        return CLAUDE_PROVIDER.name
    raise UserError(env._("No provider found for the selected model"))


def get_claude_api_token(env):
    """Get Claude API token from configuration."""
    api_key = env["ir.config_parameter"].sudo().get_param("ai.claude_key")
    if not api_key:
        raise UserError(env._("No API key set for provider 'claude'"))
    return api_key


class ClaudeApiService:
    """Claude API service implementation."""
    
    def __init__(self, env):
        self.env = env
        self.base_url = "https://api.anthropic.com/v1"
        self.api_key = get_claude_api_token(env)
    
    def get_embedding(self, input_text, dimensions=None, model=None, **kwargs):
        """Get embeddings from Claude API."""
        # Claude now supports embeddings as per official documentation
        # Reference: https://docs.claude.com/en/docs/intro
        
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01'
        }
        
        # Use the embedding model from provider configuration
        embedding_model = model or CLAUDE_PROVIDER.embedding_model
        
        body = {
            'input': input_text,
            'model': embedding_model
        }
        
        if dimensions:
            body['dimensions'] = dimensions
        
        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error'].get('message', error_msg)
                except:
                    pass
            raise UserError(f"Claude embedding API request failed: {error_msg}")
    
    def request_llm(self, llm_model, system_prompts, user_prompts, tools=None, 
                   files=None, schema=None, temperature=0.2, inputs=None, 
                   web_grounding=False):
        """Make a request to Claude API - Updated based on official documentation."""
        # Reference: https://docs.claude.com/en/docs/intro
        
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01'  # Latest stable version
        }
        
        # Build messages according to Claude API format
        messages = []
        
        # Add system instruction (Claude's preferred way)
        system_instruction = None
        if system_prompts:
            # Convert all prompts to strings and join them
            try:
                # Simple approach: convert everything to string and join
                system_instruction = "\n\n".join([str(prompt) for prompt in system_prompts])
            except Exception as e:
                # Fallback: if there are still nested structures, flatten them
                def flatten_recursive(item):
                    if isinstance(item, list):
                        return [subitem for sublist in item for subitem in flatten_recursive(sublist)]
                    else:
                        return [str(item)]
                
                flattened = flatten_recursive(system_prompts)
                system_instruction = "\n\n".join(flattened)
        
        # Add user prompts
        for prompt in user_prompts:
            messages.append({
                "role": "user", 
                "content": prompt
            })
        
        # Add conversation history
        if inputs:
            for input_msg in inputs:
                if input_msg.get("role") == "user":
                    messages.append({
                        "role": "user",
                        "content": input_msg.get("content", "")
                    })
                elif input_msg.get("role") == "assistant":
                    messages.append({
                        "role": "assistant",
                        "content": input_msg.get("content", "")
                    })
        
        # Build request body according to Claude API specification
        body = {
            "model": llm_model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": messages
        }
        
        # Add system instruction if provided
        if system_instruction:
            body["system"] = system_instruction
        
        # Add tools if provided (Claude supports tool use)
        if tools:
            body["tools"] = self._convert_tools_to_claude_format(tools)
        
        # Add structured output if schema provided
        if schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": schema
            }
        
        # Add web search if requested (Claude supports web grounding)
        if web_grounding:
            body["tools"] = body.get("tools", [])
            body["tools"].append({
                "name": "web_search",
                "description": "Search the web for current information"
            })
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=body,
                timeout=60  # Increased timeout for complex requests
            )
            response.raise_for_status()
            return self._parse_claude_response(response.json(), tools)
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error'].get('message', error_msg)
                except:
                    pass
            raise UserError(f"Claude API request failed: {error_msg}")
    
    def _convert_tools_to_claude_format(self, tools):
        """Convert Odoo tool format to Claude format - Updated for Claude API."""
        claude_tools = []
        for tool_name, (description, allow_end_message, func, schema) in tools.items():
            claude_tool = {
                "name": tool_name,
                "description": description,
                "input_schema": schema
            }
            claude_tools.append(claude_tool)
        return claude_tools
    
    def _parse_claude_response(self, response, tools=None):
        """Parse Claude API response - Updated for latest API format."""
        responses = []
        tool_calls = []
        next_inputs = []
        
        # Handle the latest Claude API response format
        for content_block in response.get('content', []):
            if content_block.get('type') == 'text':
                responses.append(content_block['text'])
            elif content_block.get('type') == 'tool_use':
                tool_name = content_block['name']
                tool_id = content_block['id']
                arguments = content_block['input']
                
                tool_calls.append((tool_name, tool_id, arguments))
                next_inputs.append({
                    "role": "assistant",
                    "content": content_block
                })
        
        return responses, tool_calls, next_inputs
