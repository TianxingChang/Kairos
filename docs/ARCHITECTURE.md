# 前端架构文档

## 📁 文件结构优化

### 新的目录结构

```
frontend/src/
├── types/           # 类型定义
│   └── index.ts     # 全局类型定义
├── config/          # 配置文件
│   └── api.ts       # API配置和端点
├── services/        # 服务层
│   ├── index.ts     # 统一导出
│   ├── api.ts       # 通用API请求封装
│   └── agents.ts    # AI代理服务
├── hooks/           # 自定义Hooks
│   ├── index.ts     # 统一导出
│   ├── useChat.ts   # 聊天功能Hook
│   ├── useAutoResize.ts   # 自动调整高度Hook
│   └── useScrollToBottom.ts   # 自动滚动Hook
├── store/           # 状态管理
│   ├── index.ts     # 主store
│   └── modules/     # 按功能模块拆分
│       ├── chatStore.ts     # 聊天状态
│       ├── videoStore.ts    # 视频状态
│       ├── uiStore.ts       # UI状态
│       └── contextStore.ts  # 上下文状态
├── components/      # 组件
└── lib/            # 工具函数
```

## 🔧 主要优化点

### 1. 网络请求层优化

**之前的问题:**
- 网络请求逻辑散落在组件中
- 没有统一的错误处理
- 缺少重试机制和超时控制

**优化后的解决方案:**
- `services/api.ts`: 通用API请求封装，支持重试、超时、错误处理
- `services/agents.ts`: 专门的AI代理服务
- `config/api.ts`: 统一的API配置管理

### 2. 状态管理优化

**之前的问题:**
- 单一文件包含所有状态逻辑
- 状态耦合度高，不利于维护

**优化后的解决方案:**
- 按功能模块拆分store (chat、video、ui、context)
- 使用Zustand的slice模式
- 支持开发工具调试

### 3. 自定义Hooks抽离

**之前的问题:**
- 组件中包含重复的逻辑
- 难以测试和复用

**优化后的解决方案:**
- `useChat`: 聊天功能逻辑
- `useAutoResize`: 自动调整textarea高度
- `useScrollToBottom`: 自动滚动到底部

### 4. 类型安全提升

**优化点:**
- 集中的类型定义
- API请求和响应的类型约束
- 更好的TypeScript支持

## 🚀 使用示例

### 发送消息

```typescript
// 之前：在组件中直接写fetch逻辑
const response = await fetch('/api/v1/agents/web_agent/runs', {
  method: 'POST',
  // ...
});

// 现在：使用服务层
import { useChat } from '@/hooks';

const { sendToWebAgent, isSending } = useChat();
await sendToWebAgent('你好');
```

### 状态管理

```typescript
// 之前：从单一store获取所有状态
const { messages, currentMode, notes, ... } = useAppStore();

// 现在：按需获取相关状态
const { messages } = useAppStore();        // 聊天相关
const { currentMode } = useAppStore();     // UI相关
const { currentVideo } = useAppStore();    // 视频相关
```

### 自定义Hooks

```typescript
// 自动调整高度
const textareaRef = useRef<HTMLTextAreaElement>(null);
useAutoResize(textareaRef, inputValue);

// 自动滚动
const scrollRef = useScrollToBottom<HTMLDivElement>({ 
  dependencies: [messages] 
});
```

## 📝 开发规范

### 1. API请求
- 所有API请求都应通过服务层进行
- 使用统一的错误处理
- 避免在组件中直接使用fetch

### 2. 状态管理
- 新功能优先考虑是否需要新的store模块
- 保持单一职责原则
- 使用TypeScript确保类型安全

### 3. 组件开发
- 抽离复用逻辑到自定义Hook
- 保持组件简洁，专注UI渲染
- 优先使用已有的服务和Hook

## 🔄 迁移指南

如果需要添加新功能，请按以下步骤进行：

1. **定义类型**: 在 `types/index.ts` 中添加相关类型
2. **创建服务**: 在 `services/` 中添加API调用逻辑
3. **添加状态**: 在适当的store模块中添加状态管理
4. **创建Hook**: 将复用逻辑抽离到自定义Hook
5. **更新组件**: 使用新的服务和Hook重构组件

这种架构确保了代码的可维护性、可测试性和可扩展性。 