# Steep AI 前端实现细节技术文档

## 项目概览

Steep AI 前端是基于 **Next.js 15.4.3** 和 **React 19.1.0** 构建的现代化Web应用程序，采用 TypeScript 开发，具有视频播放和智能聊天功能的双面板界面。

## 核心技术栈

### 主要依赖

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 15.4.3 | React 全栈框架 |
| React | 19.1.0 | UI 库 |
| TypeScript | ^5 | 类型安全 |
| Tailwind CSS | ^4 | 样式框架 |
| Zustand | ^5.0.6 | 状态管理 |
| Framer Motion | ^12.23.7 | 动画库 |
| React Resizable Panels | ^3.0.3 | 可调整面板 |

### UI 组件库
- **Radix UI** - 无障碍性原语组件
- **Shadcn/UI** - 设计系统和组件库
- **Lucide React** - 图标库
- **Class Variance Authority** - 样式变体管理

## 项目架构

### 目录结构
```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   │   ├── layout.tsx    # 根布局
│   │   ├── page.tsx      # 主页面
│   │   └── globals.css   # 全局样式
│   ├── components/       # React 组件
│   │   ├── ui/          # 基础 UI 组件
│   │   ├── ChatPanel.tsx # 聊天面板
│   │   ├── VideoPlayer.tsx # 视频播放器
│   │   └── ResizablePanels.tsx # 可调整面板
│   ├── lib/             # 工具函数
│   │   └── utils.ts     # 通用工具
│   └── store/           # 状态管理
│       └── appStore.ts  # 全局状态
├── public/              # 静态资源
└── 配置文件...
```

### 设计模式
- **组件化架构**: 采用函数式组件和 React Hooks
- **状态管理**: 使用 Zustand 进行全局状态管理
- **样式系统**: Tailwind CSS + CSS 变量主题系统
- **类型安全**: 完整的 TypeScript 类型定义

## 核心组件详解

### 1. ResizablePanels - 主布局组件

**文件**: `src/components/ResizablePanels.tsx`

```typescript
export function ResizablePanels() {
  return (
    <div className="h-screen w-full">
      <PanelGroup direction="horizontal" className="min-h-screen rounded-lg border">
        <Panel defaultSize={65} minSize={30}>
          <VideoPlayer />
        </Panel>
        <PanelResizeHandle />
        <Panel defaultSize={35} minSize={25}>
          <ChatPanel />
        </Panel>
      </PanelGroup>
    </div>
  );
}
```

**核心特性**:
- 水平双面板布局
- 可拖拽调整面板大小
- 左侧默认占 65%，右侧占 35%
- 最小尺寸限制防止面板过小

### 2. VideoPlayer - 视频播放器组件

**文件**: `src/components/VideoPlayer.tsx`

**核心功能**:
- YouTube 视频嵌入播放
- 从全局状态获取视频信息
- Framer Motion 动画效果
- 响应式设计

**动画实现**:
```typescript
<motion.div 
  initial={{ opacity: 0, scale: 0.95 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={{ duration: 0.5 }}
>
```

**特性**:
- 16:9 宽高比视频容器
- 支持全屏播放
- 视频标题和描述显示
- 渐入动画效果

### 3. ChatPanel - 聊天与笔记面板

**文件**: `src/components/ChatPanel.tsx`

**双模式设计**:
1. **聊天模式**: 实时对话界面
2. **笔记模式**: 文本编辑器

**聊天功能**:
- 消息列表显示
- 实时输入和发送
- AI 回复模拟
- 消息动画效果
- 时间戳显示

**笔记功能**:
- 大型文本域编辑器
- 实时保存到全局状态
- 占满面板高度

**关键特性**:
- 模式切换按钮
- Enter 键发送消息
- 消息动画 (Framer Motion)
- 响应式布局

## 状态管理系统

### Zustand Store 架构

**文件**: `src/store/appStore.ts`

**状态结构**:
```typescript
interface AppState {
  // 聊天状态
  messages: ChatMessage[];
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clearMessages: () => void;
  
  // 笔记状态
  notes: string;
  setNotes: (notes: string) => void;
  
  // UI状态
  currentMode: 'chat' | 'notes';
  setCurrentMode: (mode: 'chat' | 'notes') => void;
  
  // 视频状态
  currentVideo: {
    url: string;
    title: string;
    description: string;
  };
  setCurrentVideo: (video: { url: string; title: string; description: string }) => void;
}
```

**消息数据结构**:
```typescript
export interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
}
```

