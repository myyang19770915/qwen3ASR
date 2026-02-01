#!/usr/bin/env python3
"""
MP3 轉錄腳本 - 支援格式轉換
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import subprocess

def convert_mp3_to_wav(mp3_path):
    """使用 ffmpeg 將 MP3 轉換為 WAV"""
    wav_path = mp3_path.with_suffix('.wav')
    
    try:
        print(f"🔄 轉換格式: {mp3_path.name} -> {wav_path.name}")
        
        # 使用 ffmpeg 轉換格式
        cmd = [
            'ffmpeg', '-i', str(mp3_path), 
            '-ar', '16000',  # 採樣率 16kHz
            '-ac', '1',      # 單聲道
            '-y',            # 覆蓋已存在的文件
            str(wav_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 格式轉換成功: {wav_path}")
            return wav_path
        else:
            print(f"❌ ffmpeg 轉換失敗: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("❌ 未找到 ffmpeg，嘗試安裝: sudo apt install ffmpeg")
        return None
    except Exception as e:
        print(f"❌ 格式轉換出錯: {e}")
        return None

def get_audio_info_simple(audio_path):
    """獲取音檔基本資訊"""
    stat = os.stat(audio_path)
    return {
        "file_path": str(audio_path),
        "file_size": stat.st_size,
        "size_mb": stat.st_size / (1024 * 1024)
    }

def transcribe_audio_file(audio_path, server_url="http://localhost:8006"):
    """轉錄音頻檔案"""
    client = OpenAI(base_url=f"{server_url}/v1", api_key="EMPTY")
    
    try:
        print(f"🎤 開始轉錄: {audio_path}")
        
        # 讀取音頻文件
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        
        print(f"📁 檔案大小: {len(audio_data) / (1024*1024):.2f} MB")
        
        # 執行轉錄
        start_time = time.time()
        transcription = client.audio.transcriptions.create(
            model="Qwen/Qwen3-ASR-1.7B",
            file=audio_data,
        )
        end_time = time.time()
        
        result = {
            "file_info": get_audio_info_simple(audio_path),
            "transcription": {
                "text": transcription.text.strip(),
                "model": "Qwen/Qwen3-ASR-1.7B",
                "duration": end_time - start_time,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        print(f"✅ 轉錄完成 ({result['transcription']['duration']:.2f}s)")
        return result
        
    except Exception as e:
        print(f"❌ 轉錄失敗: {e}")
        return None

def save_result_json(result, output_path):
    """保存結果到JSON文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 結果已保存: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 保存失敗: {e}")
        return False

def main():
    # 音檔路徑
    mp3_file = Path("/home/myyang/deepseekocr/Lee01.mp3")
    output_file = "/home/myyang/deepseekocr/Lee01_transcription.json"
    
    print("🎵 Qwen3 ASR 音檔轉錄工具")
    print("=" * 50)
    
    # 檢查檔案
    if not mp3_file.exists():
        print(f"❌ 找不到音檔: {mp3_file}")
        return
    
    # 顯示檔案資訊
    info = get_audio_info_simple(mp3_file)
    print(f"📁 檔案: {info['file_path']}")
    print(f"📊 大小: {info['size_mb']:.2f} MB")
    
    # 如果是 MP3，先轉換為 WAV
    if mp3_file.suffix.lower() == '.mp3':
        wav_file = convert_mp3_to_wav(mp3_file)
        if not wav_file:
            print("❌ 格式轉換失敗")
            return
        audio_file = wav_file
    else:
        audio_file = mp3_file
    
    # 執行轉錄
    result = transcribe_audio_file(audio_file)
    
    if result:
        # 顯示結果
        text = result['transcription']['text']
        print(f"\n📝 轉錄結果:")
        print(f"   長度: {len(text)} 字符")
        print(f"   內容預覽: {text[:100]}...")
        print(f"   完整內容: {text}")
        
        # 保存結果
        if save_result_json(result, output_file):
            print(f"\n🎉 任務完成！結果已保存到: {output_file}")
        else:
            print("\n⚠️ 轉錄成功但保存失敗")
            
        # 清理臨時 WAV 文件
        if audio_file != mp3_file and audio_file.exists():
            try:
                audio_file.unlink()
                print(f"🗑️ 已刪除臨時文件: {audio_file.name}")
            except:
                pass
    else:
        print("\n❌ 轉錄失敗")

if __name__ == "__main__":
    main()