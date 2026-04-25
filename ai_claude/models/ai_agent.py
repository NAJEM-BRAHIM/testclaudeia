# -*- encoding: utf-8 -*-

import os
from odoo import models, api
from odoo.exceptions import UserError
from odoo.addons.ai_claude.utils.claude_provider import CLAUDE_PROVIDER, get_provider_for_embedding_model, get_provider, get_claude_api_token


class AIAgent(models.Model):
    _inherit = 'ai.agent'

    @api.model
    def _get_llm_model_selection(self):
        """Extend the LLM model selection to include Claude models."""
        selection = super()._get_llm_model_selection()
        # Add Claude models to the selection
        selection.extend(CLAUDE_PROVIDER.llms)
        return selection

    def _get_provider(self):
        """Override to support Claude provider."""
        self.ensure_one()
        try:
            return super()._get_provider()
        except UserError:
            # Try Claude provider
            try:
                return get_provider(self.env, self.llm_model)
            except UserError:
                raise UserError(self.env._("No provider found for the selected model"))

    def _get_embedding_model(self):
        """Override to support Claude embedding model."""
        self.ensure_one()
        try:
            return super()._get_embedding_model()
        except UserError:
            # Try Claude provider
            try:
                provider = get_provider(self.env, self.llm_model)
                if provider == 'claude':
                    return CLAUDE_PROVIDER.embedding_model
            except UserError:
                pass
            raise UserError(self.env._("No embedding model found for the selected provider"))

    def _generate_response(self, prompt, chat_history=None, extra_system_context=""):
        """Override to handle Claude provider directly."""
        self.ensure_one()
        
        # Check if this is a Claude model by checking the model name directly
        claude_models = [model[0] for model in CLAUDE_PROVIDER.llms]
        if self.llm_model in claude_models:
            # Use Claude API service directly
            from odoo.addons.ai_claude.utils.claude_provider import ClaudeApiService
            claude_service = ClaudeApiService(self.env)
            
            # Build system messages
            system_messages = self._build_system_context(extra_system_context)
            if rag_context := self._build_rag_context(prompt):
                system_messages.extend(rag_context)
            
            # Make Claude API request
            return claude_service.request_llm(
                self.llm_model,
                system_messages,
                [],
                inputs=(chat_history or []) + [{'role': 'user', 'content': prompt}],
                tools=self.topic_ids.tool_ids._get_ai_tools(),
                temperature=self._get_temperature(),
            )
        
        # Use original method for other providers
        return super()._generate_response(prompt, chat_history, extra_system_context)

    def _get_temperature(self):
        """Get temperature based on response style."""
        temperature_map = {
            'analytical': 0.2,
            'balanced': 0.5,
            'creative': 0.8,
        }
        return temperature_map.get(self.response_style, 0.5)

    def _build_rag_context(self, prompt):
        """Override to handle Claude embeddings."""
        self.ensure_one()
        
        # Check if this is a Claude model by checking the model name directly
        claude_models = [model[0] for model in CLAUDE_PROVIDER.llms]
        if self.llm_model in claude_models:
            # Claude doesn't have a separate embeddings API, so we'll try available providers
            import logging
            _logger = logging.getLogger(__name__)
            
            # Try available embedding providers in order of preference
            fallback_providers = ['openai', 'google']
            
            for provider in fallback_providers:
                try:
                    _logger.info(f"Trying {provider} embeddings for Claude RAG...")
                    
                    from odoo.addons.ai.utils.llm_api_service import LLMApiService
                    service = LLMApiService(env=self.env, provider=provider)
                    
                    # Get the appropriate embedding model for the provider
                    if provider == 'openai':
                        embedding_model = 'text-embedding-ada-002'
                    elif provider == 'google':
                        embedding_model = 'textembedding-gecko-001'
                    else:
                        continue
                    
                    response = service.get_embedding(
                        input=prompt,
                        dimensions=self.env['ai.embedding']._get_dimensions(),
                        model=embedding_model
                    )
                    
                    if response and "data" in response:
                        prompt_embedding = response['data'][0]['embedding']
                        _logger.info(f"Successfully got embeddings from {provider}")
                        
                        # Rest of the RAG context building logic
                        messages = []
                        context = ""
                        if self.sources_ids:
                            # Get similar sources using embeddings
                            similar_sources = self.env['ai.agent.source'].search([
                                ('agent_id', '=', self.id),
                                ('status', '=', 'ready')
                            ]).sudo()._search_similar_sources(prompt_embedding, limit=5)
                            
                            if similar_sources:
                                context = "\n\n".join([source.content for source in similar_sources])
                                messages.append(f"Use the following context to answer the user's question:\n\n{context}")
                                messages.append(self.env._("Restrict your answer to the information provided in the context above."))
                        
                        return messages
                        
                except Exception as e:
                    _logger.warning(f"Failed to get embeddings from {provider}: {e}")
                    continue
            
            # If all providers failed, show a clear error message
            _logger.error("Claude RAG: No embedding providers available. Please configure OpenAI or Google API keys for RAG functionality.")
            
            # Show user-friendly notification
            try:
                self.env.user.notify_warning(
                    "Claude RAG Warning",
                    "No embedding providers available for RAG functionality. Please configure OpenAI or Google API keys in Settings > AI to enable context-aware responses."
                )
            except:
                # If notify_warning fails, just log it
                pass
            
            # Return empty messages if all embeddings fail
            return []
        
        # Use original method for other providers
        return super()._build_rag_context(prompt)


# Extend the LLM providers to include Claude
def _extend_llm_providers():
    """Extend the LLM providers to include Claude."""
    from odoo.addons.ai.utils.llm_providers import PROVIDERS, EMBEDDING_MODELS_SELECTION
    
    # Add Claude provider to the global providers list
    if CLAUDE_PROVIDER not in PROVIDERS:
        PROVIDERS.append(CLAUDE_PROVIDER)
    
    # Add Claude embedding model to the selection
    claude_embedding = (CLAUDE_PROVIDER.embedding_model, CLAUDE_PROVIDER.display_name)
    if claude_embedding not in EMBEDDING_MODELS_SELECTION:
        EMBEDDING_MODELS_SELECTION.append(claude_embedding)


# Apply the extension when the module is loaded
_extend_llm_providers()