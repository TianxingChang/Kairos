import { buildApiUrl, API_ENDPOINTS } from '@/config/api';

export interface VideoQARequest {
  video_id: string;
  timestamp: number;
  question: string;
  user_id?: string;
  session_id?: string;
  context_before?: number;
  context_after?: number;
}

export interface VideoQAResponse {
  success: boolean;
  answer: string;
  context_transcript: string;
  timestamp_info: {
    target_time: number;
    target_formatted: string;
    context_start: number;
    context_end: number;
    context_duration: number;
  };
  video_info: {
    video_id: string;
    title: string;
    duration: number | null;
    channel: string;
  };
  error?: string;
}

export interface TimestampParseResponse {
  success: boolean;
  original: string;
  seconds: number;
  formatted: string;
  hours_minutes_seconds: string;
}

export interface VideoContextResponse {
  success: boolean;
  context_transcript: string;
  timestamp_range: {
    start: number;
    end: number;
    target: number;
  };
  timestamp_info: {
    target_time: number;
    target_formatted: string;
    context_start: number;
    context_end: number;
    before_seconds: number;
    after_seconds: number;
  };
  segments: Array<{
    start: number;
    end: number;
    text: string;
    duration: number;
  }>;
}

export interface VideoStatusResponse {
  success: boolean;
  video_id: string;
  status: 'ready' | 'processing' | 'not_found';
  message: string;
  ready_for_qa: boolean;
  video_info?: {
    title: string | null;
    duration: number | null;
    channel: string | null;
    upload_date: string | null;
    created_at: string | null;
  };
  transcript_info?: {
    segment_count: number;
    language: string | null;
    file_path: string | null;
    file_size: number | null;
    created_at: string | null;
  };
}

export interface YouTubeUploadRequest {
  url: string;
  user_id?: string;
}

export interface YouTubeUploadResponse {
  success: boolean;
  video_id: string;
  message: string;
  status: 'processing' | 'ready' | 'error';
  video_info?: {
    video_id: string;
    title?: string;
    duration?: number;
    channel?: string;
    created_at?: string;
  };
  error?: string;
}

export interface FullVideoRequest {
  video_id: string;
  question: string;
  user_id?: string;
  session_id?: string;
}

export interface FullVideoResponse {
  success: boolean;
  answer: string;
  full_transcript: string;
  video_info: {
    video_id: string;
    title: string;
    channel: string;
    duration: number;
    total_segments: number;
    text_segments: number;
  };
  transcript_stats?: {
    total_segments: number;
    text_segments: number;
    duration_minutes: number;
    transcript_length: number;
  };
  error?: string;
}

