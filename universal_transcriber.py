#!/usr/bin/env python3
"""
通用音檔轉錄系統 - 支援多種格式 (.mp3, .wav, .m4a)
"""

import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from openai import OpenAI

class UniversalTranscriber:
    def __init__(self):
        self.client = OpenAI(
            base_url="http://localhost:8006/v1",
            api_key="sk-xxx"
        )
        self.supported_formats = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
        self.max_file_size_mb = 40  # vLLM的檔案大小限制
        self.chunk_duration = 30    # 分段長度(秒)
        
    def get_audio_info(self, audio_path):
        """獲取音檔資訊"""
        try:
            cmd = [
                'ffprobe', '-i', str(audio_path),
                '-show_entries', 'format=duration,size',
                '-show_entries', 'stream=codec_name',
                '-v', 'quiet', '-of', 'json'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                info = json.loads(result.stdout)
                duration = float(info['format']['duration'])
                size_bytes = int(info['format']['size'])
                codec = info['streams'][0]['codec_name'] if info['streams'] else 'unknown'
                return {
                    'duration': duration,
                    'size_bytes': size_bytes,
                    'size_mb': size_bytes / (1024 * 1024),
                    'codec': codec
                }
            return None
        except Exception as e:
            print(f"❌ 獲取音檔資訊失敗: {e}")
            return None
    
    def convert_to_wav(self, input_path, output_path=None):
        """將音檔轉換為WAV格式"""
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"音檔不存在: {input_path}")
        
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}.wav"
        else:
            output_path = Path(output_path)
            
        print(f"🔄 轉換音檔格式: {input_path.name} -> {output_path.name}")
        
        cmd = [
            'ffmpeg', '-i', str(input_path),
            '-ar', '16000',  # 16kHz採樣率
            '-ac', '1',      # 單聲道
            '-c:a', 'pcm_s16le',  # 16-bit PCM
            '-y',            # 覆蓋輸出檔案
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ 轉換完成: {output_path}")
                return output_path
            else:
                print(f"❌ 轉換失敗: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ 轉換過程發生錯誤: {e}")
            return None
    
    def split_audio(self, input_path):
        """將音檔分割為較小的片段"""
        input_path = Path(input_path)
        info = self.get_audio_info(input_path)
        
        if not info:
            print("❌ 無法獲取音檔資訊")
            return []
        
        total_duration = info['duration']
        file_size_mb = info['size_mb']
        
        print(f"🎵 音檔資訊:")
        print(f"   格式: {info['codec']}")
        print(f"   大小: {file_size_mb:.2f} MB")
        print(f"   時長: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分鐘)")
        
        # 如果檔案小於限制且是WAV格式，直接返回
        if file_size_mb < self.max_file_size_mb and input_path.suffix.lower() == '.wav':
            print("✅ 檔案符合直接轉錄條件")
            return [{'path': input_path, 'start_time': 0, 'end_time': total_duration}]
        
        print(f"✂️ 分割為 {self.chunk_duration} 秒片段...")
        
        chunks = []
        chunk_count = int((total_duration / self.chunk_duration)) + 1
        
        for i in range(chunk_count):
            start_time = i * self.chunk_duration
            if start_time >= total_duration:
                break
                
            end_time = min(start_time + self.chunk_duration, total_duration)
            chunk_path = input_path.parent / f"temp_chunk_{i+1:03d}.wav"
            
            cmd = [
                'ffmpeg', '-i', str(input_path),
                '-ss', str(start_time),
                '-t', str(self.chunk_duration),
                '-ar', '16000',
                '-ac', '1',
                '-c:a', 'pcm_s16le',
                '-y',
                str(chunk_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                chunks.append({
                    'path': chunk_path,
                    'start_time': start_time,
                    'end_time': end_time,
                    'is_temp': True
                })
                print(f"✅ 片段 {i+1}/{chunk_count}: {start_time:.1f}s - {end_time:.1f}s")
            else:
                print(f"❌ 分割片段 {i+1} 失敗: {result.stderr}")
        
        return chunks
    
    def transcribe_chunk(self, chunk_info):
        """轉錄單個片段"""
        chunk_path = chunk_info['path']
        start_time = chunk_info['start_time']
        end_time = chunk_info['end_time']
        
        try:
            with open(chunk_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="Qwen/Qwen3-1.7B-Audio",
                    file=audio_file,
                    response_format="text"
                )
            
            return {
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'text': transcript.strip(),
                'success': True
            }
            
        except Exception as e:
            print(f"❌ 轉錄失敗 ({start_time:.1f}s - {end_time:.1f}s): {e}")
            return {
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'text': f"[轉錄失敗: {str(e)}]",
                'success': False
            }
    
    def cleanup_temp_files(self, chunks):
        """清理暫時檔案"""
        print("🧹 清理暫時檔案...")
        for chunk_info in chunks:
            if chunk_info.get('is_temp', False):
                try:
                    chunk_info['path'].unlink()
                    print(f"🗑️ 已刪除: {chunk_info['path'].name}")
                except:
                    pass
    
    def transcribe_file(self, input_file, output_file=None):
        """轉錄音檔主函數"""
        input_path = Path(input_file)
        
        # 檢查檔案是否存在
        if not input_path.exists():
            raise FileNotFoundError(f"檔案不存在: {input_file}")
        
        # 檢查檔案格式
        if input_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"不支援的檔案格式: {input_path.suffix}")
        
        print(f"🎯 開始轉錄: {input_path.name}")
        print(f"📁 檔案路徑: {input_path}")
        
        start_time = time.time()
        
        try:
            # 如果不是WAV格式，先轉換
            wav_path = input_path
            temp_wav_created = False
            
            if input_path.suffix.lower() != '.wav':
                wav_path = self.convert_to_wav(input_path)
                if not wav_path:
                    raise Exception("音檔格式轉換失敗")
                temp_wav_created = True
            
            # 分割音檔
            chunks = self.split_audio(wav_path)
            if not chunks:
                raise Exception("音檔分割失敗")
            
            print(f"\n🚀 開始轉錄 {len(chunks)} 個片段...")
            
            # 轉錄每個片段
            results = []
            successful_count = 0
            
            for i, chunk_info in enumerate(chunks, 1):
                print(f"\n📝 轉錄片段 {i}/{len(chunks)} ({chunk_info['start_time']:.1f}s - {chunk_info['end_time']:.1f}s)...")
                
                result = self.transcribe_chunk(chunk_info)
                results.append(result)
                
                if result['success']:
                    successful_count += 1
                    print(f"✅ 完成: {result['text'][:100]}{'...' if len(result['text']) > 100 else ''}")
                else:
                    print(f"❌ 失敗: {result['text']}")
                
                # 短暫延遲避免過載
                time.sleep(0.5)
            
            # 整理結果
            full_text = " ".join([r['text'] for r in results if r['success']])
            
            # 準備輸出資料
            output_data = {
                'metadata': {
                    'original_file': str(input_path),
                    'total_chunks': len(chunks),
                    'successful_chunks': successful_count,
                    'total_duration': chunks[-1]['end_time'] if chunks else 0,
                    'transcription_date': datetime.now().isoformat(),
                    'file_format': input_path.suffix.lower()
                },
                'full_text': full_text,
                'segments': results
            }
            
            # 儲存結果
            if output_file is None:
                output_file = input_path.parent / f"{input_path.stem}_transcription.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 清理暫時檔案
            self.cleanup_temp_files(chunks)
            
            # 清理轉換的WAV檔案
            if temp_wav_created and wav_path.exists():
                wav_path.unlink()
                print(f"🗑️ 已刪除轉換檔案: {wav_path.name}")
            
            # 顯示結果摘要
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"\n🎉 轉錄完成!")
            print(f"📊 處理統計:")
            print(f"   總片段數: {len(chunks)}")
            print(f"   成功片段: {successful_count}")
            print(f"   成功率: {successful_count/len(chunks)*100:.1f}%")
            print(f"   處理時間: {processing_time:.1f} 秒")
            print(f"   文字長度: {len(full_text)} 字元")
            print(f"📄 輸出檔案: {output_file}")
            
            return output_data
            
        except Exception as e:
            print(f"❌ 轉錄過程發生錯誤: {e}")
            # 確保清理暫時檔案
            if 'chunks' in locals():
                self.cleanup_temp_files(chunks)
            raise

def main():
    """主函數"""
    import sys
    
    if len(sys.argv) != 2:
        print("使用方法: python universal_transcriber.py <audio_file>")
        print("支援格式: .mp3, .wav, .m4a, .aac, .flac, .ogg")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    transcriber = UniversalTranscriber()
    
    try:
        result = transcriber.transcribe_file(audio_file)
        print(f"\n✨ 轉錄成功! 檔案已儲存")
    except Exception as e:
        print(f"\n❌ 轉錄失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()