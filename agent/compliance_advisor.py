"""
Compliance Advisor Agent
LLM-powered agent that provides CCR compliance advice using RAG.
"""

from typing import List, Dict, Optional
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI
from agent.retriever import CCRRetriever
import config
from logger import agent_logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class ComplianceAdvisor:
    """
    AI agent that answers CCR compliance questions.
    Uses RAG to provide accurate, citation-backed advice.
    """
    
    def __init__(self):
        # Determine client type based on configured AGENT_MODEL
        if "gemini" in config.AGENT_MODEL and config.GEMINI_API_KEY:
            # Use lightweight REST client instead of heavy SDK
            from agent.gemini_rest_client import GeminiRESTClient
            self.client = GeminiRESTClient(api_key=config.GEMINI_API_KEY)
            self.client_type = "gemini"
            agent_logger.info("Using Gemini REST Client for agent")
        elif config.OPENAI_API_KEY:
            from openai import OpenAI
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.client_type = "openai"
            agent_logger.info("Using OpenAI for agent")
        else:
            raise ValueError("No valid API key found for configured agent model")
        
        self.retriever = CCRRetriever()
        self.conversation_history = []
        
    def build_system_prompt(self) -> str:
        """
        Create system prompt that defines agent behavior.
        """
        return """You are a California Code of Regulations (CCR) compliance advisor.

Your role is to help facility operators (e.g., restaurants, movie theaters, farms) understand which CCR regulations apply to them.

**CRITICAL RULES:**
1. **Only use information from the retrieved CCR sections** - Do NOT hallucinate or make up regulations. If no retrieved section applies, say so clearly.
2. **Always provide specific citations** (e.g., "17 CCR § 1234") and mention that source URLs are provided below.
3. **Explain WHY each section applies** to the user's facility type or question.
4. **Ask follow-up questions** when information is insufficient (e.g., "What type of food do you serve?", "Is this a seasonal or year-round operation?", "Which county?") so you can narrow applicable regulations.
5. **Be helpful but cautious** - recommend consulting qualified legal counsel for specific compliance decisions.
6. **Include this disclaimer in every response:** "This is informational guidance based on the CCR and is not legal advice. Consult a qualified attorney for legal advice."

**Response Format:**
- Brief summary of applicability
- List each applicable CCR section with citation, why it applies, and (below) source URL
- If needed: 1–2 short follow-up questions to clarify scope
- End with the disclaimer above

**Tone:** Professional, helpful, precise, non-alarmist."""

    def extract_facility_type(self, query: str) -> Optional[str]:
        """
        Extract facility type from query using simple keyword matching.
        """
        facility_types = {
            'restaurant': ['restaurant', 'cafe', 'diner', 'eatery', 'food service'],
            'movie theater': ['theater', 'theatre', 'cinema', 'movie'],
            'farm': ['farm', 'ranch', 'agricultural', 'farming'],
            'hospital': ['hospital', 'clinic', 'medical'],
            'school': ['school', 'university', 'college', 'educational'],
            'retail': ['store', 'shop', 'retail'],
        }
        
        query_lower = query.lower()
        for facility_type, keywords in facility_types.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return facility_type
        
        return None
    
    def answer_query(
        self,
        query: str,
        title_number: Optional[int] = None,
        include_context: bool = False
    ) -> Dict[str, any]:
        """
        Answer a compliance query using RAG.
        
        Args:
            query: User's question
            title_number: Optional CCR title filter
            include_context: Whether to include retrieved context in response
            
        Returns:
            Dict with answer, citations, and metadata
        """
        agent_logger.info(f"Processing query: {query[:100]}...")
        
        # Extract facility type
        facility_type = self.extract_facility_type(query)
        if facility_type:
            agent_logger.info(f"Detected facility type: {facility_type}")
        
        # Retrieve relevant sections
        sections = self.retriever.retrieve(
            query=query,
            title_number=title_number,
            facility_type=facility_type
        )
        
        if not sections:
            return {
                'answer': "I couldn't find any relevant CCR sections for your query. Please try rephrasing or providing more specific details about your facility type and operations.",
                'citations': [],
                'sections_retrieved': 0
            }
        
        # Build context for LLM
        context = self.retriever.build_context(sections)
        
        # Create messages for LLM
        messages = [
            {'role': 'system', 'content': self.build_system_prompt()},
            {'role': 'user', 'content': f"""Based on the following CCR sections, answer this query:

**Query:** {query}

**Retrieved CCR Sections:**
{context}

Please provide a comprehensive answer with specific citations and explanations."""}
        ]
        
        # Add conversation history if exists
        if self.conversation_history:
            messages.insert(1, {'role': 'assistant', 'content': 'I have context from our previous conversation.'})
        
        # Call LLM
        try:
            if self.client_type == "gemini":
                # Use Gemini (use configured model)
                # Client is now GeminiRESTClient
                
                # Add retry logic for rate limits (429)
                @retry(
                    stop=stop_after_attempt(5),
                    wait=wait_exponential(multiplier=2, min=4, max=60),
                    reraise=True
                )
                def generate_with_retry():
                    return self.client.generate_content(
                        model_name=config.AGENT_MODEL,
                        prompt=prompt,
                        system_instruction=self.build_system_prompt()
                    )

                answer = generate_with_retry()
            else:
                # Use OpenAI
                messages = [
                    {'role': 'system', 'content': self.build_system_prompt()},
                    {'role': 'user', 'content': f"""Based on the following CCR sections, answer this query:

**Query:** {query}

**Retrieved CCR Sections:**
{context}

Please provide a comprehensive answer with specific citations and explanations."""}
                ]
                
                # Add conversation history if exists
                if self.conversation_history:
                    messages.insert(1, {'role': 'assistant', 'content': 'I have context from our previous conversation.'})
                
                response = self.client.chat.completions.create(
                    model=config.AGENT_MODEL,
                    messages=messages,
                    temperature=config.AGENT_TEMPERATURE,
                    max_tokens=2000
                )
                answer = response.choices[0].message.content
            
            # Extract citations from retrieved sections
            citations = []
            for section in sections:
                url = section.get('source_url') or section.get('section_url') or ''
                # Normalize: strip #chunk0 etc. so link points to section page
                if '#chunk' in url:
                    url = url.split('#chunk')[0]
                citations.append({
                    'citation': section.get('citation'),
                    'heading': section.get('section_heading'),
                    'url': url,
                    'similarity': section.get('similarity')
                })
            
            # Add disclaimer if not already present
            if 'not legal advice' not in answer.lower():
                answer += "\n\n---\n**Disclaimer:** This is informational guidance based on CCR sections, not legal advice. Please consult with legal counsel for specific compliance questions."
            
            result = {
                'answer': answer,
                'citations': citations,
                'sections_retrieved': len(sections),
                'facility_type': facility_type
            }
            
            if include_context:
                result['context'] = context
            
            # Update conversation history
            self.conversation_history.append({
                'query': query,
                'answer': answer,
                'citations': citations
            })
            
            agent_logger.info(f"Generated answer with {len(citations)} citations")
            return result
            
        except Exception as e:
            agent_logger.error(f"Failed to generate answer: {e}")
            
            # Fallback: Process citations even if LLM failed
            citations = []
            for section in sections:
                url = section.get('source_url') or section.get('section_url') or ''
                if '#chunk' in url:
                    url = url.split('#chunk')[0]
                citations.append({
                    'citation': section.get('citation'),
                    'heading': section.get('section_heading'),
                    'url': url,
                    'similarity': section.get('similarity')
                })
            
            # Friendly error message for rate limits
            if "429" in str(e) or "quota" in str(e).lower():
                fallback_answer = "⚠️ **AI Rate Limit Reached**\n\nI couldn't generate a summary right now because of high traffic (Google Gemini Quote Exceeded). \n\n**However, I found these relevant regulations for you:**"
            else:
                fallback_answer = f"I encountered an error generating the summary: {str(e)}\n\n**Here are the relevant regulations found:**"

            return {
                'answer': fallback_answer,
                'citations': citations,
                'sections_retrieved': len(sections),
                'error': str(e)
            }
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        agent_logger.info("Conversation history cleared")
