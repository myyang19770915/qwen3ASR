#!/usr/bin/env python3
"""
MP3 轉錄腳本 - 支援大檔案分段處理
"""

import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from openai import OpenAI

def get_audio_duration(audio_path):
    """使用 ffprobe 獲取音檔長度"""
    try:
        cmd = [
            'ffprobe', '-i', str(audio_path), 
            '-show_entries', 'format=duration', 
            '-v', 'quiet', '-of', 'csv=p=0'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except:
        return None

def split_audio(input_path, chunk_duration=60):
    """將音檔分割為較小的片段"""
    try:
        total_duration = get_audio_duration(input_path)
        if not total_duration:
            print("❌ 無法獲取音檔長度")
            return None
        
        print(f"🎵 音檔總長度: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分鐘)")
        print(f"✂️ 分割為 {chunk_duration} 秒片段...")
        
        chunks = []
        chunk_count = int((total_duration / chunk_duration)) + 1
        
        for i in range(chunk_count):
            start_time = i * chunk_duration
            if start_time >= total_duration:
                break
                
            chunk_path = input_path.parent / f"{input_path.stem}_chunk_{i+1:03d}.wav"
            
            cmd = [
                'ffmpeg', '-i', str(input_path),
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-c', 'copy',
                '-y',
                str(chunk_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                chunk_info = {
                    "path": chunk_path,
                    "start_time": start_time,
                    "chunk_duration": min(chunk_duration, total_duration - start_time),
                    "chunk_number": i + 1
                }
                chunks.append(chunk_info)
                print(f"   📁 片段 {i+1}: {start_time:.1f}s - {start_time + chunk_info['chunk_duration']:.1f}s")
            else:
                print(f"❌ 分割片段 {i+1} 失敗")
        
        print(f"✅ 分割完成，共 {len(chunks)} 個片段")
        return chunks
        
    except Exception as e:
        print(f"❌ 音檔分割失敗: {e}")
        return None

def transcribe_chunk(chunk_path, client):
    """轉錄單個音檔片段"""
    try:
        with open(chunk_path, 'rb') as f:
            audio_data = f.read()
        
        file_size_mb = len(audio_data) / (1024 * 1024)
        print(f"   🎤 轉錄 {chunk_path.name} ({file_size_mb:.2f} MB)...")
        
        start_time = time.time()
        transcription = client.audio.transcriptions.create(
            model="Qwen/Qwen3-ASR-1.7B",
            file=audio_data,
        )
        duration = time.time() - start_time
        
        return {
            "text": transcription.text.strip(),
            "duration": duration,
            "file_size_mb": file_size_mb
        }
        
    except Exception as e:
        print(f"   ❌ 轉錄失敗: {e}")
        return {"text": "", "error": str(e)}

def transcribe_large_audio(audio_path, chunk_duration=60):
    """轉錄大音檔（分段處理）"""
    client = OpenAI(base_url="http://localhost:8006/v1", api_key="EMPTY")
    
    # 分割音檔
    chunks = split_audio(audio_path, chunk_duration)
    if not chunks:
        return None
    
    # 轉錄每個片段
    print(f"\n🎯 開始轉錄 {len(chunks)} 個片段...")
    print("-" * 50)
    
    results = []
    full_text = ""
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n📍 處理片段 {i}/{len(chunks)}")
        
        result = transcribe_chunk(chunk["path"], client)
        
        if result["text"]:
            chunk_result = {
                "chunk_number": i,
                "start_time": chunk["start_time"],
                "end_time": chunk["start_time"] + chunk["chunk_duration"],
                "duration": chunk["chunk_duration"],
                "text": result["text"],
                "transcription_time": result.get("duration", 0)
            }
            
            results.append(chunk_result)
            full_text += result["text"] + " "
            
            print(f"   ✅ 完成: {result['text'][:60]}...")
        else:
            print(f"   ❌ 失敗: {result.get('error', '未知錯誤')}")
    
    # 清理臨時文件
    print(f"\n🗑️ 清理臨時片段文件...")
    for chunk in chunks:
        try:
            chunk["path"].unlink()
        except:
            pass
    
    return {
        "metadata": {
            "original_file": str(audio_path),
            "total_chunks": len(chunks),
            "successful_chunks": len(results),
            "total_duration": sum(chunk["chunk_duration"] for chunk in chunks),
            "transcription_date": datetime.now().isoformat()
        },
        "full_text": full_text.strip(),
        "segments": results
    }

def main():
    mp3_file = Path("/home/myyang/deepseekocr/Lee01.mp3")
    output_file = "/home/myyang/deepseekocr/Lee01_transcription.json"
    
    print("🎵 Qwen3 ASR 大檔案轉錄工具")
    print("=" * 60)
    
    if not mp3_file.exists():
        print(f"❌ 找不到音檔: {mp3_file}")
        return
    
    file_size_mb = mp3_file.stat().st_size / (1024 * 1024)
    print(f"📁 原始檔案: {mp3_file.name} ({file_size_mb:.2f} MB)")
    
    # 轉換為 WAV
    wav_file = mp3_file.with_suffix('.wav')
    if not wav_file.exists():
        print(f"🔄 轉換為 WAV 格式...")
        cmd = ['ffmpeg', '-i', str(mp3_file), '-ar', '16000', '-ac', '1', '-y', str(wav_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 格式轉換失敗")
            return
        print(f"✅ 轉換完成: {wav_file.name}")
    else:
        print(f"📄 WAV檔案已存在: {wav_file.name}")
    
    # 檢查 WAV 檔案大小
    wav_size_mb = wav_file.stat().st_size / (1024 * 1024)
    print(f"📊 WAV檔案大小: {wav_size_mb:.2f} MB")
    
    # 如果檔案太大（超過40MB），進行分段處理
    if wav_size_mb > 40:
        print(f"⚠️ 檔案過大，需要分段處理...")
        result = transcribe_large_audio(wav_file, chunk_duration=30)  # 30秒一段
    else:
        print(f"✅ 檔案大小適中，直接轉錄")
        # 直接轉錄小文件的代碼...
        return
    
    if result:
        # 保存結果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 顯示摘要
        print(f"\n🎉 轉錄完成！")
        print(f"   成功片段: {result['metadata']['successful_chunks']}/{result['metadata']['total_chunks']}")
        print(f"   總時長: {result['metadata']['total_duration']:.1f} 秒")
        print(f"   總字數: {len(result['full_text'])} 字符")
        print(f"   結果檔案: {output_file}")
        
        # 顯示前幾段內容
        print(f"\n📝 轉錄內容預覽:")
        print(result['full_text'][:200] + "..." if len(result['full_text']) > 200 else result['full_text'])
        
        # 顯示時間戳分段
        if len(result['segments']) > 0:
            print(f"\n⏰ 時間戳分段 (前3段):")
            for segment in result['segments'][:3]:
                print(f"   [{segment['start_time']:.1f}s-{segment['end_time']:.1f}s] {segment['text'][:100]}...")
    
    else:
        print("\n❌ 轉錄失敗")

if __name__ == "__main__":
    main()