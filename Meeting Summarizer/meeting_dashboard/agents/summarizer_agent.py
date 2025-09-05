from typing import Dict, List, Optional
from .groq_client import GroqClient

class SummarizerAgent:
    """Agent responsible for summarizing meeting transcripts"""
    
    def __init__(self, groq_client: GroqClient):
        self.groq_client = groq_client
    
    def summarize_meeting(self, transcript: str, participants: List[str] = None) -> str:
        """
        Generate a comprehensive summary of a meeting transcript
        
        Args:
            transcript: Raw meeting transcript text
            participants: Optional list of meeting participants
            
        Returns:
            Formatted meeting summary
        """
        if not transcript or not transcript.strip():
            return "No transcript provided for summarization."
        
        # Prepare context for the AI
        context = self._prepare_context(transcript, participants)
        
        try:
            summary = self.groq_client.generate_summary(context)
            return self._format_summary(summary)
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def _prepare_context(self, transcript: str, participants: List[str] = None) -> str:
        """
        Prepare context for summarization by cleaning and structuring the transcript
        """
        # Clean the transcript
        cleaned_transcript = self._clean_transcript(transcript)
        
        # Add participant context if available
        if participants:
            participant_info = f"Meeting participants: {', '.join(participants)}\n\n"
            return participant_info + cleaned_transcript
        
        return cleaned_transcript
    
    def _clean_transcript(self, transcript: str) -> str:
        """
        Clean and normalize the transcript text
        """
        # Remove excessive whitespace
        lines = transcript.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _format_summary(self, summary: str) -> str:
        """
        Format the AI-generated summary for better readability
        """
        # Ensure proper formatting
        if not summary.strip():
            return "Unable to generate summary from the provided transcript."
        
        # Add a header if not present
        if not summary.startswith('#') and not summary.startswith('**'):
            summary = f"# Meeting Summary\n\n{summary}"
        
        return summary
    
    def extract_key_points(self, transcript: str) -> List[str]:
        """
        Extract key discussion points from the meeting
        
        Args:
            transcript: Meeting transcript text
            
        Returns:
            List of key points
        """
        if not transcript or not transcript.strip():
            return []
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert at analyzing meeting transcripts. 
                    Extract the 5-10 most important discussion points, decisions, or topics covered.
                    Return them as a simple list, one point per line."""
                },
                {
                    "role": "user",
                    "content": f"Extract key discussion points from this meeting:\n\n{transcript}"
                }
            ]
            
            response = self.groq_client.chat_completion(messages, temperature=0.3, max_tokens=1500)
            
            # Parse the response into a list
            key_points = []
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('*'):
                    # Remove numbering if present
                    line = line.lstrip('0123456789.- ')
                    if line:
                        key_points.append(line)
            
            return key_points[:10]  # Limit to 10 points
            
        except Exception as e:
            print(f"Error extracting key points: {str(e)}")
            return []
    
    def identify_decisions(self, transcript: str) -> List[Dict[str, str]]:
        """
        Identify decisions made during the meeting
        
        Args:
            transcript: Meeting transcript text
            
        Returns:
            List of decision dictionaries with 'decision' and 'context' keys
        """
        if not transcript or not transcript.strip():
            return []
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert at identifying decisions made in meetings.
                    Look for statements that indicate a decision has been made, such as:
                    - "We decided to..."
                    - "The decision is..."
                    - "We will..."
                    - "It's agreed that..."
                    
                    For each decision, provide:
                    1. The decision made
                    2. Brief context about why/how it was made
                    
                    Return as a JSON array of objects with 'decision' and 'context' fields."""
                },
                {
                    "role": "user",
                    "content": f"Identify decisions made in this meeting:\n\n{transcript}"
                }
            ]
            
            response = self.groq_client.chat_completion(messages, temperature=0.2, max_tokens=2000)
            
            # Try to parse JSON response
            import json
            try:
                decisions = json.loads(response)
                if isinstance(decisions, list):
                    return decisions
            except json.JSONDecodeError:
                pass
            
            # Fallback: parse from text
            decisions = []
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line and ('decision' in line.lower() or 'decided' in line.lower()):
                    decisions.append({
                        'decision': line,
                        'context': ''
                    })
            
            return decisions
            
        except Exception as e:
            print(f"Error identifying decisions: {str(e)}")
            return []
