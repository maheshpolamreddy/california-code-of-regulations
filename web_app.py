"""
CCR Compliance Agent - Web Interface
Flask application for running the agent in a browser with enhanced features
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sys
import asyncio
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from agent.compliance_advisor import ComplianceAdvisor
from vectordb.supabase_client import SupabaseVectorDB
import config

app = Flask(__name__)
CORS(app)  # Enable CORS for API access
advisor = None
vectordb = None
stats_cache = {'data': None, 'timestamp': None}
CACHE_DURATION = timedelta(seconds=30)

def init_agent():
    """Initialize the compliance advisor"""
    global advisor, vectordb
    try:
        advisor = ComplianceAdvisor()
        vectordb = SupabaseVectorDB()
        return True
    except Exception as e:
        print(f"Error initializing agent: {e}")
        return False

@app.route('/')
def index():
    """Render the main dashboard"""
    return render_template('web_interface.html')

@app.route('/api/stats')
def get_stats():
    """Get system statistics with caching."""
    global stats_cache
    
    # Check cache
    if stats_cache['data'] and stats_cache['timestamp']:
        if datetime.now() - stats_cache['timestamp'] < CACHE_DURATION:
            return jsonify(stats_cache['data'])
    
    try:
        # Safety check: ensure vectordb is initialized
        if not vectordb:
            return jsonify({
                'error': 'Database not initialized',
                'status': 'offline',
                'sections_indexed': 0,
                'embedding_model': config.EMBEDDING_MODEL,
                'agent_model': config.AGENT_MODEL,
                'embedding_dimension': config.EMBEDDING_DIMENSION
            }), 503
            
        section_count = vectordb.count_sections()
        stats_data = {
            'sections_indexed': section_count,
            'embedding_model': config.EMBEDDING_MODEL,
            'agent_model': config.AGENT_MODEL,
            'embedding_dimension': config.EMBEDDING_DIMENSION,
            'status': 'online' if advisor else 'offline',
            'timestamp': datetime.now().isoformat()
        }
        
        # Update cache
        stats_cache['data'] = stats_data
        stats_cache['timestamp'] = datetime.now()
        
        return jsonify(stats_data)
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/query', methods=['POST'])
def query_agent():
    """Handle agent queries with enhanced error handling."""
    try:
        # Validate request
        if not request.json:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON payload'
            }), 400
        
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        if len(query) > 1000:
            return jsonify({
                'success': False,
                'error': 'Query too long (max 1000 characters)'
            }), 400
        
        if not advisor:
            return jsonify({
                'success': False,
                'error': 'Agent not initialized. Please check server logs.'
            }), 500
        
        # Run the query
        result = advisor.answer_query(
            query=query,
            include_context=True
        )
        
        return jsonify({
            'success': True,
            'answer': result['answer'],
            'citations': result['citations'],
            'sections_retrieved': result.get('sections_retrieved', 0),
            'facility_type': result.get('facility_type'),
            'query_processed_at': datetime.now().isoformat()
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid query: {str(e)}'
        }), 400
    except ConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Database connection error. Please try again.'
        }), 503
    except Exception as e:
        print(f"Query error: {e}")
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'agent_ready': advisor is not None,
        'database_ready': vectordb is not None
    })

if __name__ == '__main__':
    print("=" * 70)
    print("CCR COMPLIANCE AGENT - WEB INTERFACE")
    print("=" * 70)
    print("\nInitializing agent...")
    
    if init_agent():
        print("✅ Agent initialized successfully!")
        print(f"\nEmbedding Model: {config.EMBEDDING_MODEL}")
        print(f"Agent Model: {config.AGENT_MODEL}")
        print(f"Embedding Dimension: {config.EMBEDDING_DIMENSION}")
        
        section_count = vectordb.count_sections() if vectordb else 0
        print(f"\n📊 Indexed Sections: {section_count}")
        
        print("\n" + "=" * 70)
        print("🚀 Starting web server...")
        print("=" * 70)
        print("\n📱 Open your browser to: http://localhost:5000")
        print("\nPress CTRL+C to stop the server\n")
        
    if __import__("platform").system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # Production mode (Render, Gunicorn, etc.)
    init_agent()
