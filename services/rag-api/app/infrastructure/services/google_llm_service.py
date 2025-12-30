"""
Name: Google Gemini LLM Service Implementation

Responsibilities:
  - Implement LLMService interface for Google Gemini 1.5 Flash
  - Generate RAG answers with prompt engineering
  - Apply business rules (context-only responses)
  - Handle generation errors gracefully

Collaborators:
  - domain.services.LLMService: Interface implementation
  - google.generativeai: Google Gemini SDK

Constraints:
  - Hardcoded prompt (not configurable)
  - No control over generation parameters
  - Responses in Spanish (by prompt)
  - No streaming support

Notes:
  - Implements Service interface from domain layer
  - Can be swapped with other providers (OpenAI, Claude)
  - Uses dependency inversion principle
"""

import os
import google.generativeai as genai

from ...logger import logger
from ...exceptions import LLMError


class GoogleLLMService:
    """
    R: Google Gemini implementation of LLMService.
    
    Implements domain.services.LLMService interface
    using Gemini 1.5 Flash model.
    """
    
    def __init__(self, api_key: str | None = None):
        """
        R: Initialize Google LLM Service.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
        
        Raises:
            LLMError: If API key not configured
        """
        # R: Use provided key or fall back to environment variable
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            logger.error("GoogleLLMService: GOOGLE_API_KEY not configured")
            raise LLMError("GOOGLE_API_KEY not configured")
        
        # R: Configure Google API client
        genai.configure(api_key=self.api_key)
        
        # R: Initialize model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("GoogleLLMService initialized")
    
    def generate_answer(self, query: str, context: str) -> str:
        """
        R: Generate answer based on query and retrieved context.
        
        Implements LLMService.generate_answer()
        
        Raises:
            LLMError: If response generation fails
        """
        # R: Construct prompt with business rules
        prompt = f"""
        Act as an expert assistant for RAG Corp company.
        Your mission is to answer the user's question based EXCLUSIVELY on the context provided below.
        
        Rules:
        1. If the answer is not in the context, say "I don't have enough information in my documents".
        2. Be concise and professional.
        3. Always respond in Spanish.

        --- CONTEXT ---
        {context}
        ----------------
        
        Question: {query}
        Answer:
        """
        
        try:
            # R: Generate response using Gemini
            response = self.model.generate_content(prompt)
            logger.info("GoogleLLMService: Response generated successfully")
            
            # R: Return cleaned response text
            return response.text.strip()
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"GoogleLLMService: Generation failed: {e}")
            raise LLMError(f"Failed to generate response: {e}")
