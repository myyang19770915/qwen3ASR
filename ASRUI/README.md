# 多格式音檔轉錄系統

一個支援多種音檔格式的全端轉錄應用程式，使用 Qwen3 ASR 模型進行中英文語音識別。

## 功能特色

- 🎵 支援多種音檔格式：MP3、WAV、M4A
- 🔄 自動格式轉換和音檔分段處理
- ⏱️ 精確的時間戳記錄
- 📊 即時轉錄進度顯示
- 💾 JSON 格式結果下載
- 🌐 現代化 React 前端界面
- 📡 WebSocket 即時通訊

## 系統架構

### 後端 (Python FastAPI)
- **框架**: FastAPI 用於 REST API 和 WebSocket
- **音檔處理**: FFmpeg + librosa 進行格式轉換和分段
- **AI 模型**: Qwen3 ASR 1.7B 模型 (透過 OpenAI SDK)
- **功能**: 
  - 檔案上傳和驗證
  - 音檔格式轉換 (.mp3/.m4a → .wav)
  - 自動分段處理 (30秒片段)
  - 批次轉錄處理
  - 即時進度回報

### 前端 (React TypeScript)
- **框架**: React 18 with TypeScript
- **功能**:
  - 拖放式檔案上傳
  - 即時轉錄進度顯示
  - 分段結果展示
  - JSON 檔案下載
  - 響應式設計

## 安裝需求

### 系統依賴
```bash
# 安裝 FFmpeg (音檔處理)
sudo apt update
sudo apt install ffmpeg

# 確認 Qwen3 ASR 服務運行在 localhost:8006
```

### 後端安裝
```bash
cd backend
pip install -r requirements.txt
```

### 前端安裝
```bash
cd frontend
npm install
```

## 使用方法

### 1. 啟動 Qwen3 ASR 服務
確保 Qwen3 ASR 模型服務運行在 `http://localhost:8006`

### 2. 啟動後端服務
```bash
cd backend
python main.py
```
服務將運行在 `http://localhost:8001`

### 3. 啟動前端服務
```bash
cd frontend
npm start
```
前端將運行在 `http://localhost:3003`

### 4. 使用轉錄功能
1. 開啟瀏覽器訪問 `http://localhost:3003`
2. 拖放或選擇音檔 (.mp3, .wav, .m4a)
3. 點擊上傳文件
4. 點擊開始轉錄
5. 觀看即時轉錄進度
6. 下載轉錄結果 JSON 檔案

## API 文檔

### 主要端點

- `POST /upload` - 上傳音檔文件
- `POST /transcribe/{session_id}` - 開始轉錄處理
- `GET /download/{session_id}` - 下載轉錄結果
- `WS /ws/{session_id}` - WebSocket 即時更新

### 支援格式
- **輸入**: .mp3, .wav, .m4a
- **輸出**: JSON (包含分段文字和時間戳)

## 輸出格式範例

```json
{
  "metadata": {
    "original_file": "/path/to/audio.mp3",
    "total_segments": 10,
    "successful_segments": 10,
    "total_duration": 300.0,
    "transcription_date": "2026-02-01T12:00:00"
  },
  "full_text": "完整的轉錄文字內容...",
  "segments": [
    {
      "segment_id": 0,
      "start_time": 0.0,
      "end_time": 30.0,
      "text": "第一段轉錄文字...",
      "status": "success"
    }
  ]
}
```

## 技術細節

### 音檔處理流程
1. 檔案上傳和格式檢查
2. 非 WAV 格式自動轉換為 WAV (16kHz, mono)
3. 音檔分段 (預設 30 秒片段)
4. 並行轉錄處理
5. 結果合併和清理暫存檔

### WebSocket 通訊
- 即時進度更新
- 分段結果推送
- 錯誤狀態通知
- 完成狀態通知

## 開發指南

### 後端開發
```bash
# 開發模式運行
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 前端開發
```bash
# 開發模式
npm start

# 建置生產版本
npm run build
```

## 故障排除

### 常見問題

1. **FFmpeg 未找到**
   ```bash
   sudo apt install ffmpeg
   ```

2. **Qwen3 ASR 服務未運行**
   - 確認服務運行在 localhost:8006
   - 檢查模型載入狀態

3. **大檔案處理失敗**
   - 系統會自動分段處理
   - 檢查磁碟空間是否足夠

4. **WebSocket 連線失敗**
   - 確認後端服務正常運行
   - 檢查防火牆設定

### 重要修復：WebSocket 進度條即時更新問題

#### 問題描述
在實際使用中發現，轉錄進度條雖然接收到WebSocket消息，但UI不會即時更新，而是在轉錄完成後才一次性顯示最終結果。

#### 根本原因
1. **React狀態批處理**: React會將快速連續的狀態更新進行批處理，導致UI不會在每次狀態更新時立即重新渲染
2. **異步回調問題**: 後端的`progress_callback`函數使用`asyncio.create_task()`在同步環境中無法正確執行
3. **同步/異步不匹配**: 轉錄函數和WebSocket發送函數之間的同步/異步調用不匹配

#### 解決方案

**後端修復 (main.py)**:
```python
# 修改為真正的異步回調函數
async def progress_callback(current: int, total: int, segment_info: dict):
    try:
        message = {
            "type": "progress",
            "current": current,
            "total": total,
            "segment": segment_info,
            "percentage": round((current / total) * 100, 2) if total > 0 else 0
        }
        # 直接使用await調用，不使用asyncio.create_task
        await manager.send_message(session_id, message)
    except Exception as e:
        print(f"Error sending progress update: {e}")
```

**音檔轉錄器修復 (audio_transcriber.py)**:
```python
# 添加異步版本的轉錄方法
async def transcribe_file_async(self, input_path: str, progress_callback=None):
    # 使用異步轉錄分段方法
    segment_results = await self.transcribe_segments_async(segments, progress_callback)

# 支持同步和異步回調的兼容性處理
if progress_callback:
    if asyncio.iscoroutinefunction(progress_callback):
        await progress_callback(i + 1, len(segments), segment_info)
    else:
        progress_callback(i + 1, len(segments), segment_info)
```

**前端修復 (App.tsx)**:
```tsx
import { flushSync } from 'react-dom';

// 在WebSocket消息處理中使用flushSync強制同步更新
case 'progress':
  if (typeof message.current === 'number' && typeof message.total === 'number' && typeof message.percentage === 'number') {
    // 使用flushSync強制同步更新，避免React批處理延遲
    flushSync(() => {
      setProgress({
        current: message.current!,
        total: message.total!,
        percentage: message.percentage!
      });
    });
  }
```

#### 性能優化
- 在後端添加`await asyncio.sleep(0.1)`小延遲，避免前端被過快的更新阻塞
- 使用WebSocket調試日誌確保消息正確發送和接收
- 為進度條組件添加key屬性確保React正確重新渲染

#### 關鍵學習點
1. **異步程序設計**: 確保整個調用鏈保持一致的異步/同步模式
2. **React狀態批處理**: 使用`flushSync()`可以強制React立即更新UI
3. **WebSocket實時通訊**: 需要適當的錯誤處理和連線狀態管理
4. **調試策略**: 使用詳細的控制台日誌追蹤問題根源

這個問題的修復過程展示了全端應用中實時數據流的複雜性，特別是在涉及異步處理、WebSocket通訊和React狀態管理的場景中。

## 授權條款

本專案採用 MIT 授權條款。

## 貢獻指南

歡迎提交 Issue 和 Pull Request！

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request