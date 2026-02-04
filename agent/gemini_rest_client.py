
"""
Lightweight Gemini REST Client
Replaces the heavy google-generativeai SDK (which pulls in grpcio, 100MB+)
Uses simple HTTP requests to call Gemini API.
"""

import json
import requests
import time
import config
from typing import List, Dict, Union, Optional
from logger import agent_logger

class GeminiRESTClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def generate_content(
        self, 
        model_name: str, 
        prompt: str, 
        system_instruction: str = None
    ) -> str:
        """
        Generate content using Gemini API REST endpoint.
        """
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}" if "models/" not in model_name else model_name
            # Handle "gemini-2.0-flash" -> "models/gemini-2.0-flash"

        # Handle simple model names like "gemini-2.0-flash"
        if "/" not in model_name:
             model_name = f"models/{model_name}"

        url = f"{self.base_url}/{model_name.split('/')[-1]}:generateContent?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Build contents
        contents = [{"parts": [{"text": prompt}]}]
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.AGENT_TEMPERATURE,
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract text
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text
            except (KeyError, IndexError):
                # Check for safety blocks
                if "promptFeedback" in data:
                    agent_logger.warning(f"Safety Feedback: {data['promptFeedback']}")
                return "Error: No content generated (Safety block or empty response)."

        except Exception as e:
            agent_logger.error(f"Gemini REST Error: {e}")
            raise

    def embed_content(
        self, 
        model_name: str, 
        text: str, 
        task_type: str = "retrieval_document"
    ) -> List[float]:
        """
        Generate embedding using Gemini API REST endpoint.
        Task types: "retrieval_query", "retrieval_document"
        """
        # Map task type to API enum string if needed, but string usually works
        # API expects: RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT
        task_type_enum = task_type.upper()
        
        if "/" not in model_name:
             model_name = f"models/{model_name}"

        url = f"{self.base_url}/{model_name.split('/')[-1]}:embedContent?key={self.api_key}"
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": model_name,
            "content": {"parts": [{"text": text}]},
            "taskType": task_type_enum
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]["values"]
        except Exception as e:
            agent_logger.error(f"Gemini Embedding Error: {e}")
            raise
