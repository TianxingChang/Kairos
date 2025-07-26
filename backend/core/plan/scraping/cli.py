"""Command-line interface for the Firecrawl Learning Scraper."""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import signal

import colorama
from colorama import Fore, Style, Back

from .config.firecrawl_config import FirecrawlConfig
from .firecrawl_scraper_app import FirecrawlScraperApplication, ApplicationConfig


# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)


class CLIProgressDisplay:
    """Handles progress display in the CLI."""
    
    def __init__(self, verbose: bool = False):
        """Initialize progress display.
        
        Args:
            verbose: Whether to show detailed progress information
        """
        self.verbose = verbose
        self.current_operation = None
        self.items_processed = 0
        self.total_items = 0
    
    def update_progress(self, operation_type: str, progress_data: Dict[str, Any]):
        """Update progress display.
        
        Args:
            operation_type: Type of operation (search, crawl, process, etc.)
            progress_data: Progress information
        """
        status = progress_data.get('status', 'unknown')
        
        if operation_type == 'session':
            if status == 'started':
                print(f"{Fore.GREEN}🚀 Started scraping session: {progress_data.get('session_id', 'unknown')}")
            elif status == 'ended':
                print(f"{Fore.BLUE}✅ Session completed successfully")
                if self.verbose and 'summary' in progress_data:
                    self._print_session_summary(progress_data['summary'])
        
        elif operation_type == 'command':
            if status == 'parsing':
                print(f"{Fore.YELLOW}🧠 Processing command: {progress_data.get('input', '')[:50]}...")
            elif status == 'completed':
                if progress_data.get('success'):
                    duration = progress_data.get('duration', 0)
                    print(f"{Fore.GREEN}✅ Command completed in {duration:.1f}s")
                else:
                    print(f"{Fore.RED}❌ Command failed")
        
        elif operation_type == 'search':
            if status == 'starting':
                topic = progress_data.get('topic', 'unknown')
                print(f"{Fore.CYAN}🔍 Searching for learning resources on: {topic}")
            elif status == 'found_resources':
                count = progress_data.get('count', 0)
                print(f"{Fore.GREEN}📚 Found {count} learning resources")
            elif status == 'completed':
                items = progress_data.get('items_processed', 0)
                print(f"{Fore.BLUE}🎯 Search workflow completed - {items} items processed")
        
        elif operation_type == 'crawl':
            if status == 'starting':
                url = progress_data.get('url', 'unknown')
                print(f"{Fore.MAGENTA}🕷️  Crawling: {url}")
            elif status == 'processing':
                current = progress_data.get('current', 0)
                total = progress_data.get('total', 0)
                url = progress_data.get('url', 'unknown')
                print(f"{Fore.YELLOW}📄 Processing [{current}/{total}]: {url[:60]}...")
            elif status == 'completed':
                if progress_data.get('success'):
                    print(f"{Fore.GREEN}✅ Crawling completed")
                else:
                    print(f"{Fore.RED}❌ Crawling failed")
        
        elif operation_type == 'extract':
            if status == 'extracting':
                print(f"{Fore.CYAN}🔧 Extracting content structure...")
        
        elif operation_type == 'download':
            if status == 'downloading':
                count = progress_data.get('count', 0)
                print(f"{Fore.BLUE}📥 Downloading {count} media files...")
        
        elif operation_type == 'process':
            if status == 'processing':
                print(f"{Fore.YELLOW}⚙️  Processing and formatting content...")
        
        elif operation_type == 'store':
            if status == 'storing':
                topic = progress_data.get('topic', 'unknown')
                print(f"{Fore.GREEN}💾 Storing content for topic: {topic}")
        
        # Update progress counters for verbose mode
        if self.verbose and 'current' in progress_data and 'total' in progress_data:
            self.items_processed = progress_data['current']
            self.total_items = progress_data['total']
            self._print_progress_bar()
    
    def _print_progress_bar(self):
        """Print a progress bar for verbose mode."""
        if self.total_items > 0:
            percentage = (self.items_processed / self.total_items) * 100
            bar_length = 30
            filled_length = int(bar_length * self.items_processed // self.total_items)
            
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            print(f"\r{Fore.BLUE}Progress: |{bar}| {percentage:.1f}% ({self.items_processed}/{self.total_items})", end='')
            
            if self.items_processed == self.total_items:
                print()  # New line when complete
    
    def _print_session_summary(self, summary: Dict[str, Any]):
        """Print session summary in verbose mode."""
        print(f"{Fore.CYAN}\n📊 Session Summary:")
        print(f"   Duration: {summary.get('duration_seconds', 0):.1f} seconds")
        print(f"   Items processed: {summary.get('items_processed', 0)}")
        print(f"   Topics covered: {len(summary.get('topics_covered', []))}")
        print(f"   Sources used: {len(summary.get('sources_used', []))}")
        
        if summary.get('content_breakdown'):
            print(f"   Content breakdown:")
            for content_type, count in summary['content_breakdown'].items():
                print(f"     - {content_type}: {count}")


class InteractiveCLI:
    """Interactive command-line interface."""
    
    def __init__(self, app: FirecrawlScraperApplication, verbose: bool = False):
        """Initialize interactive CLI.
        
        Args:
            app: Firecrawl scraper application instance
            verbose: Whether to show verbose output
        """
        self.app = app
        self.verbose = verbose
        self.progress_display = CLIProgressDisplay(verbose)
        self.running = True
        
        # Add progress callback
        self.app.add_progress_callback(self.progress_display.update_progress)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n{Fore.YELLOW}⚠️  Received shutdown signal. Cleaning up...")
        self.running = False
    
    async def run(self):
        """Run the interactive CLI."""
        self._print_welcome()
        
        # Start application session
        session_id = await self.app.start_session()
        
        try:
            while self.running:
                try:
                    # Get user input
                    user_input = input(f"\n{Fore.GREEN}scraper>{Style.RESET_ALL} ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle special commands
                    if user_input.lower() in ['exit', 'quit', 'q']:
                        break
                    elif user_input.lower() in ['help', 'h']:
                        self._print_help()
                        continue
                    elif user_input.lower() in ['status', 'st']:
                        self._print_status()
                        continue
                    elif user_input.lower() in ['history', 'hist']:
                        self._print_history()
                        continue
                    elif user_input.lower().startswith('search '):
                        query = user_input[7:].strip()
                        self._search_stored_content(query)
                        continue
                    elif user_input.lower() in ['report', 'r']:
                        await self._generate_report()
                        continue
                    elif user_input.lower() in ['duplicates', 'dup']:
                        await self._check_duplicates()
                        continue
                    
                    # Process natural language command
                    result = await self.app.process_natural_language_command(user_input)
                    
                    # Display results
                    self._display_operation_result(result)
                
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}⚠️  Use 'exit' to quit gracefully")
                except EOFError:
                    break
                except Exception as e:
                    print(f"{Fore.RED}❌ Error: {e}")
                    if self.verbose:
                        import traceback
                        traceback.print_exc()
        
        finally:
            # End session
            session_data = await self.app.end_session()
            print(f"\n{Fore.BLUE}📋 Session ended. Duration: {session_data.get('duration_seconds', 0):.1f}s")
    
    def _print_welcome(self):
        """Print welcome message."""
        print(f"{Fore.CYAN}{Style.BRIGHT}")
        print("🔥 Firecrawl Learning Scraper 🕷️")
        print("=" * 50)
        print(f"{Style.RESET_ALL}")
        print("Welcome! I can help you find and organize learning resources.")
        print("Try commands like:")
        print(f"  {Fore.YELLOW}• 'Find Python programming tutorials'")
        print(f"  • 'Crawl https://docs.python.org/3/tutorial/'")
        print(f"  • 'Search for machine learning courses'")
        print(f"{Style.RESET_ALL}")
        print(f"Type {Fore.CYAN}'help'{Style.RESET_ALL} for more commands or {Fore.RED}'exit'{Style.RESET_ALL} to quit.")
    
    def _print_help(self):
        """Print help information."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Available Commands:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Natural Language Commands:")
        print(f"  • Find/search [topic] - Search for learning resources")
        print(f"  • Crawl [URL] - Extract content from a specific URL")
        print(f"  • Learn [topic] - Find tutorials and guides")
        print(f"\n{Fore.YELLOW}Special Commands:")
        print(f"  • help (h) - Show this help message")
        print(f"  • status (st) - Show current session status")
        print(f"  • history (hist) - Show operation history")
        print(f"  • search [query] - Search stored content")
        print(f"  • report (r) - Generate comprehensive report")
        print(f"  • duplicates (dup) - Check for duplicate content")
        print(f"  • exit/quit (q) - Exit the application")
        print(f"{Style.RESET_ALL}")
    
    def _print_status(self):
        """Print current status."""
        status = self.app.get_session_status()
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Session Status:{Style.RESET_ALL}")
        
        if status['status'] == 'no_active_session':
            print(f"{Fore.YELLOW}No active session")
        else:
            print(f"Session ID: {status['session_id']}")
            print(f"Started: {status['start_time']}")
            print(f"Operations: {status['operations_count']}")
            print(f"Items found: {status['total_items_found']}")
            print(f"Items stored: {status['total_items_stored']}")
            
            if status['errors_count'] > 0:
                print(f"{Fore.RED}Errors: {status['errors_count']}")
            if status['warnings_count'] > 0:
                print(f"{Fore.YELLOW}Warnings: {status['warnings_count']}")
    
    def _print_history(self):
        """Print operation history."""
        history = self.app.get_operation_history()
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Operation History:{Style.RESET_ALL}")
        
        if not history:
            print("No operations performed yet")
            return
        
        for i, op in enumerate(history[-10:], 1):  # Show last 10 operations
            status_icon = "✅" if op['success'] else "❌"
            duration = op['duration_seconds']
            op_type = op['operation_type']
            items = op['items_processed']
            
            print(f"{i:2d}. {status_icon} {op_type} - {items} items in {duration:.1f}s")
    
    def _search_stored_content(self, query: str):
        """Search stored content and display results."""
        results = self.app.search_stored_content(query=query)
        
        print(f"\n{Fore.CYAN}🔍 Search Results for '{query}':{Style.RESET_ALL}")
        
        if not results:
            print("No matching content found")
            return
        
        for i, item in enumerate(results[:10], 1):  # Show top 10 results
            title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
            content_type = item['content_type']
            topic = item['topic']
            size_mb = item['file_size_bytes'] / (1024 * 1024) if item['file_size_bytes'] > 0 else 0
            
            print(f"{i:2d}. {Fore.YELLOW}{title}")
            print(f"    Type: {content_type} | Topic: {topic} | Size: {size_mb:.1f}MB")
    
    async def _generate_report(self):
        """Generate and display comprehensive report."""
        print(f"{Fore.CYAN}📊 Generating comprehensive report...")
        
        try:
            exported_files = await self.app.generate_comprehensive_report()
            
            print(f"{Fore.GREEN}✅ Report generated successfully!")
            print("Files created:")
            
            for report_type, file_path in exported_files.items():
                print(f"  • {report_type}: {file_path}")
        
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to generate report: {e}")
    
    async def _check_duplicates(self):
        """Check for duplicate content."""
        print(f"{Fore.CYAN}🔍 Checking for duplicate content...")
        
        try:
            duplicate_report = await self.app.cleanup_duplicates(dry_run=True)
            
            duplicates_found = duplicate_report['total_duplicates_found']
            groups = duplicate_report['duplicate_groups_count']
            affected_items = duplicate_report['items_with_duplicates']
            
            if duplicates_found == 0:
                print(f"{Fore.GREEN}✅ No duplicates found - collection is clean!")
            else:
                print(f"{Fore.YELLOW}⚠️  Found {duplicates_found} duplicate matches")
                print(f"   Affecting {affected_items} items in {groups} groups")
                
                if 'recommendations' in duplicate_report:
                    print(f"\n{Fore.CYAN}Recommendations:")
                    for rec in duplicate_report['recommendations']:
                        print(f"  • {rec}")
        
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to check duplicates: {e}")
    
    def _display_operation_result(self, result):
        """Display the result of an operation."""
        if result.success:
            print(f"{Fore.GREEN}✅ Operation completed successfully!")
            
            if result.operation_type == "topic_search":
                resources_found = result.results.get('resources_found', 0)
                resources_processed = result.results.get('resources_processed', 0)
                topic = result.results.get('topic', 'unknown')
                
                print(f"   Topic: {topic}")
                print(f"   Resources found: {resources_found}")
                print(f"   Resources processed: {resources_processed}")
            
            elif result.operation_type == "url_crawl":
                url = result.results.get('url', 'unknown')
                topic = result.results.get('topic', 'unknown')
                
                print(f"   URL: {url}")
                print(f"   Categorized as: {topic}")
            
            if self.verbose and result.results:
                print(f"\n{Fore.CYAN}Detailed Results:")
                print(json.dumps(result.results, indent=2, default=str))
        
        else:
            print(f"{Fore.RED}❌ Operation failed")
            
            if result.errors:
                print(f"{Fore.RED}Errors:")
                for error in result.errors:
                    print(f"  • {error}")
            
            # Handle clarification questions
            if 'clarification_questions' in result.results:
                print(f"{Fore.YELLOW}❓ I need clarification:")
                for question in result.results['clarification_questions']:
                    print(f"  • {question}")
        
        if result.warnings:
            print(f"{Fore.YELLOW}Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")


async def run_interactive_mode(
    firecrawl_config: FirecrawlConfig,
    app_config: ApplicationConfig,
    verbose: bool = False
):
    """Run the interactive CLI mode."""
    async with FirecrawlScraperApplication(firecrawl_config, app_config) as app:
        cli = InteractiveCLI(app, verbose)
        await cli.run()


async def run_single_command(
    command: str,
    firecrawl_config: FirecrawlConfig,
    app_config: ApplicationConfig,
    verbose: bool = False
):
    """Run a single command and exit."""
    progress_display = CLIProgressDisplay(verbose)
    
    async with FirecrawlScraperApplication(firecrawl_config, app_config) as app:
        # Add progress callback
        app.add_progress_callback(progress_display.update_progress)
        
        # Process the command
        result = await app.process_natural_language_command(command)
        
        # Display results
        if result.success:
            print(f"{Fore.GREEN}✅ Command completed successfully!")
            
            if verbose:
                print(f"\n{Fore.CYAN}Results:")
                print(json.dumps(result.results, indent=2, default=str))
        else:
            print(f"{Fore.RED}❌ Command failed")
            
            for error in result.errors:
                print(f"{Fore.RED}Error: {error}")
            
            # Handle clarification questions
            if 'clarification_questions' in result.results:
                print(f"{Fore.YELLOW}Clarification needed:")
                for question in result.results['clarification_questions']:
                    print(f"  {question}")
        
        return 0 if result.success else 1


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Firecrawl Learning Scraper - Find and organize learning resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --interactive                    # Start interactive mode
  %(prog)s "Find Python tutorials"         # Run single command
  %(prog)s "Crawl https://example.com"     # Crawl specific URL
  
Interactive Commands:
  Find machine learning courses
  Search for JavaScript tutorials
  Crawl https://docs.python.org/3/tutorial/
  Learn about web development
        """
    )
    
    # Command options
    parser.add_argument(
        'command',
        nargs='?',
        help='Natural language command to execute (if not provided, starts interactive mode)'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Start interactive mode'
    )
    
    # Configuration options
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--storage-path',
        type=Path,
        default=Path.cwd() / "scraped_content",
        help='Base path for storing scraped content (default: ./scraped_content)'
    )
    
    parser.add_argument(
        '--mcp-server-url',
        default='http://localhost:8000',
        help='Firecrawl MCP server URL (default: http://localhost:8000)'
    )
    
    # Output options
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--no-download',
        action='store_true',
        help='Disable automatic video downloads'
    )
    
    parser.add_argument(
        '--no-reports',
        action='store_true',
        help='Disable automatic report generation'
    )
    
    parser.add_argument(
        '--export-format',
        choices=['markdown', 'json', 'html'],
        action='append',
        help='Export formats for processed content (can be specified multiple times)'
    )
    
    # Logging options
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        help='Path to log file (if not specified, logs to console)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if args.log_file:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            filename=args.log_file,
            filemode='a'
        )
    else:
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
    
    # Create configurations
    firecrawl_config = FirecrawlConfig(
        mcp_server_url=args.mcp_server_url
    )
    
    app_config = ApplicationConfig(
        storage_base_path=args.storage_path,
        auto_download_videos=not args.no_download,
        auto_generate_reports=not args.no_reports,
        export_formats=args.export_format or ['markdown', 'json']
    )
    
    # Ensure storage directory exists
    app_config.storage_base_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Determine mode
        if args.interactive or not args.command:
            # Interactive mode
            await run_interactive_mode(firecrawl_config, app_config, args.verbose)
            return 0
        else:
            # Single command mode
            return await run_single_command(
                args.command, firecrawl_config, app_config, args.verbose
            )
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"{Fore.RED}❌ Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))