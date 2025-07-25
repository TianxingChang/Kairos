// API 基础配置
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || '',
  VERSION: 'v1',
  TIMEOUT: 30000, // 30秒超时
  RETRY_ATTEMPTS: 3,
} as const;

// API 端点
export const API_ENDPOINTS = {
  AGENTS: {
    WEB_AGENT: '/agents/web_agent/runs',
    AGNO_ASSIST: '/agents/agno_assist/runs',
  },
  HEALTH: '/health',
  PLAYGROUND: '/playground',
} as const;

// 默认请求配置
export const DEFAULT_REQUEST_CONFIG = {
  headers: {
    'Content-Type': 'application/json',
  },
} as const;

// 构建完整的API URL
export const buildApiUrl = (endpoint: string): string => {
  const { BASE_URL, VERSION } = API_CONFIG;
  const baseUrl = BASE_URL || window.location.origin;
  return `${baseUrl}/api/${VERSION}${endpoint}`;
};

// 默认消息配置
export const DEFAULT_MESSAGE_CONFIG = {
  stream: false,
  model: 'gpt-4.1',
  user_id: 'user_1',
  session_id: 'session_1',
} as const; 