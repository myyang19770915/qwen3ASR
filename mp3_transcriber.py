#!/usr/bin/env python3
"""
MP3音檔轉錄腳本 - 支援格式轉換、分段處理和timestamp輸出
作者: AI Assistant
日期: 2026-02-01
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
import librosa
import soundfile as sf
import numpy as np
from openai import OpenAI
import httpx
from pydub import AudioSegment

class MP3Transcriber:
    def __init__(self, server_url="http://localhost:8006", model_name="Qwen/Qwen3-ASR-1.7B"):
        self.server_url = server_url
        self.model_name = model_name
        self.client = OpenAI(base_url=f"{server_url}/v1", api_key="EMPTY")
        self.max_duration = 120  # 最大音檔長度（秒）- 保守設定
        
    def check_audio_info(self, audio_path):
        """檢查音檔資訊"""
        try:
            # 使用 librosa 獲取音檔資訊
            duration = librosa.get_duration(path=audio_path)
            sr = librosa.get_samplerate(audio_path)
            
            # 使用 pydub 獲取更詳細的資訊
            audio = AudioSegment.from_file(audio_path)
            
            info = {
                "file_path": audio_path,
                "file_size": os.path.getsize(audio_path),
                "duration": duration,
                "sample_rate": sr,
                "channels": audio.channels,
                "format": audio_path.suffix.lower(),
                "bitrate": audio.frame_rate,
                "needs_conversion": audio_path.suffix.lower() == '.mp3'
            }
            
            print(f"🎵 音檔資訊:")
            print(f"   檔案: {info['file_path']}")
            print(f"   大小: {info['file_size'] / 1024 / 1024:.2f} MB")
            print(f"   長度: {info['duration']:.2f} 秒 ({info['duration'] / 60:.2f} 分鐘)")
            print(f"   採樣率: {info['sample_rate']} Hz")
            print(f"   聲道數: {info['channels']}")
            print(f"   格式: {info['format']}")
            
            return info
            
        except Exception as e:
            print(f"❌ 無法讀取音檔資訊: {e}")
            return None
    
    def convert_to_wav(self, input_path, output_path=None):
        """將MP3轉換為WAV格式"""
        if output_path is None:
            output_path = input_path.with_suffix('.wav')
        
        try:
            print(f"🔄 轉換格式: {input_path} -> {output_path}")
            
            # 使用 pydub 進行格式轉換
            audio = AudioSegment.from_file(input_path)
            
            # 轉換為標準格式：16-bit, 單聲道, 16kHz
            audio = audio.set_frame_rate(16000)
            audio = audio.set_channels(1)
            audio = audio.set_sample_width(2)  # 16-bit
            
            # 導出為WAV
            audio.export(output_path, format="wav")
            print(f"✅ 格式轉換完成: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ 格式轉換失敗: {e}")
            return None
    
    def split_audio(self, audio_path, chunk_duration=60):
        """分割音檔為更小的片段"""
        try:
            print(f"✂️ 分割音檔，每段 {chunk_duration} 秒...")
            
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)
            chunk_duration_ms = chunk_duration * 1000
            
            chunks = []
            for i in range(0, duration_ms, chunk_duration_ms):
                chunk = audio[i:i + chunk_duration_ms]
                chunk_path = audio_path.parent / f"{audio_path.stem}_chunk_{i // chunk_duration_ms + 1:03d}.wav"
                chunk.export(chunk_path, format="wav")
                
                chunk_info = {
                    "path": chunk_path,
                    "start_time": i / 1000,
                    "end_time": min((i + chunk_duration_ms) / 1000, duration_ms / 1000),
                    "duration": len(chunk) / 1000
                }
                chunks.append(chunk_info)
                print(f"   📁 分段 {len(chunks)}: {chunk_info['start_time']:.1f}s - {chunk_info['end_time']:.1f}s")
            
            print(f"✅ 分割完成，共 {len(chunks)} 段")
            return chunks
            
        except Exception as e:
            print(f"❌ 音檔分割失敗: {e}")
            return None
    
    def transcribe_chunk(self, audio_path):
        """轉錄單個音檔片段"""
        try:
            print(f"🎤 轉錄: {audio_path.name}")
            
            # 讀取音檔數據
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            # 調用轉錄API
            start_time = time.time()
            transcription = self.client.audio.transcriptions.create(
                model=self.model_name,
                file=audio_data,
            )
            end_time = time.time()
            
            result = {
                "text": transcription.text.strip(),
                "duration": end_time - start_time,
                "file_size": len(audio_data)
            }
            
            print(f"   📝 轉錄完成 ({result['duration']:.2f}s): {result['text'][:50]}...")
            return result
            
        except Exception as e:
            print(f"❌ 轉錄失敗: {e}")
            return {"text": "", "error": str(e), "duration": 0, "file_size": 0}
    
    def transcribe_mp3(self, mp3_path):
        """完整的MP3轉錄流程"""
        mp3_path = Path(mp3_path)
        
        print(f"🚀 開始轉錄 MP3 音檔: {mp3_path}")
        print("="*60)
        
        # 1. 檢查音檔資訊
        audio_info = self.check_audio_info(mp3_path)
        if not audio_info:
            return None
        
        # 2. 格式轉換
        if audio_info['needs_conversion']:
            wav_path = self.convert_to_wav(mp3_path)
            if not wav_path:
                return None
        else:
            wav_path = mp3_path
        
        # 3. 檢查是否需要分段處理
        if audio_info['duration'] > self.max_duration:
            print(f"⚠️ 音檔過長 ({audio_info['duration']:.1f}s > {self.max_duration}s)，需要分段處理")
            chunks = self.split_audio(wav_path, chunk_duration=60)
            if not chunks:
                return None
        else:
            print(f"✅ 音檔長度適中 ({audio_info['duration']:.1f}s)，直接轉錄")
            chunks = [{
                "path": wav_path,
                "start_time": 0,
                "end_time": audio_info['duration'],
                "duration": audio_info['duration']
            }]
        
        # 4. 轉錄每個片段
        print(f"\\n🎯 開始轉錄，共 {len(chunks)} 段")
        print("-"*40)
        
        transcription_results = []
        total_text = ""
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\\n🔄 處理第 {i}/{len(chunks)} 段")
            
            result = self.transcribe_chunk(chunk["path"])
            
            if result["text"]:
                # 計算全域時間戳
                chunk_result = {
                    "segment_id": i,
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "duration": chunk["duration"],
                    "text": result["text"],
                    "transcription_duration": result["duration"],
                    "file_size": result.get("file_size", 0)
                }
                
                transcription_results.append(chunk_result)
                total_text += result["text"] + " "
                
                print(f"   ✅ 第 {i} 段完成")
            else:
                print(f"   ❌ 第 {i} 段失敗: {result.get('error', '未知錯誤')}")
        
        # 5. 組織最終結果
        final_result = {
            "metadata": {
                "original_file": str(mp3_path),
                "file_size": audio_info['file_size'],
                "duration": audio_info['duration'],
                "sample_rate": audio_info['sample_rate'],
                "channels": audio_info['channels'],
                "model": self.model_name,
                "transcription_date": datetime.now().isoformat(),
                "total_segments": len(chunks),
                "successful_segments": len(transcription_results)
            },
            "full_text": total_text.strip(),
            "segments": transcription_results,
            "statistics": {
                "total_duration": audio_info['duration'],
                "transcription_time": sum(r["transcription_duration"] for r in transcription_results),
                "average_speed": audio_info['duration'] / sum(r["transcription_duration"] for r in transcription_results) if transcription_results else 0
            }
        }
        
        # 6. 清理臨時文件
        self.cleanup_temp_files(chunks, keep_original_wav=(mp3_path.suffix.lower() == '.mp3'))
        
        print(f"\\n🎉 轉錄完成!")
        print(f"   總時長: {final_result['metadata']['duration']:.2f} 秒")
        print(f"   成功段數: {final_result['metadata']['successful_segments']}/{final_result['metadata']['total_segments']}")
        print(f"   轉錄速度: {final_result['statistics']['average_speed']:.2f}x")
        
        return final_result
    
    def cleanup_temp_files(self, chunks, keep_original_wav=True):
        """清理臨時文件"""
        try:
            for chunk in chunks:
                chunk_path = chunk["path"]
                # 只刪除分段文件，保留原始文件和轉換的WAV文件
                if "chunk_" in str(chunk_path) and chunk_path.exists():
                    chunk_path.unlink()
                    print(f"🗑️ 已刪除臨時文件: {chunk_path.name}")
        except Exception as e:
            print(f"⚠️ 清理臨時文件時出錯: {e}")
    
    def save_result(self, result, output_path=None):
        """保存轉錄結果為JSON文件"""
        if output_path is None:
            original_path = Path(result['metadata']['original_file'])
            output_path = original_path.parent / f"{original_path.stem}_transcription.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"💾 結果已保存: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 保存結果失敗: {e}")
            return None

def main():
    # MP3 文件路徑
    mp3_file = "/home/myyang/deepseekocr/Lee01.mp3"
    
    print("🎵 Qwen3 ASR MP3 轉錄工具")
    print("="*60)
    
    # 檢查文件是否存在
    if not Path(mp3_file).exists():
        print(f"❌ 找不到音檔文件: {mp3_file}")
        return
    
    # 初始化轉錄器
    transcriber = MP3Transcriber()
    
    try:
        # 執行轉錄
        result = transcriber.transcribe_mp3(mp3_file)
        
        if result:
            # 保存結果
            output_file = transcriber.save_result(result)
            
            # 顯示簡要結果
            print(f"\\n📋 轉錄摘要:")
            print(f"   檔案: {result['metadata']['original_file']}")
            print(f"   全文 ({len(result['full_text'])} 字符):")
            print(f"   {result['full_text'][:200]}...")
            
            # 顯示分段結果
            if len(result['segments']) > 1:
                print(f"\\n📑 分段詳情:")
                for segment in result['segments'][:3]:  # 只顯示前3段
                    print(f"   [{segment['start_time']:.1f}s-{segment['end_time']:.1f}s] {segment['text'][:100]}...")
                if len(result['segments']) > 3:
                    print(f"   ... 還有 {len(result['segments']) - 3} 段")
            
            print(f"\\n✅ 轉錄完成，詳細結果已保存至: {output_file}")
        
        else:
            print("❌ 轉錄失敗")
    
    except KeyboardInterrupt:
        print("\\n⚠️ 用戶中斷操作")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()