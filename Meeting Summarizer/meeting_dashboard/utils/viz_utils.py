from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models import ActionItem, Meeting

def generate_action_timeline_data(user_id: int) -> Dict:
    """
    Generate timeline data for action items visualization
    
    Args:
        user_id: ID of the user to get action items for
        
    Returns:
        Dictionary with timeline data for visualization
    """
    # Get action items for the user
    action_items = ActionItem.query.join(Meeting)\
                                 .filter(Meeting.user_id == user_id)\
                                 .order_by(ActionItem.due_date.asc())\
                                 .all()
    
    timeline_data = {
        'items': [],
        'summary': {
            'total': len(action_items),
            'completed': 0,
            'pending': 0,
            'in_progress': 0,
            'cancelled': 0,
            'overdue': 0
        },
        'by_priority': {
            'high': 0,
            'medium': 0,
            'low': 0
        },
        'by_assignee': {}
    }
    
    current_date = datetime.now().date()
    
    for item in action_items:
        # Basic item data
        item_data = {
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'assignee': item.assignee or 'Unassigned',
            'priority': item.priority,
            'status': item.status,
            'due_date': item.due_date.isoformat() if item.due_date else None,
            'created_at': item.created_at.isoformat(),
            'meeting_title': item.meeting.title
        }
        
        timeline_data['items'].append(item_data)
        
        # Update summary counts (defensive for unexpected status)
        if item.status not in timeline_data['summary']:
            timeline_data['summary'][item.status] = 0
        timeline_data['summary'][item.status] += 1
        
        # Update priority counts
        if item.priority not in timeline_data['by_priority']:
            timeline_data['by_priority'][item.priority] = 0
        timeline_data['by_priority'][item.priority] += 1
        
        # Check if overdue
        if item.due_date and item.due_date.date() < current_date and item.status != 'completed':
            timeline_data['summary']['overdue'] += 1
        
        # Group by assignee
        assignee = item.assignee or 'Unassigned'
        if assignee not in timeline_data['by_assignee']:
            timeline_data['by_assignee'][assignee] = {
                'total': 0,
                'completed': 0,
                'pending': 0,
                'in_progress': 0,
                'cancelled': 0
            }
        
        timeline_data['by_assignee'][assignee]['total'] += 1
        if item.status not in timeline_data['by_assignee'][assignee]:
            timeline_data['by_assignee'][assignee][item.status] = 0
        timeline_data['by_assignee'][assignee][item.status] += 1
    
    return timeline_data

def generate_meeting_stats(user_id: int) -> Dict:
    """
    Generate meeting statistics for the user
    
    Args:
        user_id: ID of the user to get stats for
        
    Returns:
        Dictionary with meeting statistics
    """
    meetings = Meeting.query.filter_by(user_id=user_id).all()
    
    stats = {
        'total_meetings': len(meetings),
        'total_action_items': 0,
        'meetings_this_month': 0,
        'avg_meeting_duration': 0,
        'most_productive_day': None,
        'action_items_by_meeting': []
    }
    
    if not meetings:
        return stats
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    total_duration = 0
    day_counts = {}
    
    for meeting in meetings:
        # Count action items
        action_count = len(meeting.action_items)
        stats['total_action_items'] += action_count
        
        stats['action_items_by_meeting'].append({
            'meeting_id': meeting.id,
            'title': meeting.title,
            'action_count': action_count,
            'date': meeting.meeting_date.isoformat()
        })
        
        # Count meetings this month
        if meeting.meeting_date.month == current_month and meeting.meeting_date.year == current_year:
            stats['meetings_this_month'] += 1
        
        # Calculate average duration
        if meeting.duration_minutes:
            total_duration += meeting.duration_minutes
        
        # Track most productive day
        day_of_week = meeting.meeting_date.strftime('%A')
        day_counts[day_of_week] = day_counts.get(day_of_week, 0) + 1
    
    # Calculate averages
    if meetings:
        stats['avg_meeting_duration'] = total_duration / len(meetings) if total_duration > 0 else 0
    
    # Find most productive day
    if day_counts:
        stats['most_productive_day'] = max(day_counts, key=day_counts.get)
    
    return stats

def create_priority_chart_data(user_id: int) -> Dict:
    """
    Create data for priority distribution chart
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with chart data
    """
    action_items = ActionItem.query.join(Meeting)\
                                 .filter(Meeting.user_id == user_id)\
                                 .all()
    
    priority_data = {
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    for item in action_items:
        priority_data[item.priority] += 1
    
    return {
        'labels': ['High Priority', 'Medium Priority', 'Low Priority'],
        'data': [priority_data['high'], priority_data['medium'], priority_data['low']],
        'colors': ['#dc3545', '#ffc107', '#28a745']
    }

def create_status_chart_data(user_id: int) -> Dict:
    """
    Create data for status distribution chart
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with chart data
    """
    action_items = ActionItem.query.join(Meeting)\
                                 .filter(Meeting.user_id == user_id)\
                                 .all()
    
    status_data = {
        'completed': 0,
        'in_progress': 0,
        'pending': 0,
        'cancelled': 0
    }
    
    for item in action_items:
        status_data[item.status] += 1
    
    return {
        'labels': ['Completed', 'In Progress', 'Pending', 'Cancelled'],
        'data': [status_data['completed'], status_data['in_progress'], 
                status_data['pending'], status_data['cancelled']],
        'colors': ['#28a745', '#007bff', '#ffc107', '#6c757d']
    }

def create_timeline_chart_data(user_id: int, days: int = 30) -> Dict:
    """
    Create timeline data for action items over time
    
    Args:
        user_id: ID of the user
        days: Number of days to look back
        
    Returns:
        Dictionary with timeline chart data
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get action items created in the time range
    action_items = ActionItem.query.join(Meeting)\
                                 .filter(Meeting.user_id == user_id)\
                                 .filter(ActionItem.created_at >= start_date)\
                                 .all()
    
    # Group by date
    daily_counts = {}
    for item in action_items:
        date = item.created_at.date()
        if date not in daily_counts:
            daily_counts[date] = 0
        daily_counts[date] += 1
    
    # Create complete date range
    dates = []
    counts = []
    current_date = start_date
    
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        counts.append(daily_counts.get(current_date, 0))
        current_date += timedelta(days=1)
    
    return {
        'labels': dates,
        'data': counts
    }

def create_assignee_chart_data(user_id: int) -> Dict:
    """
    Create data for assignee distribution chart
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with chart data
    """
    action_items = ActionItem.query.join(Meeting)\
                                 .filter(Meeting.user_id == user_id)\
                                 .all()
    
    assignee_data = {}
    
    for item in action_items:
        assignee = item.assignee or 'Unassigned'
        if assignee not in assignee_data:
            assignee_data[assignee] = 0
        assignee_data[assignee] += 1
    
    # Sort by count (descending)
    sorted_assignees = sorted(assignee_data.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'labels': [item[0] for item in sorted_assignees],
        'data': [item[1] for item in sorted_assignees]
    }

def generate_dashboard_summary(user_id: int) -> Dict:
    """
    Generate comprehensive dashboard summary data
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with all dashboard data
    """
    return {
        'timeline': generate_action_timeline_data(user_id),
        'meeting_stats': generate_meeting_stats(user_id),
        'priority_chart': create_priority_chart_data(user_id),
        'status_chart': create_status_chart_data(user_id),
        'timeline_chart': create_timeline_chart_data(user_id),
        'assignee_chart': create_assignee_chart_data(user_id)
    }