**状态管理特点**:
- 不可变状态更新
- 自动 ID 和时间戳生成
- 类型安全的 action 定义
- 简洁的状态订阅

## UI 组件系统

### Shadcn/UI 组件库

基于 **Radix UI** 和 **Tailwind CSS** 构建的设计系统。

**核心组件**:

#### Button 组件
```typescript
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
        destructive: "bg-destructive text-white shadow-xs hover:bg-destructive/90",
        outline: "border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 rounded-md gap-1.5 px-3",
        lg: "h-10 rounded-md px-6",
        icon: "size-9",
      },
    },
  }
)
```

#### Card 组件
- 灵活的容器组件
- 支持 Header、Content、Footer 等子组件
- 一致的间距和圆角设计

### 样式系统

#### Tailwind CSS 配置
- **版本**: Tailwind CSS v4
- **主题系统**: CSS 变量 + 明暗主题
- **字体**: Geist Sans 和 Geist Mono
- **动画**: tw-animate-css 增强动画

#### 主题配置
```css
:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  /* ... 更多颜色变量 */
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  /* ... 暗色主题变量 */
}
```

## 动画系统

### Framer Motion 集成

**使用场景**:
1. **页面进入动画**: 组件渐入效果
2. **消息动画**: 聊天消息的出现和消失
3. **交互反馈**: 按钮点击和悬停效果

**常用动画模式**:
```typescript
// 渐入动画
initial={{ opacity: 0, y: 20 }}
animate={{ opacity: 1, y: 0 }}
transition={{ duration: 0.3 }}

// 缩放动画
initial={{ scale: 0.8 }}
animate={{ scale: 1 }}
transition={{ duration: 0.2, delay: 0.1 }}
```

## 开发工具链

### 构建配置

#### Next.js 配置
- **版本**: 15.4.3
- **Turbo 模式**: 开发时启用 `--turbopack`
- **App Router**: 使用最新的应用路由

#### TypeScript 配置
- **严格模式**: 启用所有类型检查
- **路径别名**: `@/*` 映射到 `./src/*`
- **目标**: ES2017

#### ESLint 配置
- 继承 Next.js 推荐配置
- 代码质量和一致性检查

### 开发脚本
```json
{
  "dev": "next dev --turbopack",
  "build": "next build",
  "start": "next start",
  "lint": "next lint"
}
```

## 性能优化

### React 优化
- **函数式组件**: 避免不必要的重渲染
- **状态最小化**: 只在必要时使用状态
- **事件处理优化**: 避免内联函数

### 样式优化
- **Tailwind CSS**: 按需生成样式
- **CSS 变量**: 高效的主题切换
- **原子化类名**: 减少样式重复

### 图标优化
- **Lucide React**: 轻量级 SVG 图标
- **Tree Shaking**: 只导入使用的图标

## 无障碍性设计

### Radix UI 支持
- **键盘导航**: 完整的键盘操作支持
- **ARIA 标签**: 屏幕阅读器友好
- **焦点管理**: 合理的焦点流转

### 设计考虑
- **颜色对比度**: 满足 WCAG 标准
- **语义化 HTML**: 使用正确的 HTML 标签
- **响应式设计**: 支持多种设备尺寸

## 扩展性设计

### 组件化
- **原子设计**: 从基础组件构建复杂界面
- **Props 接口**: 灵活的组件参数
- **组合模式**: 组件间松耦合

### 状态管理
- **模块化 Store**: 可按功能拆分状态
- **中间件支持**: Zustand 支持持久化等中间件
- **类型安全**: 完整的 TypeScript 支持

### 主题系统
- **CSS 变量**: 运行时主题切换
- **组件变体**: CVA 支持的样式变体
- **响应式**: 支持多种屏幕尺寸

## 已知技术债务和改进建议

### 当前限制
1. **AI 回复**: 目前是模拟实现，需要接入真实 AI API
2. **视频源**: 仅支持 YouTube 嵌入，可扩展支持更多平台
3. **持久化**: 状态重新加载后会丢失，需要添加本地存储

### 未来改进方向
1. **实时通信**: WebSocket 支持实时 AI 对话
2. **多媒体支持**: 支持音频、图片等多种媒体格式
3. **协作功能**: 多用户实时协作笔记
4. **离线支持**: PWA 和离线缓存机制
5. **性能监控**: 添加性能分析和用户行为追踪

---

> 本文档基于 Steep AI 前端项目的当前实现状态编写，随项目演进持续更新。 