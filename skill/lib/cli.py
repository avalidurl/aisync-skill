#!/usr/bin/env python3
"""
AI Sessions Sync CLI
====================

Sync AI coding sessions from 12 tools to Obsidian, JSON, HTML, or SQLite.

Usage:
    aisync sync [--output DIR] [--format FORMAT] [--provider PROVIDER]
    aisync search QUERY [--provider PROVIDER] [--limit N]
    aisync stats [--format FORMAT]
    aisync report [--output FILE]
    aisync outputs
    aisync providers
    aisync status
    aisync config [KEY] [VALUE]
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

from . import (
    sync_all, get_default_vault, list_outputs, 
    get_all_parsers, SessionAnalyzer, SessionSearch,
    SearchOptions, __version__
)
from .analytics.insights import generate_report


HELP_TEXT = """
🤖 AI Sessions Sync v{version}

Sync AI coding sessions from 12 tools to multiple output formats.

COMMANDS:
  sync       Sync sessions to output format(s)
  search     Search across all sessions  
  stats      Show usage statistics
  report     Generate detailed report
  status     Show detected sessions
  providers  List supported AI tools
  outputs    List output formats
  config     Get/set configuration

QUICK START:
  aisync sync                    # Sync to Obsidian
  aisync sync -f json html       # Sync to JSON + HTML
  aisync search "function"       # Search sessions
  aisync stats                   # View statistics

SUPPORTED TOOLS:
  Claude Code, Codex CLI, Cursor, Aider, Cline,
  Gemini CLI, Continue, Copilot, Roo Code, 
  Windsurf, Zed AI, Amp

OUTPUT FORMATS:
  obsidian  Markdown with YAML frontmatter
  json      JSON files (single or per-session)
  jsonl     JSON Lines for streaming
  html      Static website with search
  sqlite    Database with full-text search

