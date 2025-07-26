import { buildApiUrl, API_ENDPOINTS } from '@/config/api';

export interface YouTubeProcessResponse {
  success: boolean;
  video_id: string | null;
  message: string;
  status: 'ready' | 'processing' | 'not_found';
  transcript_count: number;
}

export interface YouTubeStatusResponse {
  video_id: string;
  status: 'ready' | 'processing' | 'not_found';
  message: string;
  transcript_count: number;
  has_video_info: boolean;
}

export interface TranscriptSegment {
  id: number;
  start_time: number;
  duration: number;
  text: string;
  language: string;
  end_time: number;
}

export interface VideoInfo {
  video_id: string;
  title: string | null;
  duration: number | null;
  upload_date: string | null;
  channel_name: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

class YouTubeService {
  /**
   * 快速处理YouTube URL（后台异步处理）
   */
  async quickProcess(url: string): Promise<YouTubeProcessResponse> {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.YOUTUBE.QUICK_PROCESS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '处理失败');
      }

      return await response.json();
    } catch (error) {
      console.error('YouTube quick process failed:', error);
      throw error;
    }
  }

  /**
   * 同步处理YouTube URL（等待处理完成）
   */
  async process(url: string, mergeSegments: boolean = true): Promise<YouTubeProcessResponse> {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.YOUTUBE.PROCESS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          url, 
          merge_segments: mergeSegments,
          auto_process: true 
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '处理失败');
      }

      return await response.json();
    } catch (error) {
      console.error('YouTube process failed:', error);
      throw error;
    }
  }

  /**
   * 获取处理状态
   */
  async getStatus(videoId: string): Promise<YouTubeStatusResponse> {
    try {
      const response = await fetch(buildApiUrl(`${API_ENDPOINTS.YOUTUBE.STATUS}/${videoId}`));

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
   * 获取转录文本
   */
  async getTranscript(videoId: string): Promise<TranscriptSegment[]> {
    try {
      const response = await fetch(buildApiUrl(`${API_ENDPOINTS.YOUTUBE.TRANSCRIPT}/${videoId}`));

      if (!response.ok) {
        if (response.status === 404) {
          return []; // 转录文本不存在
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || '获取转录文本失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get transcript failed:', error);
      throw error;
    }
  }

  /**
   * 搜索转录文本
   */
  async searchTranscript(videoId: string, query: string): Promise<TranscriptSegment[]> {
    try {
      const url = buildApiUrl(`${API_ENDPOINTS.YOUTUBE.TRANSCRIPT}/${videoId}/search`);
      const searchUrl = `${url}?q=${encodeURIComponent(query)}`;
      
      const response = await fetch(searchUrl);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '搜索失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Search transcript failed:', error);
      throw error;
    }
  }

  /**
   * 获取指定时间范围的转录文本
   */
  async getTranscriptByTimeRange(
    videoId: string, 
    startTime: number, 
    endTime: number
  ): Promise<TranscriptSegment[]> {
    try {
      const url = buildApiUrl(`${API_ENDPOINTS.YOUTUBE.TRANSCRIPT}/${videoId}/time-range`);
      const rangeUrl = `${url}?start_time=${startTime}&end_time=${endTime}`;
      
      const response = await fetch(rangeUrl);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '获取时间范围转录文本失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get transcript by time range failed:', error);
      throw error;
    }
  }

  /**
   * 获取视频信息
   */
  async getVideoInfo(videoId: string): Promise<VideoInfo | null> {
    try {
      const response = await fetch(buildApiUrl(`${API_ENDPOINTS.YOUTUBE.INFO}/${videoId}`));

      if (!response.ok) {
        if (response.status === 404) {
          return null; // 视频信息不存在
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || '获取视频信息失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get video info failed:', error);
      throw error;
    }
  }

  /**
   * 提取YouTube视频ID
   */
  extractVideoId(url: string): string | null {
    const match = url.match(
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/
    );
    return match ? match[1] : null;
  }

  /**
   * 验证YouTube URL
   */
  validateYouTubeUrl(url: string): boolean {
    const youtubeRegex =
      /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/;
    return youtubeRegex.test(url);
  }

  /**
   * 轮询处理状态直到完成
   */
  async pollStatus(videoId: string, maxAttempts: number = 30, interval: number = 2000): Promise<YouTubeStatusResponse> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const status = await this.getStatus(videoId);
      
      if (status.status === 'ready' || status.status === 'not_found') {
        return status;
      }
      
      // 等待指定时间后继续轮询
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    
    throw new Error('处理超时');
  }
}

export const youtubeService = new YouTubeService();