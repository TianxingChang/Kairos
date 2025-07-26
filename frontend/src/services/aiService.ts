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

export interface FeynmanFrameworkRequest {
  videoTitle: string;
  videoDescription: string;
  currentTime?: number;
  existingNotes: string;
}

export interface FeynmanFrameworkResponse {
  framework: string;
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

  async generateFeynmanFramework(request: FeynmanFrameworkRequest): Promise<FeynmanFrameworkResponse> {
    try {
      // 暂时使用模拟响应，后续可以替换为真实的 AI API 调用
      return await this.mockFeynmanFramework(request);
    } catch (error) {
      console.error('Feynman framework generation error:', error);
      return {
        framework: '',
        error: error instanceof Error ? error.message : '未知错误',
      };
    }
  }

  private async mockFeynmanFramework(request: FeynmanFrameworkRequest): Promise<FeynmanFrameworkResponse> {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1500));

    const { videoTitle, videoDescription } = request;
    
    // 生成费曼笔记框架的模拟内容
    const framework = `## 📋 核心概念梳理

**请尝试用自己的话解释以下概念，就像在教给一个朋友一样：**

### 1. 主要概念
- **${videoTitle}的核心思想是什么？**
  *(请用简单易懂的语言描述)*

### 2. 关键要点
- **有哪些重要的细节或步骤？**
  *(列出2-3个最重要的点)*

### 3. 实际应用
- **这个知识可以用在哪里？**
  *(想想具体的例子或场景)*

### 4. 类比理解
- **你能用什么类比来解释这个概念？**
  *(比如像什么日常生活中的事物)*

### 5. 潜在困惑
- **哪些地方容易混淆或理解错误？**
  *(诚实记录你的疑问)*

### 6. 个人总结
- **用一句话总结这个内容**
  *(检验你是否真正理解)*

---

**💡 记录提示：**
- 用自己的话写，不要复制原文
- 如果某个部分解释不清楚，说明需要重新学习
- 完成后可以使用AI检查你的理解是否准确`;

    return {
      framework,
    };
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