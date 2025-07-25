"use client";

import { LoadingDots } from "@/components/ui/loading-dots";
import { LoadingDotsAlt } from "@/components/ui/loading-dots-alt";
import { Card } from "@/components/ui/card";

export default function TestAnimationPage() {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <h1 className="text-3xl font-bold text-center mb-8">LoadingDots 动画测试</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 主要版本 */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">主要版本 - LoadingDots</h2>
            <div className="space-y-6">
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">小尺寸 (sm)</p>
                <LoadingDots size="sm" className="text-blue-500" />
              </div>

              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">中等尺寸 (md)</p>
                <LoadingDots size="md" className="text-green-500" />
              </div>

              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">大尺寸 (lg)</p>
                <LoadingDots size="lg" className="text-purple-500" />
              </div>
            </div>
          </Card>

          {/* 替代版本 */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">替代版本 - LoadingDotsAlt</h2>
            <div className="space-y-6">
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">小尺寸 (sm)</p>
                <LoadingDotsAlt size="sm" className="text-red-500" />
              </div>

              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">中等尺寸 (md)</p>
                <LoadingDotsAlt size="md" className="text-orange-500" />
              </div>

              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">大尺寸 (lg)</p>
                <LoadingDotsAlt size="lg" className="text-pink-500" />
              </div>
            </div>
          </Card>
        </div>

        {/* 聊天界面模拟 */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">聊天界面效果模拟</h2>
          <div className="space-y-4">
            {/* 模拟消息 */}
            <div className="flex justify-end">
              <div className="max-w-xs bg-primary text-primary-foreground rounded-lg px-3 py-2">
                <p className="text-sm">你好，请帮我解释一下这个概念</p>
              </div>
            </div>

            {/* 模拟加载消息 */}
            <div className="flex justify-start">
              <div className="max-w-xs bg-muted rounded-lg px-3 py-2">
                <div className="flex items-center space-x-2">
                  <LoadingDots size="sm" className="text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">正在思考...</span>
                </div>
              </div>
            </div>

            {/* 模拟发送按钮 */}
            <div className="flex justify-center pt-4">
              <div className="bg-gray-300 rounded-xl px-4 py-2 flex items-center space-x-2">
                <LoadingDots size="sm" className="text-white" />
                <span className="text-sm">发送按钮状态</span>
              </div>
            </div>
          </div>
        </Card>

        {/* 动画参数说明 */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">动画参数说明</h2>
          <div className="text-sm text-muted-foreground space-y-2">
            <p>
              <strong>主要版本特性：</strong>
            </p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li>Y轴波动：0 → -4 → 0 (像素) - 温和波动</li>
              <li>缩放效果：1 → 1.05 → 1 - 轻微缩放</li>
              <li>透明度：0.4 → 1 → 0.4 - 柔和渐变</li>
              <li>动画时长：0.9秒 - 稳定节奏</li>
              <li>延迟间隔：0.15秒</li>
            </ul>

            <p className="pt-2">
              <strong>替代版本特性：</strong>
            </p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li>Y轴波动：0 → -10 → 0 (像素)</li>
              <li>动画时长：0.6秒</li>
              <li>延迟间隔：0.1秒</li>
            </ul>
          </div>
        </Card>
      </div>
    </div>
  );
}
