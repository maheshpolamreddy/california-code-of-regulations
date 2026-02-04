"""
Retriever Module
Implements RAG (Retrieval-Augmented Generation) for CCR sections.
"""

from typing import List, Dict, Optional
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from vectordb.embedder import TextEmbedder
from vectordb.supabase_client import SupabaseVectorDB
import config
from logger import agent_logger

class CCRRetriever:
    """
    Retrieves relevant CCR sections using semantic search.
    Supports metadata filtering and re-ranking.
    """
    
    def __init__(self):
        self.embedder = TextEmbedder()
        self.vectordb = SupabaseVectorDB()
        
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        title_number: Optional[int] = None,
        facility_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve relevant CCR sections for a query.
        
        Args:
            query: User's question or search query
            top_k: Number of results to return (default from config)
            title_number: Optional filter by CCR title number
            facility_type: Optional facility type for context (e.g., 'restaurant')
            
        Returns:
            List of relevant sections with metadata and similarity scores
        """
        if top_k is None:
            top_k = config.MAX_RETRIEVAL_RESULTS
        
        # Enhance query with facility type if provided
        enhanced_query = query
        if facility_type:
            enhanced_query = f"Regulations for {facility_type} facilities: {query}"
        
        agent_logger.info(f"Retrieving sections for query: {enhanced_query[:100]}...")
        
        # Generate embedding for query (use "retrieval_query" task type for Gemini)
        query_embedding = self.embedder.embed_text(enhanced_query, task_type="retrieval_query")
        
        # Search vector database
        results = self.vectordb.search_similar(
            query_embedding=query_embedding,
            limit=top_k * 2,  # Get more for re-ranking
            title_number=title_number,
            min_similarity=0.5  # Minimum relevance threshold
        )
        
        # Re-rank and filter
        ranked_results = self.rerank_results(results, query, facility_type)
        
        # Return top K
        final_results = ranked_results[:top_k]
        
        agent_logger.info(f"Retrieved {len(final_results)} relevant sections")
        return final_results
    
    def rerank_results(
        self,
        results: List[Dict],
        query: str,
        facility_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Re-rank results based on additional heuristics.
        Boosts sections likely more relevant to facility type.
        """
        # Define facility type keywords for boosting
        facility_keywords = {
            'restaurant': ['food', 'kitchen', 'dining', 'restaurant', 'eating', 'sanitation', 'health'],
            'movie theater': ['theater', 'theatre', 'entertainment', 'venue', 'assembly', 'public gathering'],
            'farm': ['farm', 'agriculture', 'agricultural', 'crop', 'livestock', 'rural'],
            'hospital': ['hospital', 'medical', 'health care', 'patient', 'clinical'],
            'school': ['school', 'education', 'student', 'classroom', 'educational'],
        }
        
        for result in results:
            # Start with base similarity score
            score = result.get('similarity', 0.0)
            
            # Boost if facility type matches
            if facility_type and facility_type.lower() in facility_keywords:
                content = (result.get('content_markdown', '') + ' ' + 
                          result.get('section_heading', '')).lower()
                
                for keyword in facility_keywords[facility_type.lower()]:
                    if keyword in content:
                        score += 0.05  # Small boost per matching keyword
            
            result['final_score'] = score
        
        # Sort by final score descending
        results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        return results
    
    def format_section_for_context(self, section: Dict) -> str:
        """
        Format a retrieved section for LLM context.
        Creates a concise, informative representation.
        """
        formatted = f"""### {section.get('citation', 'Unknown')}
**Title:** {section.get('section_heading', 'Unknown')}
**Hierarchy:** {section.get('breadcrumb_path', 'N/A')}
**Source:** {section.get('source_url') or section.get('section_url', 'N/A')}

**Content:**
{section.get('content_markdown', '')[:1000]}...  

**Relevance Score:** {section.get('similarity', 0):.3f}

---
"""
        return formatted
    
    def build_context(self, sections: List[Dict]) -> str:
        """
        Build complete context from multiple retrieved sections.
        """
        if not sections:
            return "No relevant CCR sections found."
        
        context = f"Retrieved {len(sections)} relevant CCR sections:\n\n"
        for idx, section in enumerate(sections, 1):
            context += f"## Section {idx}\n\n"
            context += self.format_section_for_context(section)
        
        return context
