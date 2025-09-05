from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re
from .groq_client import GroqClient

class ActionAgent:
    """Agent responsible for extracting and managing action items from meeting transcripts"""
    
    def __init__(self, groq_client: GroqClient):
        self.groq_client = groq_client
    
    def extract_action_items(self, transcript: str) -> List[Dict[str, str]]:
        """
        Extract action items from meeting transcript using AI
        
        Args:
            transcript: Meeting transcript text
            
        Returns:
            List of action item dictionaries
        """
        if not transcript or not transcript.strip():
            return []
        
        try:
            # Use Groq client to extract action items
            action_items = self.groq_client.extract_action_items(transcript)
            
            # Post-process and validate the extracted items
            processed_items = []
            for item in action_items:
                processed_item = self._process_action_item(item)
                if processed_item:
                    processed_items.append(processed_item)
            
            return processed_items
            
        except Exception as e:
            print(f"Error extracting action items: {str(e)}")
            return []
    
    def _process_action_item(self, item: Dict) -> Optional[Dict]:
        """
        Process and validate a single action item
        
        Args:
            item: Raw action item dictionary
            
        Returns:
            Processed action item or None if invalid
        """
        if not isinstance(item, dict):
            return None
        
        # Ensure required fields
        title = item.get('title', '').strip()
        if not title:
            return None
        
        # Process description
        description = item.get('description', '').strip()
        
        # Process assignee
        assignee = item.get('assignee', '').strip()
        
        # Process due date
        due_date = self._parse_due_date(item.get('due_date', ''))
        
        # Process priority
        priority = self._normalize_priority(item.get('priority', 'medium'))
        
        return {
            'title': title,
            'description': description,
            'assignee': assignee,
            'due_date': due_date,
            'priority': priority
        }
    
    def _parse_due_date(self, date_str: str) -> Optional[str]:
        """
        Parse and normalize due date string
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            ISO format date string or None
        """
        if not date_str or not date_str.strip():
            return None
        
        date_str = date_str.strip()
        
        # Try to parse common date formats
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'(\d{1,2}-\d{1,2}-\d{4})',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    date_str = match.group(1)
                    # Try to parse and reformat
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            month, day, year = parts
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif '-' in date_str:
                        if len(date_str.split('-')[0]) == 4:  # YYYY-MM-DD
                            return date_str
                        else:  # MM-DD-YYYY
                            parts = date_str.split('-')
                            if len(parts) == 3:
                                month, day, year = parts
                                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except:
                    continue
        
        # Handle relative dates
        if 'next week' in date_str.lower():
            next_week = datetime.now() + timedelta(days=7)
            return next_week.strftime('%Y-%m-%d')
        elif 'next month' in date_str.lower():
            next_month = datetime.now() + timedelta(days=30)
            return next_month.strftime('%Y-%m-%d')
        elif 'tomorrow' in date_str.lower():
            tomorrow = datetime.now() + timedelta(days=1)
            return tomorrow.strftime('%Y-%m-%d')
        
        return None
    
    def _normalize_priority(self, priority: str) -> str:
        """
        Normalize priority string to standard values
        
        Args:
            priority: Priority string
            
        Returns:
            Normalized priority (low, medium, high)
        """
        if not priority:
            return 'medium'
        
        priority = priority.lower().strip()
        
        if priority in ['high', 'urgent', 'critical', 'important']:
            return 'high'
        elif priority in ['low', 'minor', 'optional']:
            return 'low'
        else:
            return 'medium'
    
    def categorize_action_items(self, action_items: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize action items by priority and assignee
        
        Args:
            action_items: List of action item dictionaries
            
        Returns:
            Dictionary with categorized action items
        """
        categories = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': [],
            'unassigned': [],
            'by_assignee': {}
        }
        
        for item in action_items:
            # Categorize by priority
            priority = item.get('priority', 'medium')
            if priority == 'high':
                categories['high_priority'].append(item)
            elif priority == 'low':
                categories['low_priority'].append(item)
            else:
                categories['medium_priority'].append(item)
            
            # Categorize by assignee
            assignee = item.get('assignee', '').strip()
            if assignee:
                if assignee not in categories['by_assignee']:
                    categories['by_assignee'][assignee] = []
                categories['by_assignee'][assignee].append(item)
            else:
                categories['unassigned'].append(item)
        
        return categories
    
    def generate_action_summary(self, action_items: List[Dict]) -> str:
        """
        Generate a summary of action items
        
        Args:
            action_items: List of action item dictionaries
            
        Returns:
            Summary text
        """
        if not action_items:
            return "No action items found in this meeting."
        
        total_items = len(action_items)
        high_priority = len([item for item in action_items if item.get('priority') == 'high'])
        assigned_items = len([item for item in action_items if item.get('assignee')])
        
        summary = f"Found {total_items} action items:\n"
        summary += f"- {high_priority} high priority items\n"
        summary += f"- {assigned_items} items with assigned owners\n"
        
        if assigned_items < total_items:
            summary += f"- {total_items - assigned_items} items need assignment\n"
        
        return summary
    
    def validate_action_item(self, item: Dict) -> List[str]:
        """
        Validate an action item and return any issues
        
        Args:
            item: Action item dictionary
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check required fields
        if not item.get('title', '').strip():
            issues.append("Title is required")
        
        # Check title length
        title = item.get('title', '')
        if len(title) > 300:
            issues.append("Title is too long (max 300 characters)")
        
        # Check priority
        priority = item.get('priority', '')
        if priority and priority not in ['low', 'medium', 'high']:
            issues.append("Priority must be low, medium, or high")
        
        # Check due date format
        due_date = item.get('due_date', '')
        if due_date:
            try:
                datetime.fromisoformat(due_date)
            except ValueError:
                issues.append("Due date must be in ISO format (YYYY-MM-DD)")
        
        return issues
