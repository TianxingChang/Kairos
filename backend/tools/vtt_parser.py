import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class VTTSegment:
    """Represents a VTT subtitle segment with timing and text."""
    start_time: str
    end_time: str
    text: str
    start_seconds: float
    end_seconds: float


class VTTParser:
    """Parser for WebVTT subtitle files."""
    
    def __init__(self):
        self.time_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')
    
    def time_to_seconds(self, time_str: str) -> float:
        """Convert time format HH:MM:SS.mmm to seconds."""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1])
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
            return total_seconds
        except (ValueError, IndexError):
            return 0.0
    
    def seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to time format HH:MM:SS.mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"
    
    def parse_file(self, file_path: str) -> List[VTTSegment]:
        """Parse a VTT file and return a list of segments."""
        segments = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            return self.parse_content(content)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"VTT file not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error parsing VTT file: {str(e)}")
    
    def parse_content(self, content: str) -> List[VTTSegment]:
        """Parse VTT content string and return a list of segments."""
        segments = []
        lines = content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and header
            if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                i += 1
                continue
            
            # Check if this line contains timing
            time_match = self.time_pattern.match(line)
            if time_match:
                start_time = time_match.group(1)
                end_time = time_match.group(2)
                
                # Collect text lines for this segment
                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                if text_lines:
                    text = ' '.join(text_lines)
                    start_seconds = self.time_to_seconds(start_time)
                    end_seconds = self.time_to_seconds(end_time)
                    
                    segment = VTTSegment(
                        start_time=start_time,
                        end_time=end_time,
                        text=text,
                        start_seconds=start_seconds,
                        end_seconds=end_seconds
                    )
                    segments.append(segment)
            else:
                i += 1
        
        return segments
    
    def get_text_by_time_range(self, segments: List[VTTSegment], start_seconds: float, end_seconds: float) -> str:
        """Get all text within a specific time range."""
        text_parts = []
        for segment in segments:
            if (segment.start_seconds >= start_seconds and segment.start_seconds <= end_seconds) or \
               (segment.end_seconds >= start_seconds and segment.end_seconds <= end_seconds) or \
               (segment.start_seconds <= start_seconds and segment.end_seconds >= end_seconds):
                text_parts.append(segment.text)
        
        return ' '.join(text_parts)
    
    def get_full_text(self, segments: List[VTTSegment]) -> str:
        """Get all text from segments concatenated."""
        return ' '.join([segment.text for segment in segments])
    
    def get_duration(self, segments: List[VTTSegment]) -> float:
        """Get total duration of the video in seconds."""
        if not segments:
            return 0.0
        return max(segment.end_seconds for segment in segments)


class VTTTool:
    """Tool class for integrating VTT parsing with agents."""
    
    def __init__(self):
        self.parser = VTTParser()
    
    def parse_vtt_file(self, file_path: str) -> dict:
        """Parse VTT file and return structured data."""
        try:
            segments = self.parser.parse_file(file_path)
            
            return {
                "success": True,
                "segments": [
                    {
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "text": seg.text,
                        "start_seconds": seg.start_seconds,
                        "end_seconds": seg.end_seconds
                    }
                    for seg in segments
                ],
                "full_text": self.parser.get_full_text(segments),
                "duration": self.parser.get_duration(segments),
                "total_segments": len(segments)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "segments": [],
                "full_text": "",
                "duration": 0.0,
                "total_segments": 0
            }