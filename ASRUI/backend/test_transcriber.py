#!/usr/bin/env python3
import asyncio
import sys
import os

# 添加backend目錄到路徑
sys.path.append('/home/myyang/deepseekocr/ASRUI/backend')

from audio_transcriber import AudioTranscriber

async def test_progress_callback(current, total, segment_info):
    print(f"Progress: {current}/{total} ({(current/total)*100:.1f}%) - Segment {segment_info['segment_id']}: {segment_info['status']}")

async def test_transcription():
    transcriber = AudioTranscriber()
    
    # 創建一個測試用的短音頻文件
    test_file = "/home/myyang/deepseekocr/ASRUI/backend/test_audio.wav"
    
    # 如果沒有測試文件，使用任何現有的音頻文件
    if not os.path.exists(test_file):
        # 尋找現有的音頻文件
        for ext in ['.mp3', '.wav', '.m4a']:
            for root, dirs, files in os.walk('/home/myyang/deepseekocr'):
                for file in files:
                    if file.endswith(ext):
                        test_file = os.path.join(root, file)
                        print(f"Found test file: {test_file}")
                        break
                if os.path.exists(test_file) and test_file != "/home/myyang/deepseekocr/ASRUI/backend/test_audio.wav":
                    break
    
    if not os.path.exists(test_file):
        print("No audio file found for testing")
        return
        
    print(f"Testing with file: {test_file}")
    result = await transcriber.transcribe_file_async(test_file, test_progress_callback)
    
    if result['success']:
        print(f"Transcription successful! Total segments: {result['metadata']['total_segments']}")
        print(f"Full text: {result['full_text'][:100]}...")
    else:
        print(f"Transcription failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_transcription())