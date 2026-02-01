export interface TranscriptionSegment {
  segment_id: number;
  start_time: number;
  end_time: number;
  text: string;
  status: 'success' | 'error' | 'processing';
  error?: string;
}

export interface TranscriptionMetadata {
  original_file: string;
  total_segments: number;
  successful_segments: number;
  total_duration: number;
  transcription_date: string;
}

export interface TranscriptionResult {
  success: boolean;
  metadata: TranscriptionMetadata;
  full_text: string;
  segments: TranscriptionSegment[];
  error?: string;
}

export interface UploadResponse {
  session_id: string;
  filename: string;
  message: string;
}

export interface SessionStatus {
  filename: string;
  file_path: string;
  status: 'uploaded' | 'processing' | 'completed' | 'error';
  upload_time: string;
  result_file?: string;
  completion_time?: string;
  error?: string;
}

export interface WebSocketMessage {
  type: 'progress' | 'completed' | 'error' | 'heartbeat';
  current?: number;
  total?: number;
  segment?: TranscriptionSegment;
  percentage?: number;
  result?: TranscriptionResult;
  download_url?: string;
  error?: string;
  message?: string;
}