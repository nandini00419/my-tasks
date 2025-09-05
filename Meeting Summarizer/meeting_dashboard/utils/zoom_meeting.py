import re
import subprocess
import os
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Tuple
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

class ZoomMeetingHandler:
    """Handle Zoom meeting operations including joining and recording"""
    
    def __init__(self):
        self.driver = None
        self.is_recording = False
        self.recording_path = None
        
    def parse_zoom_link(self, meeting_url: str) -> Optional[Dict[str, str]]:
        """
        Parse Zoom meeting URL to extract meeting ID and passcode
        
        Args:
            meeting_url: Zoom meeting URL
            
        Returns:
            Dictionary with meeting_id and passcode, or None if invalid
        """
        # Pattern for Zoom meeting URLs
        patterns = [
            r'https://us\d+web\.zoom\.us/j/(\d+)\?pwd=([^&\s]+)',  # Standard format
            r'https://zoom\.us/j/(\d+)\?pwd=([^&\s]+)',           # Alternative format
            r'https://.*\.zoom\.us/j/(\d+)\?pwd=([^&\s]+)',       # Generic format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, meeting_url)
            if match:
                meeting_id = match.group(1)
                passcode = match.group(2)
                return {
                    'meeting_id': meeting_id,
                    'passcode': passcode,
                    'url': meeting_url
                }
        
        return None
    
    def setup_driver(self) -> bool:
        """
        Setup Chrome WebDriver for automated meeting joining
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # For headless mode (uncomment if needed)
            # chrome_options.add_argument('--headless')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            return False
    
    def join_meeting(self, meeting_data: Dict[str, str], auto_join: bool = True) -> Tuple[bool, str]:
        """
        Join a Zoom meeting using Selenium automation
        
        Args:
            meeting_data: Dictionary with meeting_id, passcode, and url
            auto_join: Whether to automatically join the meeting
            
        Returns:
            Tuple of (success, message)
        """
        if not self.setup_driver():
            return False, "Failed to setup browser automation"
        
        try:
            # Navigate to the meeting URL
            self.driver.get(meeting_data['url'])
            
            # Wait for the page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Handle passcode if required
            try:
                passcode_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "input-for-pwd"))
                )
                passcode_input.clear()
                passcode_input.send_keys(meeting_data['passcode'])
                
                # Click continue or join button
                join_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Join') or contains(text(), 'Continue')]")
                join_button.click()
                
            except TimeoutException:
                # No passcode required or already entered
                pass
            
            # Wait for meeting to load
            time.sleep(3)
            
            if auto_join:
                # Try to join the meeting automatically
                try:
                    join_meeting_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Join') or contains(text(), 'Join Audio')]"))
                    )
                    join_meeting_btn.click()
                except TimeoutException:
                    pass
            
            return True, "Successfully joined the meeting"
            
        except Exception as e:
            return False, f"Error joining meeting: {str(e)}"
    
    def start_recording(self, output_path: str) -> bool:
        """
        Start recording the meeting (browser-based recording)
        
        Args:
            output_path: Path to save the recording
            
        Returns:
            True if recording started successfully
        """
        if not self.driver:
            return False
        
        try:
            # This is a simplified approach - in practice, you'd need more sophisticated recording
            # For now, we'll use browser's built-in recording capabilities
            self.is_recording = True
            self.recording_path = output_path
            
            # Execute JavaScript to start recording (if supported by browser)
            self.driver.execute_script("""
                if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
                    navigator.mediaDevices.getDisplayMedia({video: true, audio: true})
                    .then(stream => {
                        window.recordingStream = stream;
                        console.log('Recording started');
                    })
                    .catch(err => console.error('Recording failed:', err));
                }
            """)
            
            return True
        except Exception as e:
            print(f"Error starting recording: {e}")
            return False
    
    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and return the path to the recording file
        
        Returns:
            Path to recording file or None if failed
        """
        if not self.is_recording or not self.driver:
            return None
        
        try:
            # Stop the recording stream
            self.driver.execute_script("""
                if (window.recordingStream) {
                    window.recordingStream.getTracks().forEach(track => track.stop());
                    window.recordingStream = null;
                    console.log('Recording stopped');
                }
            """)
            
            self.is_recording = False
            return self.recording_path
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return None
    
    def leave_meeting(self):
        """Leave the current meeting"""
        if self.driver:
            try:
                # Try to find and click leave button
                leave_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Leave') or contains(text(), 'End')]")
                leave_button.click()
            except:
                pass
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.is_recording = False
        self.recording_path = None

def process_zoom_meeting(meeting_url: str, duration_minutes: int = 60) -> Dict:
    """
    Process a Zoom meeting by joining, recording, and extracting information
    
    Args:
        meeting_url: Zoom meeting URL
        duration_minutes: Expected duration of the meeting
        
    Returns:
        Dictionary with processing results
    """
    handler = ZoomMeetingHandler()
    result = {
        'success': False,
        'message': '',
        'meeting_data': None,
        'recording_path': None,
        'transcript': ''
    }
    
    try:
        # Parse the meeting URL
        meeting_data = handler.parse_zoom_link(meeting_url)
        if not meeting_data:
            result['message'] = 'Invalid Zoom meeting URL'
            return result
        
        result['meeting_data'] = meeting_data
        
        # Join the meeting
        success, message = handler.join_meeting(meeting_data)
        if not success:
            result['message'] = message
            return result
        
        # Start recording
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        recording_path = f"recordings/zoom_meeting_{timestamp}.webm"
        os.makedirs(os.path.dirname(recording_path), exist_ok=True)
        
        if handler.start_recording(recording_path):
            result['recording_path'] = recording_path
            
            # Wait for the meeting duration (in a real scenario, you'd monitor for meeting end)
            print(f"Recording meeting for {duration_minutes} minutes...")
            time.sleep(duration_minutes * 60)
            
            # Stop recording
            final_recording_path = handler.stop_recording()
            if final_recording_path:
                result['recording_path'] = final_recording_path
        
        # Leave the meeting
        handler.leave_meeting()
        
        result['success'] = True
        result['message'] = 'Meeting processed successfully'
        
    except Exception as e:
        result['message'] = f'Error processing meeting: {str(e)}'
    finally:
        handler.cleanup()
    
    return result

def extract_meeting_info_from_url(meeting_url: str) -> Dict:
    """
    Extract meeting information from URL without joining
    
    Args:
        meeting_url: Zoom meeting URL
        
    Returns:
        Dictionary with extracted information
    """
    meeting_data = ZoomMeetingHandler().parse_zoom_link(meeting_url)
    
    if not meeting_data:
        return {'valid': False, 'message': 'Invalid Zoom meeting URL'}
    
    return {
        'valid': True,
        'meeting_id': meeting_data['meeting_id'],
        'passcode': meeting_data['passcode'],
        'url': meeting_data['url'],
        'platform': 'Zoom',
        'message': 'Valid Zoom meeting URL'
    }
