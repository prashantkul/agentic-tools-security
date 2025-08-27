"""
LLM Backend for Travel Advisor Agent
Supports multiple LLM providers (Anthropic Claude, Google Gemini)
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import json

class LLMBackend(ABC):
    """Abstract base class for LLM backends"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the LLM provider"""
        pass

class AnthropicBackend(LLMBackend):
    """Anthropic Claude backend"""
    
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                print("Warning: anthropic package not installed")
            except Exception as e:
                print(f"Warning: Failed to initialize Anthropic client: {e}")
    
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate response using Claude"""
        if not self.client:
            return "Error: Anthropic client not available"
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt or "You are a helpful travel advisor agent.",
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_provider_name(self) -> str:
        return "Anthropic Claude"

class GoogleBackend(LLMBackend):
    """Google Gemini backend"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.client = None
        
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel('gemini-1.5-flash')
            except ImportError:
                print("Warning: google-generativeai package not installed")
            except Exception as e:
                print(f"Warning: Failed to initialize Google client: {e}")
    
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate response using Gemini"""
        if not self.client:
            return "Error: Google client not available"
        
        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}"
            
            response = self.client.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_provider_name(self) -> str:
        return "Google Gemini"

class LLMManager:
    """Manages multiple LLM backends"""
    
    def __init__(self, preferred_provider: str = "anthropic"):
        self.backends = {
            "anthropic": AnthropicBackend(),
            "google": GoogleBackend()
        }
        
        self.preferred_provider = preferred_provider
        self.current_backend = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the preferred backend with fallback"""
        # Try preferred provider first
        if self.preferred_provider in self.backends:
            backend = self.backends[self.preferred_provider]
            if self._test_backend(backend):
                self.current_backend = backend
                return
        
        # Try fallback providers
        for name, backend in self.backends.items():
            if name != self.preferred_provider and self._test_backend(backend):
                self.current_backend = backend
                print(f"Fallback to {name} backend")
                return
        
        print("Warning: No LLM backend available")
    
    def _test_backend(self, backend: LLMBackend) -> bool:
        """Test if a backend is available"""
        if hasattr(backend, 'client') and backend.client:
            return True
        return False
    
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate response using current backend"""
        if not self.current_backend:
            return "I'm a travel advisor agent, but my AI backend is not available right now. Please try again later."
        
        return await self.current_backend.generate_response(prompt, system_prompt)
    
    def get_current_provider(self) -> str:
        """Get current provider name"""
        if self.current_backend:
            return self.current_backend.get_provider_name()
        return "None"
    
    def switch_provider(self, provider: str) -> bool:
        """Switch to a different provider"""
        if provider in self.backends:
            backend = self.backends[provider]
            if self._test_backend(backend):
                self.current_backend = backend
                self.preferred_provider = provider
                return True
        return False

# Example usage and testing
if __name__ == "__main__":
    async def test_llm_manager():
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test Anthropic backend
        print("Testing LLM Manager...")
        
        llm = LLMManager("anthropic")
        print(f"Current provider: {llm.get_current_provider()}")
        
        system_prompt = "You are a helpful travel advisor. Be concise and friendly."
        user_prompt = "What are the top 3 attractions in Tokyo?"
        
        response = await llm.generate_response(user_prompt, system_prompt)
        print(f"Response: {response[:200]}...")
        
        # Test switching providers
        if llm.switch_provider("google"):
            print(f"Switched to: {llm.get_current_provider()}")
            response2 = await llm.generate_response(user_prompt, system_prompt)
            print(f"Google response: {response2[:200]}...")
    
    asyncio.run(test_llm_manager())