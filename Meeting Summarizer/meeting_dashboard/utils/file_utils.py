import os
import re
from typing import List, Optional
from werkzeug.utils import secure_filename
import tempfile
import subprocess

def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """
    Check if a file has an allowed extension
    
    Args:
        filename: Name of the file to check
        allowed_extensions: Set of allowed extensions (default: txt, pdf, docx, md)
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = {'txt', 'pdf', 'docx', 'md'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def parse_transcript_file(filepath: str) -> str:
    """
    Parse transcript from various file formats
    
    Args:
        filepath: Path to the transcript file
        
    Returns:
        Extracted text content
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    filename = os.path.basename(filepath)
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    try:
        if extension == 'txt':
            return parse_txt_file(filepath)
        elif extension == 'md':
            return parse_markdown_file(filepath)
        elif extension == 'pdf':
            return parse_pdf_file(filepath)
        elif extension == 'docx':
            return parse_docx_file(filepath)
        else:
            # Try to read as plain text
            return parse_txt_file(filepath)
    except Exception as e:
        raise Exception(f"Error parsing file {filename}: {str(e)}")

def parse_txt_file(filepath: str) -> str:
    """Parse plain text file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # Try with different encoding
        with open(filepath, 'r', encoding='latin-1') as file:
            return file.read()

def parse_markdown_file(filepath: str) -> str:
    """Parse markdown file and extract text content"""
    content = parse_txt_file(filepath)
    
    # Remove markdown formatting
    content = re.sub(r'#{1,6}\s+', '', content)  # Remove headers
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold
    content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic
    content = re.sub(r'`(.*?)`', r'\1', content)  # Remove code
    content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)  # Remove links
    
    return content

def parse_pdf_file(filepath: str) -> str:
    """Parse PDF file and extract text content"""
    try:
        import PyPDF2
        
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
    except ImportError:
        raise Exception("PyPDF2 library is required to parse PDF files. Install with: pip install PyPDF2")
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")

def parse_docx_file(filepath: str) -> str:
    """Parse DOCX file and extract text content"""
    try:
        from docx import Document
        
        doc = Document(filepath)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except ImportError:
        raise Exception("python-docx library is required to parse DOCX files. Install with: pip install python-docx")
    except Exception as e:
        raise Exception(f"Error parsing DOCX: {str(e)}")

def transcribe_audio_faster_whisper(filepath: str, model_size: str = 'base') -> str:
    """
    Transcribe audio using faster-whisper (local inference).
    Supports common formats including webm (recorded via MediaRecorder).
    Requires: pip install faster-whisper ffmpeg-python (and ffmpeg installed on system PATH).
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise Exception("faster-whisper is required. Install with: pip install faster-whisper ffmpeg-python")

    # Ensure ffmpeg is available; if webm, convert to wav for stability
    input_path = filepath
    if filepath.lower().endswith('.webm'):
        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        tmp_wav.close()
        try:
            import ffmpeg
            (
                ffmpeg
                .input(filepath)
                .output(tmp_wav.name, ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            input_path = tmp_wav.name
        except Exception as e:
            raise Exception(f"Failed to convert webm to wav: {e}")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(input_path, beam_size=1)
    text_parts = []
    for seg in segments:
        text_parts.append(seg.text)
    return ' '.join(text_parts).strip()

def clean_transcript_text(text: str) -> str:
    """
    Clean and normalize transcript text
    
    Args:
        text: Raw transcript text
        
    Returns:
        Cleaned transcript text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove timestamps (common formats)
    text = re.sub(r'\d{1,2}:\d{2}(?::\d{2})?\s*', '', text)
    text = re.sub(r'\[\d{1,2}:\d{2}(?::\d{2})?\]\s*', '', text)
    
    # Remove speaker labels (common patterns)
    text = re.sub(r'^[A-Z][a-z]+:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Speaker \d+:\s*', '', text, flags=re.MULTILINE)
    
    # Clean up line breaks
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def extract_speakers(text: str) -> List[str]:
    """
    Extract unique speakers from transcript text
    
    Args:
        text: Transcript text
        
    Returns:
        List of unique speaker names
    """
    speakers = set()
    
    # Common speaker patterns
    patterns = [
        r'^([A-Z][a-z]+):\s*',  # Name:
        r'^Speaker (\d+):\s*',  # Speaker 1:
        r'^([A-Z][A-Z]+):\s*',  # NAME:
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        speakers.update(matches)
    
    return sorted(list(speakers))

def split_transcript_by_speaker(text: str) -> List[dict]:
    """
    Split transcript into speaker segments
    
    Args:
        text: Transcript text
        
    Returns:
        List of dictionaries with 'speaker' and 'content' keys
    """
    segments = []
    current_speaker = None
    current_content = []
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line starts with speaker name
        speaker_match = re.match(r'^([A-Z][a-z]+):\s*(.*)', line)
        if speaker_match:
            # Save previous segment
            if current_speaker and current_content:
                segments.append({
                    'speaker': current_speaker,
                    'content': ' '.join(current_content)
                })
            
            # Start new segment
            current_speaker = speaker_match.group(1)
            current_content = [speaker_match.group(2)] if speaker_match.group(2) else []
        else:
            # Continue current segment
            if current_content:
                current_content.append(line)
            else:
                # No speaker identified yet, treat as continuation
                if segments:
                    segments[-1]['content'] += ' ' + line
                else:
                    # First line without speaker
                    current_content = [line]
    
    # Save last segment
    if current_speaker and current_content:
        segments.append({
            'speaker': current_speaker,
            'content': ' '.join(current_content)
        })
    
    return segments

def validate_transcript(text: str) -> List[str]:
    """
    Validate transcript text and return any issues
    
    Args:
        text: Transcript text to validate
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    
    if not text or not text.strip():
        issues.append("Transcript is empty")
        return issues
    
    # Check minimum length
    if len(text.strip()) < 50:
        issues.append("Transcript is too short (minimum 50 characters)")
    
    # Check for common issues
    if len(text.split()) < 10:
        issues.append("Transcript appears to have very few words")
    
    # Check for excessive repetition
    words = text.lower().split()
    if len(words) > 0:
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        max_repetition = max(word_counts.values())
        if max_repetition > len(words) * 0.1:  # More than 10% repetition
            issues.append("Transcript may have excessive repetition")
    
    return issues
