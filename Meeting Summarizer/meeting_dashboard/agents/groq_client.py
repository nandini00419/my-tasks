import os
import requests
import json
from typing import Dict, List, Optional


class GroqClient:
    """Wrapper for Groq API client"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key is required")

        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """
        Send a chat completion request to Groq API
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,  # ✅ correct param
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            if response.status_code != 200:
                print("❌ DEBUG: Request failed")
                print("Payload Sent:", json.dumps(payload, indent=2))
                print("Response Text:", response.text)

            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            raise Exception(f"Groq API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected response format from Groq API: {str(e)}")

    def generate_summary(
        self, text: str, model: str = "llama-3.1-8b-instant"
    ) -> str:
        """
        Generate a summary of the given text
        """
        messages = [
            {
                "role": "system",
                "content": """You are an expert meeting summarizer. 
                Create a concise, well-structured summary of the meeting transcript. 
                Focus on key decisions, important discussions, and main outcomes. 
                Use bullet points for clarity.""",
            },
            {
                "role": "user",
                "content": f"Please summarize this meeting transcript:\n\n{text}",
            },
        ]

        return self.chat_completion(messages, model=model, temperature=0.3, max_tokens=2000)

    def extract_action_items(
        self, text: str, model: str = "llama-3.1-8b-instant"
    ) -> List[Dict]:
        """
        Extract action items from meeting transcript
        """
        messages = [
            {
                "role": "system",
                "content": """You are an expert at extracting action items from meeting transcripts. 
                Extract all action items, tasks, and follow-ups mentioned in the meeting.
                For each action item, identify:
                - Title/description
                - Assignee (if mentioned)
                - Due date (if mentioned)
                - Priority level (low, medium, high)

                Return the results as a JSON array of objects with these fields:
                - title
                - description
                - assignee
                - due_date
                - priority

                If no action items are found, return an empty array [].""",
            },
            {
                "role": "user",
                "content": f"Extract action items from this meeting transcript:\n\n{text}",
            },
        ]

        try:
            response = self.chat_completion(
                messages, model=model, temperature=0.2, max_tokens=3000
            )

            # Try parsing JSON response
            try:
                action_items = json.loads(response)
                if isinstance(action_items, list):
                    return action_items
                else:
                    return []
            except json.JSONDecodeError:
                # If JSON parsing fails, fallback
                return self._parse_action_items_from_text(response)

        except Exception as e:
            print(f"Error extracting action items: {str(e)}")
            return []

    def _parse_action_items_from_text(self, text: str) -> List[Dict]:
        """
        Fallback method to parse action items from text response
        """
        action_items = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if line and (
                "action" in line.lower()
                or "task" in line.lower()
                or "follow" in line.lower()
            ):
                action_items.append(
                    {
                        "title": line,
                        "description": "",
                        "assignee": "",
                        "due_date": None,
                        "priority": "medium",
                    }
                )

        return action_items


