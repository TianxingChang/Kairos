# UI 组件说明

## LoadingDots 组件

一个优雅的三点波动加载动画组件，用于表示正在加载的状态。

### 功能特性

- 🌊 **波动动画**: 三个小点依次波动，营造流畅的加载效果
- 📏 **多种尺寸**: 支持 `sm`、`md`、`lg` 三种尺寸
- 🎨 **自适应颜色**: 使用 `bg-current` 自动适应父元素的文字颜色
- ⚡ **高性能**: 基于 Framer Motion，流畅的动画体验

### 使用方法

```tsx
import { LoadingDots } from '@/components/ui/loading-dots';

// 基础用法
<LoadingDots />

// 指定尺寸
<LoadingDots size="sm" />

// 自定义样式
<LoadingDots size="lg" className="text-blue-500" />
```

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `size` | `"sm" \| "md" \| "lg"` | `"md"` | 点的尺寸 |
| `className` | `string` | `""` | 额外的CSS类名 |

### 尺寸规格

- **sm**: `w-1 h-1` (4px × 4px)
- **md**: `w-1.5 h-1.5` (6px × 6px)
- **lg**: `w-2 h-2` (8px × 8px)

### 在 ChatPanel 中的应用

在聊天界面中，LoadingDots 组件被用于两个场景：

1. **消息加载提示**: 在等待AI回复时显示 "正在思考..." 消息
2. **发送按钮状态**: 发送消息时按钮内显示加载动画

这种设计为用户提供了清晰的视觉反馈，改善了交互体验。 