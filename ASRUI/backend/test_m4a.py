#!/usr/bin/env python3
"""
簡單測試 M4A 格式轉錄功能
"""

import sys
import os
sys.path.append('/home/myyang/deepseekocr/ASRUI/backend')

from audio_transcriber import AudioTranscriber

def test_m4a_transcription():
    transcriber = AudioTranscriber()
    
    # 測試文件路徑
    test_file = "/home/myyang/deepseekocr/資策會test.m4a"
    
    if not os.path.exists(test_file):
        print(f"測試文件不存在: {test_file}")
        return
    
    print(f"開始轉錄 M4A 文件: {test_file}")
    print(f"格式支援: {transcriber.is_supported_format(test_file)}")
    
    def progress_callback(current, total, segment_info):
        percentage = (current / total) * 100
        print(f"進度: {current}/{total} ({percentage:.1f}%) - 段落 {segment_info['segment_id']}")
        if segment_info.get('text'):
            print(f"  文字: {segment_info['text'][:50]}...")
    
    result = transcriber.transcribe_file(test_file, progress_callback)
    
    if result["success"]:
        print(f"\n轉錄成功!")
        print(f"總時長: {result['metadata']['total_duration']:.2f} 秒")
        print(f"成功段落: {result['metadata']['successful_segments']}/{result['metadata']['total_segments']}")
        print(f"完整文字 ({len(result['full_text'])} 字符):")
        print(result['full_text'][:200] + "..." if len(result['full_text']) > 200 else result['full_text'])
    else:
        print(f"轉錄失敗: {result.get('error', '未知錯誤')}")

if __name__ == "__main__":
    test_m4a_transcription()