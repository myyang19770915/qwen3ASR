import React, { useState, useCallback, useEffect, useRef } from 'react';
import { flushSync } from 'react-dom';
import { TranscriptionSegment, TranscriptionResult, UploadResponse, WebSocketMessage } from './types';

const API_BASE_URL = 'http://localhost:8001';
const WS_BASE_URL = 'ws://localhost:8001';

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number; percentage: number }>({
    current: 0,
    total: 0,
    percentage: 0
  });
  const [segments, setSegments] = useState<TranscriptionSegment[]>([]);
  const [transcriptionResult, setTranscriptionResult] = useState<TranscriptionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // WebSocket connection
  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/ws/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected successfully for session:', sessionId);
    };

    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      console.log('[WebSocket] Message received:', message);

      switch (message.type) {
        case 'progress':
          console.log('Progress update:', { current: message.current, total: message.total, percentage: message.percentage });
          if (typeof message.current === 'number' && typeof message.total === 'number' && typeof message.percentage === 'number') {
            console.log('Updating progress state with:', { current: message.current, total: message.total, percentage: message.percentage });
            
            // 使用flushSync強制同步更新
            flushSync(() => {
              setProgress({
                current: message.current!,
                total: message.total!,
                percentage: message.percentage!
              });
            });
            
          } else {
            console.warn('Invalid progress data:', { current: message.current, total: message.total, percentage: message.percentage });
          }
          
          if (message.segment) {
            console.log('Segment update:', message.segment);
            flushSync(() => {
              setSegments(prev => {
                const newSegments = [...prev];
                const segment = message.segment!;
                const existingIndex = newSegments.findIndex(s => s.segment_id === segment.segment_id);
                
                if (existingIndex >= 0) {
                  newSegments[existingIndex] = segment;
                } else {
                  newSegments.push(segment);
                }
                
                return newSegments.sort((a, b) => a.segment_id - b.segment_id);
              });
            });
          }
          break;

        case 'completed':
          setIsTranscribing(false);
          if (message.result) {
            setTranscriptionResult(message.result);
            setSuccessMessage('轉錄完成！您可以下載結果文件。');
          }
          break;

        case 'error':
          setIsTranscribing(false);
          setError(message.error || '轉錄過程中發生錯誤');
          break;

        case 'heartbeat':
          // Keep connection alive
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Connection error:', error);
      setError('WebSocket連接錯誤');
    };

    ws.onclose = (event) => {
      console.log('[WebSocket] Connection closed:', event.code, event.reason);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId]);

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const handleFileSelect = useCallback((file: File) => {
    const supportedFormats = ['.mp3', '.wav', '.m4a'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!supportedFormats.includes(fileExtension)) {
      setError(`不支援的檔案格式：${fileExtension}。支援的格式：${supportedFormats.join(', ')}`);
      return;
    }

    setSelectedFile(file);
    setError(null);
    setSuccessMessage(null);
    setSegments([]);
    setTranscriptionResult(null);
    setProgress({ current: 0, total: 0, percentage: 0 });
  }, []);

  const handleFileDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const uploadFile = async () => {
    if (!selectedFile) {
      setError('請選擇一個音檔文件');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`上傳失敗: ${response.statusText}`);
      }

      const result: UploadResponse = await response.json();
      setSessionId(result.session_id);
      setSuccessMessage(`文件上傳成功：${result.filename}`);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '上傳失敗');
    } finally {
      setIsUploading(false);
    }
  };

  const startTranscription = async () => {
    if (!sessionId) {
      setError('請先上傳文件');
      return;
    }

    setIsTranscribing(true);
    setError(null);
    setSegments([]);
    setTranscriptionResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/transcribe/${sessionId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`轉錄啟動失敗: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('Transcription started:', result);

    } catch (err) {
      setIsTranscribing(false);
      setError(err instanceof Error ? err.message : '轉錄啟動失敗');
    }
  };

  const downloadResult = async () => {
    if (!sessionId) {
      setError('沒有可下載的結果');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/download/${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`下載失敗: ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedFile?.name?.split('.')[0] || 'transcription'}_transcription.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

    } catch (err) {
      setError(err instanceof Error ? err.message : '下載失敗');
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>音檔轉錄系統</h1>
        <p>支援 MP3、WAV、M4A 格式，自動分段轉錄並提供時間戳</p>
      </div>

      {/* File Upload Area */}
      <div 
        className="upload-area"
        onDrop={handleFileDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp3,.wav,.m4a"
          onChange={handleFileInputChange}
          className="file-input"
        />
        
        <div>
          <h3>選擇音檔文件</h3>
          <p>拖拽文件到此處或點擊選擇</p>
          <p>支援格式：MP3、WAV、M4A</p>
          
          <button
            className="upload-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isTranscribing}
          >
            選擇文件
          </button>

          {selectedFile && (
            <div style={{ marginTop: '15px' }}>
              <p><strong>已選擇：</strong> {selectedFile.name}</p>
              <p><strong>大小：</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
              
              <button
                className="upload-button"
                onClick={uploadFile}
                disabled={isUploading || isTranscribing}
              >
                {isUploading && <span className="loading"></span>}
                {isUploading ? '上傳中...' : '上傳文件'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      {error && <div className="error-message">{error}</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}

      {/* Transcription Controls */}
      {sessionId && !isTranscribing && !transcriptionResult && (
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <button
            className="upload-button"
            onClick={startTranscription}
            disabled={isUploading || isTranscribing}
          >
            開始轉錄
          </button>
        </div>
      )}

      {/* Progress Section */}
      {isTranscribing && (
        <div className="progress-section" key={`progress-${progress.current}-${progress.total}`}>
          <h3>轉錄進度</h3>
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${progress.percentage}%` }}
            ></div>
          </div>
          <p key={`progress-text-${progress.current}-${progress.total}`}>
            進度：{progress.current} / {progress.total} 片段 
            ({progress.percentage.toFixed(1)}%)
          </p>
          {/* <div style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
            調試信息: current={progress.current}, total={progress.total}, percentage={progress.percentage}
          </div> */}
        </div>
      )}

      {/* Segments Results */}
      {segments.length > 0 && (
        <div className="segment-results">
          <h3>轉錄結果</h3>
          {segments.map((segment) => (
            <div key={segment.segment_id} className="segment">
              <div className="segment-header">
                <span className="timestamp">
                  {formatTime(segment.start_time)} - {formatTime(segment.end_time)}
                </span>
                <span className={`segment-status status-${segment.status}`}>
                  {segment.status === 'success' && '完成'}
                  {segment.status === 'error' && '錯誤'}
                  {segment.status === 'processing' && '處理中'}
                </span>
              </div>
              {segment.text && (
                <div className="segment-text">
                  {segment.text}
                </div>
              )}
              {segment.error && (
                <div className="error-message" style={{ marginTop: '10px' }}>
                  錯誤：{segment.error}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Download Section */}
      {transcriptionResult && (
        <div className="download-section">
          <h3>轉錄完成</h3>
          <p>
            總時長：{Math.floor(transcriptionResult.metadata.total_duration / 60)}分
            {Math.floor(transcriptionResult.metadata.total_duration % 60)}秒
          </p>
          <p>
            成功片段：{transcriptionResult.metadata.successful_segments} / {transcriptionResult.metadata.total_segments}
          </p>
          <p>
            總字數：{transcriptionResult.full_text.length} 字符
          </p>
          
          <button
            className="download-button"
            onClick={downloadResult}
          >
            下載轉錄結果 (JSON)
          </button>
        </div>
      )}
    </div>
  );
}

export default App;