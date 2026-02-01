import os
import subprocess
import tempfile
import librosa
import soundfile as sf
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union
from openai import OpenAI

class AudioTranscriber:
    def __init__(self, base_url: str = "http://localhost:8006/v1", api_key: str = "fake_key"):
        """Initialize the audio transcriber with OpenAI client."""
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.supported_formats = ['.mp3', '.wav', '.m4a']
        self.segment_duration = 60  # 音訊分段轉錄 seconds
        
    def is_supported_format(self, file_path: str) -> bool:
        """Check if the audio format is supported."""
        return Path(file_path).suffix.lower() in self.supported_formats
    
    def convert_to_wav(self, input_path: str, output_path: str) -> bool:
        """Convert audio file to WAV format using ffmpeg."""
        try:
            cmd = [
                'ffmpeg', '-i', input_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y', output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg conversion error: {e}")
            return False
        except FileNotFoundError:
            print("FFmpeg not found. Please install ffmpeg.")
            return False
    
    def get_audio_duration(self, file_path: str) -> float:
        """Get the duration of an audio file."""
        try:
            audio_data, sample_rate = librosa.load(file_path, sr=None)
            return len(audio_data) / sample_rate
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            return 0.0
    
    def create_audio_segments(self, wav_path: str, segment_duration: int = 60) -> List[str]:
        """Split audio file into segments."""
        segments = []
        try:
            duration = self.get_audio_duration(wav_path)
            num_segments = int(duration // segment_duration) + (1 if duration % segment_duration > 0 else 0)
            
            base_name = Path(wav_path).stem
            temp_dir = Path(wav_path).parent
            
            for i in range(num_segments):
                start_time = i * segment_duration
                segment_path = temp_dir / f"{base_name}_segment_{i:03d}.wav"
                
                cmd = [
                    'ffmpeg', '-i', wav_path,
                    '-ss', str(start_time),
                    '-t', str(segment_duration),
                    '-acodec', 'copy',
                    '-y', str(segment_path)
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                segments.append(str(segment_path))
                
            return segments
            
        except Exception as e:
            print(f"Error creating segments: {e}")
            return []
    
    def transcribe_audio_file(self, file_path: str) -> Optional[str]:
        """Transcribe a single audio file."""
        try:
            with open(file_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="Qwen/Qwen3-ASR-1.7B",
                    file=audio_file,
                    response_format="text"
                )
                return response
        except Exception as e:
            print(f"Error transcribing {file_path}: {e}")
            return None
    
    async def transcribe_segments_async(self, segments: List[str], progress_callback=None) -> List[Dict[str, Any]]:
        """Transcribe all audio segments asynchronously."""
        results = []
        
        print(f"[DEBUG] Starting transcription of {len(segments)} segments")
        
        for i, segment_path in enumerate(segments):
            print(f"[DEBUG] Processing segment {i+1}/{len(segments)}: {segment_path}")
            try:
                transcription = self.transcribe_audio_file(segment_path)
                
                if transcription:
                    segment_info = {
                        "segment_id": i,
                        "start_time": i * self.segment_duration,
                        "end_time": min((i + 1) * self.segment_duration, 
                                      self.get_audio_duration(segments[0].replace('_segment_000', ''))),
                        "text": transcription,
                        "status": "success"
                    }
                    print(f"[DEBUG] Segment {i} transcribed successfully: {transcription[:50]}...")
                else:
                    segment_info = {
                        "segment_id": i,
                        "start_time": i * self.segment_duration,
                        "end_time": (i + 1) * self.segment_duration,
                        "text": "",
                        "status": "error"
                    }
                    print(f"[DEBUG] Segment {i} transcription failed")
                
                results.append(segment_info)
                
                # Call progress callback if provided (async version)
                if progress_callback:
                    print(f"[DEBUG] Calling progress callback for segment {i}")
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(i + 1, len(segments), segment_info)
                    else:
                        progress_callback(i + 1, len(segments), segment_info)
                    print(f"[DEBUG] Progress callback completed for segment {i}")
                    
                    # 添加小延遲避免前端被過快的更新阻塞
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"Error processing segment {i}: {e}")
                error_info = {
                    "segment_id": i,
                    "start_time": i * self.segment_duration,
                    "end_time": (i + 1) * self.segment_duration,
                    "text": "",
                    "status": "error",
                    "error": str(e)
                }
                results.append(error_info)
                
                if progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(i + 1, len(segments), error_info)
                    else:
                        progress_callback(i + 1, len(segments), error_info)
        
        print(f"[DEBUG] Completed transcription of all segments")
        return results

    def transcribe_segments(self, segments: List[str], progress_callback=None) -> List[Dict[str, Any]]:
        """Transcribe all audio segments."""
        results = []
        
        for i, segment_path in enumerate(segments):
            try:
                transcription = self.transcribe_audio_file(segment_path)
                
                if transcription:
                    segment_info = {
                        "segment_id": i,
                        "start_time": i * self.segment_duration,
                        "end_time": min((i + 1) * self.segment_duration, 
                                      self.get_audio_duration(segments[0].replace('_segment_000', ''))),
                        "text": transcription,
                        "status": "success"
                    }
                else:
                    segment_info = {
                        "segment_id": i,
                        "start_time": i * self.segment_duration,
                        "end_time": (i + 1) * self.segment_duration,
                        "text": "",
                        "status": "error"
                    }
                
                results.append(segment_info)
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, len(segments), segment_info)
                    
            except Exception as e:
                print(f"Error processing segment {i}: {e}")
                error_info = {
                    "segment_id": i,
                    "start_time": i * self.segment_duration,
                    "end_time": (i + 1) * self.segment_duration,
                    "text": "",
                    "status": "error",
                    "error": str(e)
                }
                results.append(error_info)
                
                if progress_callback:
                    progress_callback(i + 1, len(segments), error_info)
        
        return results
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up {file_path}: {e}")
    
    async def transcribe_file_async(self, input_path: str, progress_callback=None) -> Dict[str, Any]:
        """Main method to transcribe an audio file asynchronously."""
        if not self.is_supported_format(input_path):
            return {
                "error": f"Unsupported format. Supported formats: {self.supported_formats}",
                "success": False
            }
        
        temp_files = []
        
        try:
            # Convert to WAV if necessary
            if not input_path.lower().endswith('.wav'):
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                    wav_path = temp_wav.name
                temp_files.append(wav_path)
                
                if not self.convert_to_wav(input_path, wav_path):
                    return {"error": "Failed to convert audio format", "success": False}
            else:
                wav_path = input_path
            
            # Get audio duration
            duration = self.get_audio_duration(wav_path)
            
            # Create segments
            segments = self.create_audio_segments(wav_path, self.segment_duration)
            temp_files.extend(segments)
            
            # Transcribe segments asynchronously
            segment_results = await self.transcribe_segments_async(segments, progress_callback)
            
            # Combine all text
            full_text = " ".join([seg["text"] for seg in segment_results if seg["text"]])
            
            # Count successful segments
            successful_segments = len([seg for seg in segment_results if seg["status"] == "success"])
            
            result = {
                "success": True,
                "metadata": {
                    "original_file": input_path,
                    "total_segments": len(segments),
                    "successful_segments": successful_segments,
                    "total_duration": duration,
                    "transcription_date": datetime.now().isoformat()
                },
                "full_text": full_text,
                "segments": segment_results
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Transcription failed: {str(e)}", "success": False}
        
        finally:
            # Clean up temporary files
            self.cleanup_temp_files(temp_files)

    def transcribe_file(self, input_path: str, progress_callback=None) -> Dict[str, Any]:
        """Main method to transcribe an audio file."""
        if not self.is_supported_format(input_path):
            return {
                "error": f"Unsupported format. Supported formats: {self.supported_formats}",
                "success": False
            }
        
        temp_files = []
        
        try:
            # Convert to WAV if necessary
            if not input_path.lower().endswith('.wav'):
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                    wav_path = temp_wav.name
                temp_files.append(wav_path)
                
                if not self.convert_to_wav(input_path, wav_path):
                    return {"error": "Failed to convert audio format", "success": False}
            else:
                wav_path = input_path
            
            # Get audio duration
            duration = self.get_audio_duration(wav_path)
            
            # Create segments
            segments = self.create_audio_segments(wav_path, self.segment_duration)
            temp_files.extend(segments)
            
            # Transcribe segments
            segment_results = self.transcribe_segments(segments, progress_callback)
            
            # Combine all text
            full_text = " ".join([seg["text"] for seg in segment_results if seg["text"]])
            
            # Count successful segments
            successful_segments = len([seg for seg in segment_results if seg["status"] == "success"])
            
            result = {
                "success": True,
                "metadata": {
                    "original_file": input_path,
                    "total_segments": len(segments),
                    "successful_segments": successful_segments,
                    "total_duration": duration,
                    "transcription_date": datetime.now().isoformat()
                },
                "full_text": full_text,
                "segments": segment_results
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Transcription failed: {str(e)}", "success": False}
        
        finally:
            # Clean up temporary files
            self.cleanup_temp_files(temp_files)