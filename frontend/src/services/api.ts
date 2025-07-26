import { API_CONFIG, DEFAULT_REQUEST_CONFIG, buildApiUrl } from '@/config/api';
import type { ApiResponse } from '@/types';

// API 错误类
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string,
    public response?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// 请求配置接口
interface RequestConfig extends RequestInit {
  timeout?: number;
  retries?: number;
}

// 通用请求函数
async function request<T = unknown>(
  endpoint: string,
  config: RequestConfig = {}
): Promise<T> {
  const {
    timeout = API_CONFIG.TIMEOUT,
    retries = API_CONFIG.RETRY_ATTEMPTS,
    ...fetchConfig
  } = config;

  const url = buildApiUrl(endpoint);
  const controller = new AbortController();
  
  // 设置超时
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  const requestConfig: RequestInit = {
    ...DEFAULT_REQUEST_CONFIG,
    ...fetchConfig,
    signal: controller.signal,
  };

  let lastError: Error;

  // 重试机制
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(url, requestConfig);
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new ApiError(
          response.status,
          response.statusText,
          `HTTP ${response.status}: ${response.statusText}`,
          response
        );
      }

      // 尝试解析JSON，如果失败则返回文本
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        return await response.text() as T;
      }
    } catch (error) {
      lastError = error as Error;
      
      // 如果是最后一次尝试或者是非网络错误，直接抛出
      if (attempt === retries || error instanceof ApiError) {
        throw error;
      }
      
      // 等待一段时间后重试
      await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }

  throw lastError!;
}

// HTTP 方法
export const api = {
  get: <T = unknown>(endpoint: string, config?: RequestConfig) =>
    request<T>(endpoint, { ...config, method: 'GET' }),

  post: <T = unknown>(endpoint: string, data?: unknown, config?: RequestConfig) =>
    request<T>(endpoint, {
      ...config,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T = unknown>(endpoint: string, data?: unknown, config?: RequestConfig) =>
    request<T>(endpoint, {
      ...config,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T = unknown>(endpoint: string, config?: RequestConfig) =>
    request<T>(endpoint, { ...config, method: 'DELETE' }),

  patch: <T = unknown>(endpoint: string, data?: unknown, config?: RequestConfig) =>
    request<T>(endpoint, {
      ...config,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),
}; 