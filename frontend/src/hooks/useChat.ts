import { useState, useCallback } from 'react';
import { useAppStore } from '@/store';
import { agentService } from '@/services/agents';
import type { AgentType } from '@/types';

export function useChat() {
  const [isSending, setIsSending] = useState(false);
  const { addMessage } = useAppStore();

  const sendMessage = useCallback(async (
    message: string,
    agentType: AgentType = 'agno_assist'
  ): Promise<void> => {
    if (!message.trim() || isSending) return;

    setIsSending(true);

    // 添加用户消息
    addMessage({
      content: message.trim(),
      isUser: true,
    });

    try {
      // 发送消息给AI代理
      const response = await agentService.sendMessage(agentType, message);
      
      // 添加AI回复
      addMessage({
        content: response,
        isUser: false,
      });
    } catch (error) {
      console.error('Error sending message:', error);
      
      // 添加错误消息
      addMessage({
        content: '抱歉，发生了错误。请稍后再试。',
        isUser: false,
      });
    } finally {
      setIsSending(false);
    }
  }, [isSending, addMessage]);

  const sendToWebAgent = useCallback((message: string) => {
    return sendMessage(message, 'web_agent');
  }, [sendMessage]);

  const sendToAgnoAssist = useCallback((message: string) => {
    return sendMessage(message, 'agno_assist');
  }, [sendMessage]);

  return {
    isSending,
    sendMessage,
    sendToWebAgent,
    sendToAgnoAssist,
  };
} 