class VideoQAService {
  /**
   * 智能视频问答
   */
  async askQuestion(request: VideoQARequest): Promise<VideoQAResponse> {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.FRONTEND.VIDEO_QA.ASK), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: request.video_id,
          timestamp: request.timestamp,
          question: request.question,
          user_id: request.user_id || 'frontend_user',
          session_id: request.session_id || `session_${Date.now()}`,
          context_before: request.context_before || 20,
          context_after: request.context_after || 5,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '问答失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Video QA failed:', error);
      throw error;
    }
  }

  /**
   * 完整视频问答 (直接调用)
   */
  async askFullVideoQuestion(request: FullVideoRequest): Promise<FullVideoResponse> {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.FRONTEND.VIDEO_QA.ASK_FULL), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: request.video_id,
          question: request.question,
          user_id: request.user_id || 'frontend_user',
          session_id: request.session_id || `session_${Date.now()}`,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '完整视频问答失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Full video QA failed:', error);
      throw error;
    }
  }

  /**
   * 完整视频问答 (使用Agent)
   */
  async askFullVideoQuestionWithAgent(request: FullVideoRequest): Promise<FullVideoResponse> {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.FRONTEND.VIDEO_QA.ASK_FULL_AGENT), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: request.video_id,
          question: request.question,
          user_id: request.user_id || 'frontend_user',
          session_id: request.session_id || `session_${Date.now()}`,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '完整视频Agent问答失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Full video QA with Agent failed:', error);
      throw error;
    }
  }

  /**
   * 获取视频时间点上下文
   */
  async getVideoContext(
    videoId: string,
    timestamp: string | number,
    before: number = 20,
    after: number = 5
  ): Promise<VideoContextResponse> {
    try {
      const url = buildApiUrl(`${API_ENDPOINTS.FRONTEND.VIDEO_QA.CONTEXT}/${videoId}`);
      const params = new URLSearchParams({
        timestamp: timestamp.toString(),
        before: before.toString(),
        after: after.toString(),
      });

      const response = await fetch(`${url}?${params}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '获取上下文失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get video context failed:', error);
      throw error;
    }
  }

  /**
   * 解析时间戳
   */
  async parseTimestamp(timestamp: string): Promise<TimestampParseResponse> {
    try {
      const url = buildApiUrl(API_ENDPOINTS.FRONTEND.VIDEO_QA.PARSE_TIMESTAMP);
      const response = await fetch(`${url}?timestamp=${encodeURIComponent(timestamp)}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '时间戳解析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Parse timestamp failed:', error);
      throw error;
    }
  }

  /**
   * 检查视频状态
   */
  async getVideoStatus(videoId: string): Promise<VideoStatusResponse> {
    try {
      const response = await fetch(
        buildApiUrl(`${API_ENDPOINTS.FRONTEND.VIDEO_QA.VIDEO_STATUS}/${videoId}`)
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '获取视频状态失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get video status failed:', error);
      throw error;
    }
  }

  /**
   * 上传YouTube视频
   */
  async uploadYouTubeVideo(request: YouTubeUploadRequest): Promise<YouTubeUploadResponse> {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.FRONTEND.YOUTUBE.UPLOAD), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...request,
          user_id: request.user_id || 'frontend_user',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '上传失败');
      }

      return await response.json();
    } catch (error) {
      console.error('YouTube upload failed:', error);
      throw error;
    }
  }

  /**
   * 获取YouTube视频状态
   */
  async getYouTubeStatus(videoId: string): Promise<VideoStatusResponse> {
    try {
      const response = await fetch(
        buildApiUrl(`${API_ENDPOINTS.FRONTEND.YOUTUBE.STATUS}/${videoId}`)
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '获取状态失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get YouTube status failed:', error);
      throw error;
    }
  }

  /**
   * 搜索已处理的视频
   */
  async searchVideos(query?: string, limit: number = 10) {
    try {
      const url = buildApiUrl(API_ENDPOINTS.FRONTEND.YOUTUBE.SEARCH);
      const params = new URLSearchParams({ limit: limit.toString() });
      if (query) {
        params.set('query', query);
      }

      const response = await fetch(`${url}?${params}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '搜索失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Search videos failed:', error);
      throw error;
    }
  }

  /**
   * 轮询视频处理状态
   */
  async pollVideoStatus(
    videoId: string,
    maxAttempts: number = 30,
    interval: number = 10000
  ): Promise<VideoStatusResponse> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const status = await this.getYouTubeStatus(videoId);

      if (status.status === 'ready' || status.status === 'not_found') {
        return status;
      }

      // 等待指定时间后继续轮询
      await new Promise(resolve => setTimeout(resolve, interval));
    }

    throw new Error('处理超时');
  }

  /**
   * 提取YouTube视频ID
   */
  extractVideoId(url: string): string | null {
    const patterns = [
      /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/,
      /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)/,
      /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]+)/,
      /(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]+)/,
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) {
        return match[1];
      }
    }

    // 如果直接是视频ID
    if (/^[a-zA-Z0-9_-]{11}$/.test(url)) {
      return url;
    }

    return null;
  }

  /**
   * 验证YouTube URL
   */
  validateYouTubeUrl(url: string): boolean {
    return this.extractVideoId(url) !== null;
  }

  /**
   * 格式化时间戳
   */
  formatTimestamp(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }

  /**
   * 解析时间戳为秒数
   */
  parseTimestampToSeconds(timestamp: string): number {
    // 匹配 MM:SS 或 HH:MM:SS 格式
    const timePattern = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(timestamp);
    if (timePattern) {
      const hours = timePattern[3] ? parseInt(timePattern[1]) : 0;
      const minutes = timePattern[3] ? parseInt(timePattern[2]) : parseInt(timePattern[1]);
      const seconds = timePattern[3] ? parseInt(timePattern[3]) : parseInt(timePattern[2]);
      
      return hours * 3600 + minutes * 60 + seconds;
    }

    // 直接是数字格式
    const seconds = parseFloat(timestamp);
    if (!isNaN(seconds)) {
      return seconds;
    }

    throw new Error(`无法解析时间戳: ${timestamp}`);
  }
}

export const videoQAService = new VideoQAService();