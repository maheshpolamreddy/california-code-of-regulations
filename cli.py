"""
CLI Interface for CCR Compliance Agent
Interactive and single-query modes.
"""

import argparse
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from agent.compliance_advisor import ComplianceAdvisor
import config

console = Console()

def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║          CCR COMPLIANCE AGENT                                 ║
║          California Code of Regulations Advisor               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")
    console.print("Ask questions about CCR regulations for your facility\n", style="dim")

def display_answer(result: dict):
    """Display agent answer with rich formatting."""
    
    # Display main answer
    console.print("\n" + "="*70 + "\n", style="bold")
    answer_md = Markdown(result['answer'])
    console.print(answer_md)
    
    # Display citations
    if result.get('citations'):
        console.print("\n" + "="*70, style="bold")
        console.print("\n📚 Citations & Source URLs:\n", style="bold cyan")
        
        for idx, citation in enumerate(result['citations'], 1):
            console.print(f"{idx}. {citation['citation']}", style="bold yellow")
            console.print(f"   {citation['heading']}", style="italic")
            console.print(f"   🔗 {citation['url']}", style="blue underline")
            console.print(f"   Relevance: {citation.get('similarity', 0):.2%}\n", style="dim")
    
    # Display metadata
    console.print("="*70, style="bold")
    console.print(f"Retrieved {result['sections_retrieved']} relevant sections", style="dim")
    if result.get('facility_type'):
        console.print(f"Detected facility type: {result['facility_type']}", style="dim")
    console.print()

def interactive_mode():
    """Run in interactive conversational mode."""
    print_banner()
    
    console.print("💡 Tips:", style="bold green")
    console.print("  - Be specific about your facility type (restaurant, theater, farm, etc.)")
    console.print("  - Ask about specific operations or requirements")
    console.print("  - Type 'quit' or 'exit' to end\n")
    
    advisor = ComplianceAdvisor()
    
    while True:
        try:
            # Get user query
            query = Prompt.ask("\n[bold green]Your Question[/bold green]")
            
            if query.lower() in ['quit', 'exit', 'q']:
                console.print("\n👋 Goodbye! Stay compliant!\n", style="bold blue")
                break
            
            if not query.strip():
                continue
            
            # Process query
            console.print("\n🔍 Searching CCR regulations...", style="italic")
            result = advisor.answer_query(query)
            
            # Display result
            display_answer(result)
            
        except KeyboardInterrupt:
            console.print("\n\n👋 Goodbye!\n", style="bold blue")
            break
        except Exception as e:
            console.print(f"\n❌ Error: {e}\n", style="bold red")

def single_query_mode(query: str, title: int = None):
    """Run single query mode."""
    print_banner()
    
    console.print(f"[bold]Query:[/bold] {query}\n")
    
    advisor = ComplianceAdvisor()
    
    console.print("🔍 Searching CCR regulations...\n", style="italic")
    result = advisor.answer_query(query, title_number=title)
    
    display_answer(result)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CCR Compliance Agent - Get regulatory advice for your facility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python cli.py
  
  # Single query
  python cli.py --query "What regulations apply to restaurants?"
  
  # Query with title filter
  python cli.py --query "Food safety requirements" --title 17
        """
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Single query to ask (non-interactive mode)'
    )
    
    parser.add_argument(
        '--title', '-t',
        type=int,
        help='Filter by CCR title number (e.g., 17 for Public Health)'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Force interactive mode (default if no query provided)'
    )
    
    args = parser.parse_args()
    
    # Check if Supabase is configured
    if not config.SUPABASE_URL or not config.OPENAI_API_KEY:
        console.print("\n❌ Error: Missing required environment variables\n", style="bold red")
        console.print("Please configure .env file with:")
        console.print("  - OPENAI_API_KEY")
        console.print("  - SUPABASE_URL")
        console.print("  - SUPABASE_SERVICE_KEY\n")
        console.print(f"See .env.example for template\n", style="dim")
        sys.exit(1)
    
    try:
        if args.query:
            # Single query mode
            single_query_mode(args.query, args.title)
        else:
            # Interactive mode
            interactive_mode()
    except Exception as e:
        console.print(f"\n❌ Fatal error: {e}\n", style="bold red")
        sys.exit(1)

if __name__ == "__main__":
    main()
