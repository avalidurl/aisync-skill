"""
Generate insights from session analytics.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import Counter

from ..models import Session


def generate_insights(sessions: List[Session], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate human-readable insights from sessions and stats.
    
    Args:
        sessions: List of analyzed sessions
        stats: Aggregate statistics from SessionAnalyzer
        
    Returns:
        List of insight objects
    """
    insights = []
    
    if not sessions or not stats:
        return insights
    
    # 1. Most productive day
    by_date = stats.get('by_date', {})
    if by_date:
        top_date, top_count = max(by_date.items(), key=lambda x: x[1])
        insights.append({
            'type': 'productivity',
            'title': 'Most Productive Day',
            'value': top_date,
            'detail': f'{top_count} sessions',
            'icon': '📅'
        })
    
    # 2. Favorite tool
    by_provider = stats.get('by_provider', {})
    if by_provider:
        top_provider, top_count = max(by_provider.items(), key=lambda x: x[1])
        total = stats.get('total_sessions', 1)
        pct = round(top_count / total * 100)
        insights.append({
            'type': 'preference',
            'title': 'Most Used Tool',
            'value': top_provider.replace('-', ' ').title(),
            'detail': f'{top_count} sessions ({pct}%)',
            'icon': '🔧'
        })
    
    # 3. Top language
    by_language = stats.get('by_language', {})
    if by_language:
        top_lang, top_count = max(by_language.items(), key=lambda x: x[1])
        insights.append({
            'type': 'language',
            'title': 'Top Language',
            'value': top_lang.title(),
            'detail': f'{top_count} sessions',
            'icon': '💻'
        })
    
    # 4. Peak hour
    by_hour = stats.get('by_hour', {})
    if by_hour:
        peak_hour, peak_count = max(by_hour.items(), key=lambda x: x[1])
        hour_str = f"{peak_hour}:00 - {(peak_hour + 1) % 24}:00"
        insights.append({
            'type': 'timing',
            'title': 'Peak Coding Hour',
            'value': hour_str,
            'detail': f'{peak_count} sessions',
            'icon': '⏰'
        })
    
    # 5. Token usage
    total_tokens = stats.get('total_tokens', 0)
    if total_tokens:
        # Rough cost estimate (assuming ~$0.01 per 1K tokens average)
        estimated_cost = total_tokens / 1000 * 0.01
        insights.append({
            'type': 'usage',
            'title': 'Total Tokens Used',
            'value': f'{total_tokens:,}',
            'detail': f'~${estimated_cost:.2f} estimated',
            'icon': '🔢'
        })
    
    # 6. Code blocks
    total_code = stats.get('total_code_blocks', 0)
    if total_code:
        insights.append({
            'type': 'code',
            'title': 'Code Blocks Generated',
            'value': f'{total_code:,}',
            'detail': 'across all sessions',
            'icon': '📝'
        })
    
    # 7. Activity streak
    streak = _calculate_streak(sessions)
    if streak > 1:
        insights.append({
            'type': 'streak',
            'title': 'Current Streak',
            'value': f'{streak} days',
            'detail': 'consecutive coding days',
            'icon': '🔥'
        })
    
    # 8. Weekend warrior or weekday coder
    by_day = stats.get('by_day_of_week', {})
    if by_day:
        weekend = by_day.get('Saturday', 0) + by_day.get('Sunday', 0)
        weekday = sum(v for k, v in by_day.items() if k not in ['Saturday', 'Sunday'])
        
        if weekend > weekday * 0.4:  # More than 40% of weekday activity
            insights.append({
                'type': 'pattern',
                'title': 'Weekend Warrior',
                'value': f'{weekend} weekend sessions',
                'detail': 'You code a lot on weekends!',
                'icon': '🏖️'
            })
        elif weekday > 0 and weekend == 0:
            insights.append({
                'type': 'pattern',
                'title': 'Weekday Coder',
                'value': f'{weekday} weekday sessions',
                'detail': 'You keep weekends free',
                'icon': '💼'
            })
    
    # 9. Model preference
    by_model = stats.get('by_model', {})
    if by_model:
        top_model, count = max(by_model.items(), key=lambda x: x[1])
        # Simplify model name
        model_short = top_model.split('/')[-1] if '/' in top_model else top_model
        insights.append({
            'type': 'model',
            'title': 'Favorite Model',
            'value': model_short,
            'detail': f'{count} sessions',
            'icon': '🧠'
        })
    
    # 10. Session length insight
    avg_messages = stats.get('avg_messages_per_session', 0)
    if avg_messages:
        if avg_messages > 20:
            length_desc = 'Long conversations'
        elif avg_messages > 10:
            length_desc = 'Medium conversations'
        else:
            length_desc = 'Quick questions'
        
        insights.append({
            'type': 'style',
            'title': 'Conversation Style',
            'value': length_desc,
            'detail': f'~{avg_messages:.0f} messages avg',
            'icon': '💬'
        })
    
    return insights


def _calculate_streak(sessions: List[Session]) -> int:
    """Calculate current consecutive day streak."""
    if not sessions:
        return 0
    
    # Get unique dates, sorted descending
    dates = sorted(set(s.created_at.date() for s in sessions), reverse=True)
    
    if not dates:
        return 0
    
    # Check if today or yesterday has activity
    today = datetime.now().date()
    if dates[0] < today - timedelta(days=1):
        return 0  # Streak broken
    
    # Count consecutive days
    streak = 1
    for i in range(1, len(dates)):
        if dates[i-1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            break
    
    return streak


def generate_report(sessions: List[Session], stats: Dict[str, Any]) -> str:
    """
    Generate a text report from analytics.
    
    Args:
        sessions: List of analyzed sessions
        stats: Aggregate statistics
        
    Returns:
        Formatted report string
    """
    insights = generate_insights(sessions, stats)
    
    report = []
    report.append("=" * 50)
    report.append("AI CODING SESSIONS REPORT")
    report.append("=" * 50)
    report.append("")
    
    # Overview
    report.append("📊 OVERVIEW")
    report.append("-" * 30)
    report.append(f"  Total Sessions: {stats.get('total_sessions', 0):,}")
    report.append(f"  Total Messages: {stats.get('total_messages', 0):,}")
    report.append(f"  Total Tokens:   {stats.get('total_tokens', 0):,}")
    report.append(f"  Code Blocks:    {stats.get('total_code_blocks', 0):,}")
    report.append("")
    
    # Date range
    date_range = stats.get('date_range', {})
    if date_range.get('start'):
        report.append(f"  Period: {date_range['start'][:10]} to {date_range['end'][:10]}")
    report.append("")
    
    # Insights
    report.append("💡 INSIGHTS")
    report.append("-" * 30)
    for insight in insights:
        report.append(f"  {insight['icon']} {insight['title']}: {insight['value']}")
        report.append(f"     {insight['detail']}")
    report.append("")
    
    # By provider
    by_provider = stats.get('by_provider', {})
    if by_provider:
        report.append("🔧 BY TOOL")
        report.append("-" * 30)
        for provider, count in by_provider.items():
            report.append(f"  {provider.replace('-', ' ').title()}: {count}")
    report.append("")
    
    # By language
    by_language = stats.get('by_language', {})
    if by_language:
        report.append("💻 TOP LANGUAGES")
        report.append("-" * 30)
        for lang, count in list(by_language.items())[:5]:
            report.append(f"  {lang.title()}: {count}")
    report.append("")
    
    report.append("=" * 50)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    return "\n".join(report)
