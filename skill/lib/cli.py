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
  backup     Export sessions to output format(s)
  find       Search across all sessions  
  metrics    Show usage statistics
  insights   Generate detailed report
  check      Show detected sessions & status
  tools      List supported AI tools
  formats    List available output formats
  set        Get/set configuration

QUICK START:
  aisync backup                  # Export to Obsidian
  aisync backup -f json html     # Export to JSON + HTML
  aisync find "function"         # Search sessions
  aisync metrics                 # View statistics

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
    
    # backup command (was: sync)
    backup_parser = subparsers.add_parser('backup', 
        help='Export sessions to output format(s)',
        description='Export AI coding sessions to Obsidian, JSON, HTML, or SQLite.',
        epilog='''
Examples:
  aisync backup                          Export to Obsidian (auto-detected)
  aisync backup -o ~/ai-sessions         Custom output directory
  aisync backup -f obsidian json html    Multiple output formats
  aisync backup -p claude-code cursor    Only specific providers
  aisync backup -f sqlite --no-analyze   SQLite without analytics
''',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    backup_parser.add_argument('-o', '--output', metavar='DIR',
                            help='Output directory (default: auto-detect Obsidian vault)')
    backup_parser.add_argument('-f', '--format', nargs='+', default=['obsidian'],
                            metavar='FMT',
                            help='Output format(s): obsidian, json, jsonl, html, sqlite')
    backup_parser.add_argument('-p', '--provider', nargs='+', metavar='PROV',
                            help='Only export specific provider(s)')
    backup_parser.add_argument('--no-analyze', action='store_true', 
                            help='Skip analytics computation')
    backup_parser.add_argument('--json', action='store_true', 
                            help='Output results as JSON')
    
    # find command (was: search)
    find_parser = subparsers.add_parser('find', 
        help='Search across all sessions',
        description='Full-text search across all AI coding sessions.',
        epilog='''
Examples:
  aisync find "async function"         Simple text search
  aisync find "error" -p cursor        Filter by provider
  aisync find "def \\w+\\(" --regex    Regex pattern
  aisync find "api" --json -l 50       JSON output, 50 results
''',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    find_parser.add_argument('query', help='Search query (text or regex)')
    find_parser.add_argument('-p', '--provider', metavar='PROV',
                              help='Filter by provider name')
    find_parser.add_argument('-l', '--limit', type=int, default=20, metavar='N',
                              help='Maximum results (default: 20)')
    find_parser.add_argument('--regex', action='store_true', 
                              help='Treat query as regex pattern')
    find_parser.add_argument('--json', action='store_true', 
                              help='Output results as JSON')
    
    # metrics command (was: stats)
    metrics_parser = subparsers.add_parser('metrics', 
        help='Show usage statistics',
        description='Display statistics about your AI coding sessions.')
    metrics_parser.add_argument('-f', '--format', choices=['text', 'json'], default='text',
                             help='Output format (default: text)')
    
    # insights command (was: report)
    insights_parser = subparsers.add_parser('insights', 
        help='Generate detailed report with insights',
        description='Generate a comprehensive report with productivity insights.')
    insights_parser.add_argument('-o', '--output', metavar='FILE',
                              help='Save to file (default: print to stdout)')
    
    # formats command (was: outputs)
    subparsers.add_parser('formats', 
        help='List available output formats',
        description='Show all supported output formats with descriptions.')
    
    # tools command (was: providers)
    subparsers.add_parser('tools', 
        help='List supported AI coding tools',
        description='Show all 12 supported AI coding tools and detected sessions.')
    
    # check command (was: status)
    subparsers.add_parser('check', 
        help='Check status and detected sessions',
        description='Display current configuration and detected sessions.')
    
    # set command (was: config)
    set_parser = subparsers.add_parser('set', 
        help='Get/set configuration',
        description='Manage aisync configuration.',
        epilog='''
Examples:
  aisync set                           List all settings
  aisync set OBSIDIAN_VAULT            Get vault path
  aisync set OBSIDIAN_VAULT ~/vault    Set vault path
''',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    set_parser.add_argument('key', nargs='?', metavar='KEY',
                              help='Configuration key')
    set_parser.add_argument('value', nargs='?', metavar='VALUE',
                              help='Value to set')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'backup':
            cmd_backup(args)
        elif args.command == 'find':
            cmd_find(args)
        elif args.command == 'metrics':
            cmd_metrics(args)
        elif args.command == 'insights':
            cmd_insights(args)
        elif args.command == 'formats':
            cmd_formats()
        elif args.command == 'tools':
            cmd_tools()
        elif args.command == 'check':
            cmd_check()
        elif args.command == 'set':
            cmd_set(args)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_backup(args):
    """Export sessions to output format(s)."""
    print("📦 Backing up AI sessions...")
    
    result = sync_all(
        output_dir=args.output,
        outputs=args.format,
        providers=args.provider,
        analyze=not args.no_analyze
    )
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n✅ Backup complete!")
        print(f"   📁 Output: {result['output_dir']}")
        print(f"   📊 Sessions: {result['sessions_total']}")
        print(f"   🔌 Tools: {', '.join(result['by_provider'].keys())}")
        
        if result.get('statistics'):
            stats = result['statistics']
            print(f"\n📈 Metrics:")
            print(f"   Total tokens: {stats.get('total_tokens', 0):,}")
            print(f"   Code blocks: {stats.get('total_code_blocks', 0):,}")
            if stats.get('by_language'):
                top_langs = list(stats['by_language'].keys())[:3]
                print(f"   Top languages: {', '.join(top_langs)}")


def cmd_find(args):
    """Find/search sessions."""
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
        print(f"🔍 Found {len(results)} matches for '{args.query}'\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result.session.provider.value}] {result.session.date_str}")
            print(f"   {result.message.role.value}: {result.message.content[:100]}...")
            print()


def cmd_metrics(args):
    """Show usage metrics."""
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
        print("📊 AI Sessions Metrics")
        print("=" * 40)
        print(f"Total sessions:  {stats.get('total_sessions', 0):,}")
        print(f"Total messages:  {stats.get('total_messages', 0):,}")
        print(f"Total tokens:    {stats.get('total_tokens', 0):,}")
        print(f"Code blocks:     {stats.get('total_code_blocks', 0):,}")
        print()
        
        print("By Tool:")
        for provider, count in stats.get('by_provider', {}).items():
            print(f"  {provider}: {count}")
        print()
        
        print("Top Languages:")
        for lang, count in list(stats.get('by_language', {}).items())[:5]:
            print(f"  {lang}: {count}")


def cmd_insights(args):
    """Generate insights report."""
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
        print(f"💡 Insights saved to {args.output}")
    else:
        print(report)


def cmd_formats():
    """List output formats."""
    print("📤 Available Output Formats:")
    print()
    for name, desc in list_outputs().items():
        print(f"  {name:10} - {desc}")


def cmd_tools():
    """List AI tools."""
    from .models import Provider
    
    print("🔧 Supported AI Coding Tools:")
    print()
    
    parsers = get_all_parsers()
    for provider in Provider:
        parser = parsers.get(provider)
        if parser:
            count = len(parser.get_session_paths())
            status = "✅" if count > 0 else "⚪"
            print(f"  {status} {provider.value}: {count} sessions")
        else:
            print(f"  ⚪ {provider.value}")


def cmd_check():
    """Check status and detected sessions."""
    vault = get_default_vault()
    
    print("🔍 AI Sessions Sync Check")
    print("=" * 40)
    
    if vault:
        print(f"✅ Obsidian vault: {vault}")
    else:
        print("⚠️  No Obsidian vault detected")
        print("   Run: aisync set OBSIDIAN_VAULT /path/to/vault")
    
    print()
    
    # Count sessions
    total = 0
    print("Detected sessions:")
    for provider, parser in get_all_parsers().items():
        paths = parser.get_session_paths()
        count = len(paths)
        total += count
        status = "✅" if count > 0 else "⚪"
        print(f"  {status} {provider.value}: {count}")
    
    print()
    print(f"📊 Total: {total} sessions ready to backup")


def cmd_set(args):
    """Get/set configuration."""
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
        print(f"✅ Set {args.key}={args.value}")
    elif args.key:
        # Get
        value = config.get(args.key)
        if value:
            print(f"{args.key}={value}")
        else:
            print(f"⚪ {args.key} is not set")
    else:
        # List all
        print("⚙️  Configuration:")
        for key, value in config.items():
            print(f"  {key}={value}")
        if not config:
            print("  (no settings configured)")
        print()
        print("Available keys: OBSIDIAN_VAULT, DEFAULT_OUTPUT, REDACT_SECRETS")


if __name__ == '__main__':
    main()
