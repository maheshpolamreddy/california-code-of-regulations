import json
import numpy as np
import re
from pathlib import Path
from typing import List, Dict, Optional
from vectordb.embedder import TextEmbedder
import config

class LocalOfflineAdvisor:
    def __init__(self):
        self.embedder = TextEmbedder()
        self.sections = []
        self.load_sections()
        
    def load_sections(self):
        sections_file = Path(config.DATA_DIR) / "extracted_sections.jsonl"
        if sections_file.exists():
            with open(sections_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        sec = json.loads(line)
                        content = sec.get("content_markdown", "")
                        
                        # 1. Parse hierarchy
                        lines = [l.strip() for l in content.split('\n') if l.strip()]
                        hierarchy = []
                        title_num = None
                        for l in lines:
                            for keyword in ['Title', 'Division', 'Subdivision', 'Chapter', 'Subchapter', 'Article']:
                                if l.startswith(keyword):
                                    hierarchy.append(l)
                                    if keyword == 'Title':
                                        t_match = re.match(r'Title\s*(\d+)', l)
                                        if t_match:
                                            title_num = int(t_match.group(1))
                                    break
                                    
                        if hierarchy:
                            sec["breadcrumb_path"] = " > ".join(hierarchy)
                        if title_num is not None:
                            sec["title_number"] = title_num
                            
                        # 2. Fix citation
                        heading = sec.get("section_heading", "")
                        h_match = re.match(r'§\s*(.+?)\.\s', heading)
                        if h_match:
                            real_sec_num = h_match.group(1).strip()
                            sec["section_number"] = real_sec_num
                            if title_num is not None:
                                sec["citation"] = f"{title_num} CCR § {real_sec_num}"
                                
                        self.sections.append(sec)
            print(f"Loaded {len(self.sections)} local sections for offline mode.")
        else:
            print("Local extracted_sections.jsonl not found!")
            
    def extract_facility_type(self, query: str) -> Optional[str]:
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
        
    def answer_query(self, query: str, title_number: Optional[int] = None, include_context: bool = False, min_similarity: float = 0.5) -> Dict[str, any]:
        # Filter by title first if provided
        filtered_sections = self.sections
        if title_number is not None:
            filtered_sections = [sec for sec in self.sections if sec.get("title_number") == title_number]
            if not filtered_sections:  # fallback if no sections in this title
                filtered_sections = self.sections

        # Simple keyword matching to find candidates
        query_words = set(query.lower().replace("?", "").replace(",", "").split())
        stop_words = {"what", "are", "the", "apply", "to", "for", "in", "of", "a", "an", "is", "and", "or", "how", "do", "does", "regulations", "rules", "laws"}
        keywords = [w for w in query_words if w not in stop_words and len(w) > 2]
        
        candidates = []
        for sec in filtered_sections:
            content = (sec.get("content_markdown", "") + " " + sec.get("section_heading", "") + " " + sec.get("citation", "")).lower()
            match_count = sum(1 for kw in keywords if kw in content)
            if match_count > 0:
                candidates.append((match_count, sec))
                
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [item[1] for item in candidates[:30]]
        
        if not top_candidates:
            top_candidates = filtered_sections[:10]
            
        query_emb = np.array(self.embedder.embed_text(query, task_type="retrieval_query"))
        
        results = []
        for sec in top_candidates:
            try:
                text_to_embed = sec.get("content_markdown", "")[:1000]
                sec_emb = np.array(self.embedder.embed_text(text_to_embed))
                similarity = float(np.dot(query_emb, sec_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(sec_emb)))
            except Exception as e:
                similarity = 0.5
                
            sec_copy = sec.copy()
            sec_copy["similarity"] = similarity
            results.append(sec_copy)
            
        results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = [r for r in results[:5] if r.get("similarity", 0.5) >= min_similarity]
        if not top_results:
            top_results = results[:3] # fallback
        
        facility_type = self.extract_facility_type(query)
        
        answer = f"### California Code of Regulations - Offline Analysis\n\n"
        answer += f"Running in **Local Offline RAG Mode** (matched on {len(self.sections)} local protocols using FastEmbed).\n\n"
        answer += f"Based on your query, here are the most relevant CCR sections found:\n\n"
        
        for idx, sec in enumerate(top_results, 1):
            citation = sec.get("citation") or f"Title {sec.get('title_number')} CCR Section {sec.get('section_number')}"
            heading = sec.get("section_heading") or "Untitled Regulation"
            path = sec.get("breadcrumb_path") or f"Title {sec.get('title_number')}"
            summary = sec.get("content_markdown", "")[:400]
            if len(sec.get("content_markdown", "")) > 400:
                summary += "..."
                
            answer += f"#### {idx}. {citation}: {heading}\n"
            answer += f"- **Applicability:** Applies to facility operations matching query parameters.\n"
            answer += f"- **Hierarchy:** `{path}`\n"
            answer += f"- **Summary:** {summary}\n\n"
            
        if facility_type:
            answer += f"**Detected Facility Type:** {facility_type.capitalize()}\n\n"
            answer += f"**Follow-up Questions:**\n"
            answer += f"1. Are there specific aspects of your {facility_type} operations (e.g. food prep, waste disposal) you'd like to check?\n"
            answer += f"2. Is your facility seasonal or operating year-round?\n\n"
            
        answer += "---\n"
        answer += "*Disclaimer: This is informational guidance based on the CCR and is not legal advice. Consult a qualified attorney for legal advice.*"
        
        citations = []
        for sec in top_results:
            citations.append({
                "citation": sec.get("citation") or f"Title {sec.get('title_number')} CCR Section {sec.get('section_number')}",
                "heading": sec.get("section_heading") or "Untitled Regulation",
                "url": sec.get("source_url") or sec.get("section_url") or "",
                "similarity": sec.get("similarity", 0.5)
            })
            
        return {
            "answer": answer,
            "citations": citations,
            "sections_retrieved": len(top_results),
            "facility_type": facility_type
        }
