import { api } from './api';
import { API_ENDPOINTS, DEFAULT_MESSAGE_CONFIG } from '@/config/api';
import type { SendMessageRequest, SendMessageResponse, AgentType } from '@/types';

// 代理服务类
export class AgentService {
  /**
   * 发送消息给指定的代理
   */
  static async sendMessage(
    agentType: AgentType,
    message: string,
    config?: Partial<SendMessageRequest>
  ): Promise<string> {
    const endpoint = agentType === 'web_agent' 
      ? API_ENDPOINTS.AGENTS.WEB_AGENT 
      : API_ENDPOINTS.AGENTS.AGNO_ASSIST;

    const requestData: SendMessageRequest = {
      ...DEFAULT_MESSAGE_CONFIG,
      ...config,
      message,
    };

    try {
      const response = await api.post<string>(endpoint, requestData);
      return response;
    } catch (error) {
      console.error(`Error sending message to ${agentType}:`, error);
      throw new Error(`发送消息失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  /**
   * 发送消息给网络搜索代理
   */
  static async sendToWebAgent(
    message: string,
    config?: Partial<SendMessageRequest>
  ): Promise<string> {
    return this.sendMessage('web_agent', message, config);
  }

  /**
   * 发送消息给本地助手
   */
  static async sendToAgnoAssist(
    message: string,
    config?: Partial<SendMessageRequest>
  ): Promise<string> {
    return this.sendMessage('agno_assist', message, config);
  }
}

// 导出便捷方法
export const agentService = AgentService; 