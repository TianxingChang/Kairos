export interface AIQueryRequest {
  message: string;
  context?: {
    videoTime?: number;
    selectedContexts?: Array<{
      id: string;
      type: string;
      title: string;
      description?: string;
      timestamp?: number;
    }>;
    previousMessages?: Array<{
      type: 'user' | 'ai';
      content: string;
    }>;
  };
}

export interface AIQueryResponse {
  response: string;
  error?: string;
}

export class AIService {
  private static instance: AIService;
  private apiEndpoint: string;

  constructor() {
    this.apiEndpoint = process.env.NEXT_PUBLIC_AI_API_ENDPOINT || '/api/ai/query';
  }

  static getInstance(): AIService {
    if (!AIService.instance) {
      AIService.instance = new AIService();
    }
    return AIService.instance;
  }

  async query(request: AIQueryRequest): Promise<AIQueryResponse> {
    try {
      // 暂时使用模拟响应，后续可以替换为真实的 AI API 调用
      return await this.mockQuery(request);

      // 真实的 API 调用会是这样的：
      // const response = await fetch(this.apiEndpoint, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify(request),
      // });
      // 
      // if (!response.ok) {
      //   throw new Error(`AI API error: ${response.status}`);
      // }
      // 
      // return await response.json();
    } catch (error) {
      console.error('AI service error:', error);
      return {
        response: '',
        error: error instanceof Error ? error.message : '未知错误',
      };
    }
  }

  private async mockQuery(request: AIQueryRequest): Promise<AIQueryResponse> {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 1200));

    const { message, context } = request;
    
    // 简单的模拟响应逻辑
    const responses = [
      `关于您的问题"${message}"，这是一个很有趣的观点。基于视频内容${context?.videoTime ? `在 ${this.formatTime(context.videoTime)} 时刻` : ''}，我可以为您提供以下见解：

这个问题涉及多个方面，需要从不同角度来分析。首先，我们可以考虑...`,

      `您提到的"${message}"确实是一个重要的话题。${context?.videoTime ? `特别是在视频的 ${this.formatTime(context.videoTime)} 这个时间点，` : ''}我注意到了几个关键要素：

1. **核心概念**：这里涉及的主要思想是...
2. **实际应用**：在实践中，这通常意味着...
3. **注意事项**：需要特别关注的是...`,

      `基于您的询问"${message}"${context?.videoTime ? `以及视频 ${this.formatTime(context.videoTime)} 处的内容` : ''}，我想分享一些相关的思考：

这个概念的核心在于理解其背后的原理。从历史发展来看，这个观点经历了多个阶段的演进...`,
    ];

    const randomResponse = responses[Math.floor(Math.random() * responses.length)];
    
    return {
      response: randomResponse,
    };
  }

  private formatTime(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }
}

export const aiService = AIService.getInstance(); 