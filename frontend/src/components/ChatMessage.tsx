"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { HelpCircle, PenTool } from "lucide-react";
import type { ChatMessage } from "@/types";

interface ChatMessageProps {
  message: ChatMessage;
  mounted?: boolean;
  onNeedHelp?: (message: ChatMessage) => void;
  onTakeNotes?: (message: ChatMessage) => void;
  isLatest?: boolean;
}

// 预留的媒体内容类型接口
interface MediaContent {
  type: "image" | "pdf" | "video" | "audio" | "file";
  url: string;
  title?: string;
  thumbnail?: string;
  duration?: number; // for video/audio
  size?: number; // file size in bytes
}

// 扩展的消息接口（预留）
interface ExtendedMessage extends ChatMessage {
  media?: MediaContent[];
  reactions?: string[];
  threadId?: string;
  mentions?: string[];
}

export function ChatMessage({ message, mounted = true, onNeedHelp, onTakeNotes, isLatest = false }: ChatMessageProps) {
  const isUser = message.isUser;

  // 预留的媒体渲染函数
  const renderMedia = (media: MediaContent[]) => {
    // TODO: 实现图片、PDF、视频等媒体内容渲染
    return null;
  };

  // 预留的互动功能
  const handleReaction = (emoji: string) => {
    // TODO: 实现消息反应功能
  };

  const handleReply = () => {
    // TODO: 实现回复功能
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.2, delay: 0.1 }}
        className={`max-w-[80%] min-w-[120px] rounded-lg px-3 py-2 ${
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        }`}
      >
        {/* 消息内容 */}
        <div className="text-[13px] break-words leading-relaxed">
          {isUser ? (
            // 用户消息：纯文本
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            // AI消息：支持Markdown
            <div className="markdown-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // 代码块渲染
                  code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    return match ? (
                      <div className="my-3 first:mt-0 last:mb-0">
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                          className="!rounded-lg !text-xs !my-0"
                        >
                          {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      </div>
                    ) : (
                      <code
                        className={`${className} bg-muted/40 px-1.5 py-0.5 rounded text-xs font-mono`}
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  },
                  // 段落样式 - 优化间距
                  p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                  // 列表样式 - 改进间距和缩进
                  ul: ({ children }) => (
                    <ul className="list-disc ml-4 mb-3 last:mb-0 space-y-1">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal ml-4 mb-3 last:mb-0 space-y-1">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-[13px] leading-relaxed pl-1">{children}</li>
                  ),
                  // 标题样式 - 优化层级和间距
                  h1: ({ children }) => (
                    <h1 className="text-base font-bold mb-3 mt-4 first:mt-0 border-b border-muted/30 pb-1">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-[14px] font-bold mb-2 mt-3 first:mt-0">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-[13px] font-semibold mb-2 mt-2 first:mt-0">{children}</h3>
                  ),
                  h4: ({ children }) => (
                    <h4 className="text-[13px] font-medium mb-1 mt-2 first:mt-0">{children}</h4>
                  ),
                  // 引用样式 - 改进视觉效果
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-3 border-muted-foreground/40 pl-4 py-2 my-3 bg-muted/20 rounded-r-md italic">
                      {children}
                    </blockquote>
                  ),
                  // 链接样式 - 改进可读性
                  a: ({ children, href }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline decoration-1 underline-offset-2 hover:decoration-2 transition-all"
                    >
                      {children}
                    </a>
                  ),
                  // 分割线
                  hr: () => <hr className="my-4 border-0 h-px bg-muted-foreground/30" />,
                  // 表格样式 - 改进布局和间距
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3 first:mt-0 last:mb-0">
                      <table className="min-w-full border-collapse border border-muted/50 rounded-md overflow-hidden">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => <thead className="bg-muted/30">{children}</thead>,
                  th: ({ children }) => (
                    <th className="border border-muted/50 px-3 py-2 font-semibold text-[12px] text-left">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-muted/50 px-3 py-2 text-[12px]">{children}</td>
                  ),
                  // 强调样式
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  // 删除线
                  del: ({ children }) => <del className="line-through opacity-75">{children}</del>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* 预留：媒体内容渲染区域 */}
        {/* TODO: 实现媒体内容显示 */}
        {/* {(message as ExtendedMessage).media && renderMedia((message as ExtendedMessage).media!)} */}

        {/* 时间戳 */}
        <p className="text-xs opacity-70 mt-1">
          {mounted ? message.timestamp.toLocaleTimeString() : ""}
        </p>

        {/* AI消息操作按钮 - 只在最新消息显示 */}
        {!isUser && isLatest && (
          <div className="flex items-center gap-2 mt-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs opacity-60 hover:opacity-100 hover:bg-muted/50"
              onClick={() => onNeedHelp?.(message)}
            >
              <HelpCircle className="w-3 h-3 mr-1" />
              没听懂
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs opacity-60 hover:opacity-100 hover:bg-muted/50"
              onClick={() => onTakeNotes?.(message)}
            >
              <PenTool className="w-3 h-3 mr-1" />
              记笔记
            </Button>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