Run 'aisync <command> --help' for command details.
"""


def main():
    parser = argparse.ArgumentParser(
        prog='aisync',
        description='AI Sessions Sync - Sync AI coding sessions to various outputs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_TEXT.format(version=__version__)
    )
    
    parser.add_argument('-v', '--version', action='version', 
                       version=f'aisync {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # sync command
    sync_parser = subparsers.add_parser('sync', 
        help='Sync sessions to output format(s)',
        description='Sync AI coding sessions to Obsidian, JSON, HTML, or SQLite.',
        epilog='''
Examples:
  aisync sync                          Sync to Obsidian (auto-detected)
  aisync sync -o ~/ai-sessions         Custom output directory
  aisync sync -f obsidian json html    Multiple output formats
  aisync sync -p claude-code cursor    Only specific providers
  aisync sync -f sqlite --no-analyze   SQLite without analytics
''',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sync_parser.add_argument('-o', '--output', metavar='DIR',
                            help='Output directory (default: auto-detect Obsidian vault)')
    sync_parser.add_argument('-f', '--format', nargs='+', default=['obsidian'],
                            metavar='FMT',
                            help='Output format(s): obsidian, json, jsonl, html, sqlite')
    sync_parser.add_argument('-p', '--provider', nargs='+', metavar='PROV',
                            help='Only sync specific provider(s)')
    sync_parser.add_argument('--no-analyze', action='store_true', 
                            help='Skip analytics computation')
    sync_parser.add_argument('--json', action='store_true', 
                            help='Output results as JSON')
    
    # search command
    search_parser = subparsers.add_parser('search', 
        help='Search across all sessions',
        description='Full-text search across all AI coding sessions.',
        epilog='''
Examples:
  aisync search "async function"       Simple text search
  aisync search "error" -p cursor      Filter by provider
  aisync search "def \\w+\\(" --regex  Regex pattern
  aisync search "api" --json -l 50     JSON output, 50 results
''',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    search_parser.add_argument('query', help='Search query (text or regex)')
    search_parser.add_argument('-p', '--provider', metavar='PROV',
                              help='Filter by provider name')
    search_parser.add_argument('-l', '--limit', type=int, default=20, metavar='N',
                              help='Maximum results (default: 20)')
    search_parser.add_argument('--regex', action='store_true', 
                              help='Treat query as regex pattern')
    search_parser.add_argument('--json', action='store_true', 
                              help='Output results as JSON')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', 
        help='Show usage statistics',
        description='Display statistics about your AI coding sessions.')
    stats_parser.add_argument('-f', '--format', choices=['text', 'json'], default='text',
                             help='Output format (default: text)')
    
    # report command
    report_parser = subparsers.add_parser('report', 
        help='Generate detailed report',
        description='Generate a comprehensive report with insights.')
    report_parser.add_argument('-o', '--output', metavar='FILE',
                              help='Save to file (default: print to stdout)')
    
    # outputs command
    subparsers.add_parser('outputs', 
        help='List available output formats',
        description='Show all supported output formats with descriptions.')
    
    # providers command
    subparsers.add_parser('providers', 
        help='List supported AI tools',
        description='Show all 12 supported AI coding tools and detected sessions.')
    
    # status command
    subparsers.add_parser('status', 
        help='Show sync status',
        description='Display current configuration and detected sessions.')
    
    # config command
    config_parser = subparsers.add_parser('config', 
        help='Get/set configuration',
        description='Manage aisync configuration.',
        epilog='''
Examples:
  aisync config                        List all settings
  aisync config OBSIDIAN_VAULT         Get vault path
  aisync config OBSIDIAN_VAULT ~/Obs   Set vault path
''',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    config_parser.add_argument('key', nargs='?', metavar='KEY',
                              help='Configuration key')
    config_parser.add_argument('value', nargs='?', metavar='VALUE',
                              help='Value to set')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'sync':
            cmd_sync(args)
        elif args.command == 'search':
            cmd_search(args)
        elif args.command == 'stats':
            cmd_stats(args)
        elif args.command == 'report':
            cmd_report(args)
        elif args.command == 'outputs':
            cmd_outputs()
        elif args.command == 'providers':
            cmd_providers()
        elif args.command == 'status':
            cmd_status()
        elif args.command == 'config':
            cmd_config(args)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_sync(args):
    """Run sync."""
    print("🔄 Syncing AI sessions...")
    
    result = sync_all(
        output_dir=args.output,
        outputs=args.format,
        providers=args.provider,
        analyze=not args.no_analyze
    )
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n✅ Sync complete!")
        print(f"   📁 Output: {result['output_dir']}")
        print(f"   📊 Sessions: {result['sessions_total']}")
        print(f"   🔌 Providers: {', '.join(result['by_provider'].keys())}")
        
        if result.get('statistics'):
            stats = result['statistics']
            print(f"\n📈 Statistics:")
            print(f"   Total tokens: {stats.get('total_tokens', 0):,}")
            print(f"   Code blocks: {stats.get('total_code_blocks', 0):,}")
            if stats.get('by_language'):
                top_langs = list(stats['by_language'].keys())[:3]
                print(f"   Top languages: {', '.join(top_langs)}")


def cmd_search(args):
    """Search sessions."""
    # Parse all sessions
    all_sessions = []
    for provider, parser in get_all_parsers().items():
        if args.provider and provider.value != args.provider:
            continue
        all_sessions.extend(parser.parse_all())
    
    if not all_sessions:
        print("No sessions found.")
        return
    
    # Search
    search = SessionSearch(all_sessions)
    options = SearchOptions(
        query=args.query,
        provider=args.provider,
        limit=args.limit,
        regex=args.regex
    )
    results = search.search(options)
    
    if args.json:
        output = [{
            'session_id': r.session.id,
            'provider': r.session.provider.value,
            'date': r.session.date_str,
            'role': r.message.role.value,
            'content': r.message.content[:200],
            'score': r.score
        } for r in results]
        print(json.dumps(output, indent=2))
    else:
        print(f"🔍 Found {len(results)} results for '{args.query}'\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result.session.provider.value}] {result.session.date_str}")
            print(f"   {result.message.role.value}: {result.message.content[:100]}...")
            print()


def cmd_stats(args):
    """Show statistics."""
    # Parse and analyze
    all_sessions = []
    for provider, parser in get_all_parsers().items():
        all_sessions.extend(parser.parse_all())
    
    analyzer = SessionAnalyzer()
    all_sessions = analyzer.analyze_sessions(all_sessions)
    stats = analyzer.get_aggregate_stats(all_sessions)
    
    if args.format == 'json':
        print(json.dumps(stats, indent=2, default=str))
    else:
        print("📊 AI Sessions Statistics")
        print("=" * 40)
        print(f"Total sessions:  {stats.get('total_sessions', 0):,}")
        print(f"Total messages:  {stats.get('total_messages', 0):,}")
        print(f"Total tokens:    {stats.get('total_tokens', 0):,}")
        print(f"Code blocks:     {stats.get('total_code_blocks', 0):,}")
        print()
        
        print("By Provider:")
        for provider, count in stats.get('by_provider', {}).items():
            print(f"  {provider}: {count}")
        print()
        
        print("Top Languages:")
        for lang, count in list(stats.get('by_language', {}).items())[:5]:
            print(f"  {lang}: {count}")


def cmd_report(args):
    """Generate report."""
    # Parse and analyze
    all_sessions = []
    for provider, parser in get_all_parsers().items():
        all_sessions.extend(parser.parse_all())
    
    analyzer = SessionAnalyzer()
    all_sessions = analyzer.analyze_sessions(all_sessions)
    stats = analyzer.get_aggregate_stats(all_sessions)
    
    report = generate_report(all_sessions, stats)
    
    if args.output:
        Path(args.output).write_text(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


def cmd_outputs():
    """List outputs."""
    print("📤 Available Output Formats:")
    print()
    for name, desc in list_outputs().items():
        print(f"  {name:10} - {desc}")


def cmd_providers():
    """List providers."""
    from .models import Provider
    
    print("🔌 Supported AI Tools:")
    print()
    
    parsers = get_all_parsers()
    for provider in Provider:
        status = "✅" if provider in parsers else "⚪"
        print(f"  {status} {provider.value}")


def cmd_status():
    """Show status."""
    vault = get_default_vault()
    
    print("📊 AI Sessions Sync Status")
    print("=" * 40)
    
    if vault:
        print(f"✅ Obsidian vault: {vault}")
    else:
        print("⚠️  No Obsidian vault detected")
        print("   Set OBSIDIAN_VAULT env var or create ~/.aisync.conf")
    
    print()
    
    # Count sessions
    total = 0
    print("Sessions by provider:")
    for provider, parser in get_all_parsers().items():
        paths = parser.get_session_paths()
        count = len(paths)
        total += count
        status = "✅" if count > 0 else "⚪"
        print(f"  {status} {provider.value}: {count}")
    
    print()
    print(f"Total: {total} sessions")


def cmd_config(args):
    """Get/set config."""
    config_path = Path.home() / ".aisync.conf"
    
    # Load existing config
    config = {}
    if config_path.exists():
        for line in config_path.read_text().split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"\'')
    
    if args.key and args.value:
        # Set
        config[args.key] = args.value
        lines = [f'{k}="{v}"' for k, v in config.items()]
        config_path.write_text('\n'.join(lines) + '\n')
        print(f"Set {args.key}={args.value}")
    elif args.key:
        # Get
        value = config.get(args.key)
        if value:
            print(f"{args.key}={value}")
        else:
            print(f"{args.key} is not set")
    else:
        # List all
        print("Configuration:")
        for key, value in config.items():
            print(f"  {key}={value}")
        if not config:
            print("  (empty)")


if __name__ == '__main__':
    main()
