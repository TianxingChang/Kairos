"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Typography from "@tiptap/extension-typography";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import CodeBlockLowlight from "@tiptap/extension-code-block-lowlight";
import Placeholder from "@tiptap/extension-placeholder";
import Dropcursor from "@tiptap/extension-dropcursor";
import { createLowlight, common } from "lowlight";
import { Button } from "@/components/ui/button";
import { TimestampExtension } from "@/extensions/TimestampExtension";
import SlashCommand from "@/extensions/SlashCommand";
import { AIQueryPanel } from "@/components/AIQueryPanel";
import { SelectionMenu } from "@/components/SelectionMenu";
import { aiService } from "@/services/aiService";
import {
  Code2,
  Quote,
  Heading1,
  Heading2,
  Heading3,
  Image as ImageIcon,
  Undo,
  Redo,
  Clock,
  Bot,
  GraduationCap,
} from "lucide-react";
import { useCallback, useState, useEffect } from "react";
import { useAppStore } from "@/store";

// 创建lowlight实例并注册常用语言
const lowlight = createLowlight(common);

interface TiptapEditorProps {
  content: string;
  onChange: (content: string) => void;
  placeholder?: string;
  className?: string;
  onScreenshot?: () => Promise<string>; // 返回base64图片数据
}

export function TiptapEditor({
  content,
  onChange,
  placeholder = "开始写作，按空格键使用AI，按 / 键使用命令",
  className = "",
  onScreenshot,
}: TiptapEditorProps) {
  const { currentVideoTime } = useAppStore();
  const [showAIQuery, setShowAIQuery] = useState(false);
  const [selectionMenu, setSelectionMenu] = useState({
    isVisible: false,
    position: { x: 0, y: 0 },
    selectedText: "",
  });

  const handleShowAIQuery = useCallback(() => {
    setShowAIQuery(true);
  }, []);

  const handleCloseAIQuery = useCallback(() => {
    setShowAIQuery(false);
  }, []);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        codeBlock: false, // 禁用默认的代码块，使用lowlight版本
      }),
      Typography,
      Placeholder.configure({
        placeholder,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class:
            "text-primary underline decoration-1 underline-offset-2 hover:decoration-2 transition-all",
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: "max-w-full h-auto rounded-lg",
        },
      }),
      CodeBlockLowlight.configure({
        lowlight,
        defaultLanguage: "plaintext",
        HTMLAttributes: {
          class: "code-block-custom",
          style: "padding: 0; margin: 0;",
        },
      }),
      Dropcursor.configure({
        color: "#3b82f6",
        width: 3,
      }),
      TimestampExtension,
      SlashCommand(onScreenshot, currentVideoTime, handleShowAIQuery),
    ],
    content,
    immediatelyRender: false, // 修复SSR水合问题
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    onSelectionUpdate: ({ editor }) => {
      const { from, to, empty } = editor.state.selection;

      if (!empty) {
        // 有文本被选中
        const selectedText = editor.state.doc.textBetween(from, to, " ");

        if (selectedText.trim()) {
          // 获取选择的位置
          const coordsStart = editor.view.coordsAtPos(from);
          const coordsEnd = editor.view.coordsAtPos(to);

          // 获取编辑器容器的边界
          const editorElement = editor.view.dom;
          const editorRect = editorElement.getBoundingClientRect();

          // 计算选中区域的中心点
          let centerX = coordsStart.left + (coordsEnd.right - coordsStart.left) / 2;

          // 菜单尺寸
          const menuWidth = 150; // 菜单宽度（调整为更紧凑的尺寸）
          const menuHeight = 50; // 只有一个按钮，高度更小
          const halfMenuWidth = menuWidth / 2;

          // 确保菜单不超出编辑器的左右边界
          const editorLeft = editorRect.left;
          const editorRight = editorRect.right;

          if (centerX - halfMenuWidth < editorLeft) {
            // 菜单左侧会超出编辑器，调整到编辑器左边界
            centerX = editorLeft + halfMenuWidth + 10;
          } else if (centerX + halfMenuWidth > editorRight) {
            // 菜单右侧会超出编辑器，调整到编辑器右边界
            centerX = editorRight - halfMenuWidth - 10;
          }

          // 检查上下空间（相对于编辑器容器）
          const spaceAbove = coordsStart.top - editorRect.top;
          const spaceBelow = editorRect.bottom - coordsEnd.bottom;

          // 智能选择菜单位置：优先在上方，空间不足时放在下方
          const showAbove = spaceAbove >= menuHeight + 10;
          let positionY = showAbove
            ? coordsStart.top - menuHeight - 10 // 上方显示
            : coordsEnd.bottom + 10; // 下方显示

          // 确保菜单不超出编辑器的上下边界
          if (positionY < editorRect.top) {
            positionY = editorRect.top + 10;
          } else if (positionY + menuHeight > editorRect.bottom) {
            positionY = editorRect.bottom - menuHeight - 10;
          }

          setSelectionMenu({
            isVisible: true,
            position: {
              x: centerX,
              y: positionY,
            },
            selectedText: selectedText.trim(),
          });
        }
      } else {
        // 没有选中文本，隐藏菜单
        setSelectionMenu((prev) => ({ ...prev, isVisible: false }));
      }
    },
    editorProps: {
      attributes: {
        class: `prose prose-sm max-w-none focus:outline-none min-h-full ${className}`,
      },
      handlePaste: (view, event, slice) => {
        const { clipboardData } = event;

        if (clipboardData && clipboardData.files.length > 0) {
          event.preventDefault();

          Array.from(clipboardData.files).forEach((file) => {
            if (file.type.startsWith("image/")) {
              handleImageFile(file);
            }
          });

          return true;
        }

        return false;
      },
      handleDrop: (view, event, slice, moved) => {
        const { dataTransfer } = event;

        if (dataTransfer && dataTransfer.files.length > 0) {
          event.preventDefault();

          Array.from(dataTransfer.files).forEach((file) => {
            if (file.type.startsWith("image/")) {
              handleImageFile(file);
            }
          });

          return true;
        }

        return false;
      },
      handleKeyDown: (view, event) => {
        // 检测空格键，且编辑器为空时触发AI写作助手
        if (event.key === " " && view.state.doc.textContent.trim() === "") {
          event.preventDefault();
          handleShowAIQuery();
          return true;
        }
        return false;
      },
    },
  });

  // 处理图片文件的函数
  const handleImageFile = useCallback(
    (file: File) => {
      if (!editor) return;

      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        // 直接插入图片，不显示任何提示
        editor.chain().focus().setImage({ src: base64 }).run();
      };

      reader.onerror = () => {
        console.error("图片读取失败");
      };

      reader.readAsDataURL(file);
    },
    [editor]
  );

  const addImage = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result as string;
          editor?.chain().focus().setImage({ src: base64 }).run();
        };
        reader.readAsDataURL(file);
      }
    };
    input.click();
  }, [editor]);

  const addImageFromUrl = useCallback(() => {
    const url = window.prompt("图片URL");
    if (url) {
      editor?.chain().focus().setImage({ src: url }).run();
    }
  }, [editor]);

  const insertTimestamp = useCallback(() => {
    if (editor) {
      editor
        .chain()
        .focus()
        .insertContent({
          type: "timestamp",
          attrs: { timestamp: currentVideoTime },
        })
        .run();
    }
  }, [editor, currentVideoTime]);

  const handleInsertAIResponse = useCallback(
    (response: string) => {
      if (editor) {
        // 逐步插入内容，正确处理段落和格式
        const insertFormattedContent = () => {
          // 首先插入标题
          editor.chain().focus().insertContent("<p></p>").run();
          editor.chain().focus().insertContent("<p><strong>AI 写作：</strong></p>").run();

          // 处理回答内容，按段落分割
          const paragraphs = response.split(/\n\s*\n/).filter((p) => p.trim());

          paragraphs.forEach((paragraph) => {
            const processedParagraph = paragraph
              .trim()
              .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // **粗体**
              .replace(/\*(.*?)\*/g, "<em>$1</em>") // *斜体*
              .replace(/`(.*?)`/g, "<code>$1</code>") // `代码`
              .replace(/\n/g, "<br>"); // 单独的换行转为 br

            editor.chain().focus().insertContent(`<p>${processedParagraph}</p>`).run();
          });

          // 最后添加空段落作为间隔
          editor.chain().focus().insertContent("<p></p>").run();
        };

        insertFormattedContent();
      }
      setShowAIQuery(false);
    },
    [editor]
  );

  const handleFeynmanNotes = useCallback(async () => {
    if (!editor) return;

    try {
      // 在编辑器最下方插入费曼笔记标题
      editor.chain().focus().setTextSelection(editor.state.doc.content.size).run();
      editor.chain().focus().insertContent("<p></p>").run();
      editor.chain().focus().insertContent("<h2>🎓 费曼笔记法</h2>").run();
      editor
        .chain()
        .focus()
        .insertContent("<p><em>基于视频内容生成的学习框架，请尝试用自己的话解释每个概念：</em></p>")
        .run();

      // 显示加载状态
      editor.chain().focus().insertContent("<p><strong>AI 正在生成学习框架...</strong></p>").run();

      // 调用AI服务生成费曼笔记框架
      const { currentVideo, currentVideoTime } = useAppStore.getState();
      const response = await aiService.generateFeynmanFramework({
        videoTitle: currentVideo.title,
        videoDescription: currentVideo.description,
        currentTime: currentVideoTime,
        existingNotes: editor.getHTML(),
      });

      if (response.error) {
        throw new Error(response.error);
      }

      // 移除加载状态
      const docSize = editor.state.doc.content.size;
      editor.chain().focus().setTextSelection(docSize).deleteSelection().run();

      // 插入生成的框架内容
      const frameworkContent = response.framework;
      const lines = frameworkContent.split("\n");

      lines.forEach((line: string) => {
        const trimmedLine = line.trim();

        if (!trimmedLine) {
          // 空行，插入段落间隔
          editor.chain().focus().insertContent("<p></p>").run();
          return;
        }

        // 处理标题
        if (trimmedLine.startsWith("### ")) {
          const title = trimmedLine.replace(/^### /, "");
          const processedTitle = title
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`(.*?)`/g, "<code>$1</code>");
          editor.chain().focus().insertContent(`<h3>${processedTitle}</h3>`).run();
          return;
        }

        if (trimmedLine.startsWith("## ")) {
          const title = trimmedLine.replace(/^## /, "");
          const processedTitle = title
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`(.*?)`/g, "<code>$1</code>");
          editor.chain().focus().insertContent(`<h2>${processedTitle}</h2>`).run();
          return;
        }

        // 处理水平分割线
        if (trimmedLine === "---") {
          editor.chain().focus().insertContent("<hr>").run();
          return;
        }

        // 处理列表项
        if (trimmedLine.startsWith("- ")) {
          const listContent = trimmedLine.replace(/^- /, "");
          const processedContent = listContent
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`(.*?)`/g, "<code>$1</code>");
          // 使用简单的HTML，让Tiptap正确处理
          editor.chain().focus().insertContent(`<p>• ${processedContent}</p>`).run();
          return;
        }

        // 处理普通段落
        const processedLine = trimmedLine
          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
          .replace(/\*(.*?)\*/g, "<em>$1</em>")
          .replace(/`(.*?)`/g, "<code>$1</code>");
        editor.chain().focus().insertContent(`<p>${processedLine}</p>`).run();
      });

      // 添加检查提示
      editor.chain().focus().insertContent("<p></p>").run();
      editor
        .chain()
        .focus()
        .insertContent("<p><em>💡 完成记录后，可以使用AI写作助手检查你的理解是否正确</em></p>")
        .run();
      editor.chain().focus().insertContent("<p></p>").run();
    } catch (error) {
      console.error("生成费曼笔记失败:", error);

      // 移除加载状态并显示错误
      const docSize = editor.state.doc.content.size;
      editor.chain().focus().setTextSelection(docSize).deleteSelection().run();

      editor
        .chain()
        .focus()
        .insertContent("<p><strong>生成费曼笔记框架失败，请稍后重试</strong></p>")
        .run();
    }
  }, [editor]);

  // 处理选择菜单的操作
  const handleSelectionAskAI = useCallback((selectedText: string) => {
    // 将选中的文本作为上下文自动添加到AI查询中
    setShowAIQuery(true);

    // 使用全局事件来传递选中文本作为上下文
    const event = new CustomEvent("add-selection-context", {
      detail: { selectedText },
    });
    window.dispatchEvent(event);
  }, []);

  const handleSelectionMenuClose = useCallback(() => {
    setSelectionMenu((prev) => ({ ...prev, isVisible: false }));
  }, []);

  // 监听斜杠命令触发的费曼笔记事件
  useEffect(() => {
    const handleFeynmanEvent = () => {
      handleFeynmanNotes();
    };

    window.addEventListener("feynman-notes-trigger", handleFeynmanEvent);
    return () => {
      window.removeEventListener("feynman-notes-trigger", handleFeynmanEvent);
    };
  }, [handleFeynmanNotes]);

  if (!editor) {
    return null;
  }

  return (
    <div className="h-full flex flex-col border-0 max-h-full overflow-hidden">
      {/* 工具栏 */}
      <div className="flex-shrink-0 border-b border-border p-2 bg-background/50">
        <div className="flex gap-1">
          {/* 基础格式 */}
          <Button
            variant={editor.isActive("codeBlock") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            title="代码块"
          >
            <Code2 className="h-4 w-4" />
          </Button>

          {/* 分割线 */}
          <div className="w-px h-6 bg-border mx-2" />

          {/* 媒体 */}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={addImage}
            title="插入图片"
          >
            <ImageIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={insertTimestamp}
            title="插入当前时间戳"
          >
            <Clock className="h-4 w-4" />
          </Button>

          {/* 分割线 */}
          <div className="w-px h-6 bg-border mx-2" />

          {/* AI 功能 */}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={handleShowAIQuery}
            title="AI 写作"
          >
            <Bot className="h-4 w-4" />
          </Button>

          {/* 费曼笔记 */}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={handleFeynmanNotes}
            title="费曼笔记法"
          >
            <GraduationCap className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 编辑器内容区域 */}
      <div className="flex-1 min-h-0 overflow-hidden relative">
        <EditorContent
          editor={editor}
          className="h-full focus-within:outline-none tiptap-content"
        />
      </div>

      <style jsx global>{`
        .tiptap-content {
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .tiptap-content .ProseMirror {
          flex: 1;
          min-height: 0;
          padding: 1rem;
          font-size: 14px;
          line-height: 1.6;
          color: hsl(var(--foreground));
          background: transparent;
          border: none;
          outline: none;
          word-wrap: break-word;
          overflow-wrap: break-word;
          overflow-y: auto;
          max-height: 100%;
        }

        /* 自定义滚动条样式 */
        .tiptap-content .ProseMirror::-webkit-scrollbar {
          width: 6px;
        }

        .tiptap-content .ProseMirror::-webkit-scrollbar-track {
          background: transparent;
        }

        .tiptap-content .ProseMirror::-webkit-scrollbar-thumb {
          background-color: hsl(var(--border));
          border-radius: 3px;
        }

        .tiptap-content .ProseMirror::-webkit-scrollbar-thumb:hover {
          background-color: hsl(var(--muted-foreground));
        }

        .tiptap-content .ProseMirror p {
          margin: 0.5rem 0;
          line-height: 1.6;
        }

        .tiptap-content .ProseMirror p:first-child {
          margin-top: 0;
        }

        .tiptap-content .ProseMirror p:last-child {
          margin-bottom: 0;
        }

        .tiptap-content .ProseMirror h1,
        .tiptap-content .ProseMirror h2,
        .tiptap-content .ProseMirror h3 {
          font-weight: 600;
          margin: 1.5rem 0 0.75rem 0;
          line-height: 1.4;
        }

        .tiptap-content .ProseMirror h1:first-child,
        .tiptap-content .ProseMirror h2:first-child,
        .tiptap-content .ProseMirror h3:first-child {
          margin-top: 0;
        }

        .tiptap-content .ProseMirror h1 {
          font-size: 1.5rem;
          border-bottom: 1px solid hsl(var(--border));
          padding-bottom: 0.5rem;
        }

        .tiptap-content .ProseMirror h2 {
          font-size: 1.25rem;
        }

        .tiptap-content .ProseMirror h3 {
          font-size: 1.125rem;
        }

        .tiptap-content .ProseMirror ul {
          margin: 0.75rem 0;
          padding-left: 1.5rem;
          list-style-type: disc;
        }

        .tiptap-content .ProseMirror ol {
          margin: 0.75rem 0;
          padding-left: 1.5rem;
          list-style-type: decimal;
        }

        .tiptap-content .ProseMirror li {
          margin: 0.25rem 0;
          line-height: 1.6;
          list-style-position: outside;
        }

        .tiptap-content .ProseMirror ul li {
          list-style-type: disc;
        }

        .tiptap-content .ProseMirror ol li {
          list-style-type: decimal;
        }

        .tiptap-content .ProseMirror code {
          background: #f6f8fa;
          color: #d73a49;
          padding: 0.15rem 0.4rem;
          border-radius: 0.25rem;
          font-size: 0.875rem;
          font-weight: 500;
          border: 1px solid #e1e4e8;
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo,
            monospace;
        }

        .tiptap-content .ProseMirror .code-block-custom {
          background: #f6f8fa;
          border: 1px solid #e1e4e8;
          border-radius: 0.5rem;
          margin: 1.25rem 0;
          overflow: hidden;
          position: relative;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
          transition: all 0.2s ease;
        }

        .tiptap-content .ProseMirror .code-block-custom:hover {
          border-color: #c6cbd1;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        }

        .tiptap-content .code-block-custom pre,
        .tiptap-content [data-type="codeBlock"] pre {
          background: #f6f8fa !important;
          padding: 1.25rem 1.5rem !important;
          margin: 0 !important;
          border-radius: 0 !important;
          border: none !important;
          overflow-x: auto;
          font-size: 0.875rem;
          line-height: 1.6;
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo,
            monospace !important;
          color: #24292e !important;
          white-space: pre !important;
          word-wrap: normal !important;
          box-sizing: border-box !important;
        }

        .tiptap-content .ProseMirror .code-block-custom code {
          background: transparent !important;
          padding: 0 !important;
          border-radius: 0 !important;
          border: none !important;
          font-size: inherit !important;
          color: inherit !important;
          font-family: inherit !important;
          line-height: inherit !important;
          display: block;
          margin: 0;
          min-height: 1.6em;
        }

        /* 确保代码块内容有正确的间距 */
        .tiptap-content .ProseMirror .code-block-custom {
          padding: 0 !important;
        }

        .tiptap-content .ProseMirror .code-block-custom * {
          box-sizing: border-box;
        }

        /* 移除代码行的边框和间距 */
        .tiptap-content .ProseMirror .code-block-custom .hljs {
          display: block;
          overflow-x: auto;
          padding: 0 !important;
          margin: 0 !important;
          border: none !important;
          background: transparent !important;
        }

        /* 确保代码块内容不会贴边 */
        .tiptap-content .ProseMirror .code-block-custom > * {
          padding-left: 0 !important;
          padding-right: 0 !important;
        }

        /* 代码行样式 */
        .tiptap-content .ProseMirror .code-block-custom .hljs-ln {
          border: none !important;
          margin: 0;
          padding: 0;
        }

        .tiptap-content .ProseMirror .code-block-custom .hljs-ln-line {
          border: none !important;
          margin: 0;
          padding: 0;
          display: block;
        }

        /* 代码块内的段落和换行 */
        .tiptap-content .ProseMirror .code-block-custom p {
          margin: 0 !important;
          padding: 0 !important;
          border: none !important;
          text-indent: 0 !important;
        }

        .tiptap-content .ProseMirror .code-block-custom br {
          line-height: 1.6;
        }

        /* 强制确保代码块内容有间距 - 多重选择器 */
        .tiptap-content pre,
        .tiptap-content .ProseMirror pre,
        .tiptap-content pre[class*="language-"],
        .tiptap-content .code-block-custom pre,
        .tiptap-content [data-type="codeBlock"] pre {
          padding: 1.25rem 1.5rem !important;
          margin: 0 !important;
          background: #f6f8fa !important;
          border-radius: 0 !important;
          border: none !important;
        }

        /* 为代码块添加内容区域样式 */
        .tiptap-content .ProseMirror [data-type="codeBlock"] {
          padding: 0 !important;
        }

        .tiptap-content .ProseMirror [data-type="codeBlock"] pre {
          padding: 1.25rem 1.5rem !important;
          background: #f6f8fa !important;
          border-radius: 0 !important;
          margin: 0 !important;
        }

        /* 最终的强制样式 - 确保代码块有 padding */
        .tiptap-content pre {
          padding: 1.25rem 1.5rem !important;
        }

        .tiptap-content .ProseMirror-widget pre {
          padding: 1.25rem 1.5rem !important;
        }

        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
          .tiptap-content .ProseMirror .code-block-custom {
            background: #f8fafc;
            border-color: #e2e8f0;
          }

          .tiptap-content .ProseMirror .code-block-custom pre {
            background: #f8fafc !important;
            color: #334155;
            padding: 1.25rem 1.5rem !important;
            line-height: 1.6;
            box-sizing: border-box;
          }
        }

        /* 确保语法高亮样式正确应用 */
        .tiptap-content .hljs {
          background: transparent !important;
          padding: 0 !important;
          border: none !important;
          margin: 0 !important;
        }

        .tiptap-content .hljs-keyword {
          color: #d73a49;
          font-weight: 600;
        }

        .tiptap-content .hljs-string {
          color: #0366d6;
        }

        .tiptap-content .hljs-comment {
          color: #6a737d;
          font-style: italic;
        }

        .tiptap-content .hljs-number {
          color: #005cc5;
        }

        .tiptap-content .hljs-function {
          color: #6f42c1;
        }

        .tiptap-content .hljs-variable {
          color: #e36209;
        }

        .tiptap-content .hljs-type {
          color: #6f42c1;
        }

        .tiptap-content .ProseMirror blockquote {
          border-left: 3px solid hsl(var(--border));
          padding-left: 1rem;
          margin: 1rem 0;
          color: hsl(var(--muted-foreground));
          font-style: italic;
        }

        .tiptap-content .ProseMirror a {
          color: hsl(var(--primary));
          text-decoration: underline;
          text-decoration-thickness: 1px;
          text-underline-offset: 2px;
          transition: all 0.2s;
        }

        .tiptap-content .ProseMirror a:hover {
          text-decoration-thickness: 2px;
        }

        .tiptap-content .ProseMirror img {
          max-width: 100%;
          height: auto;
          border-radius: 0.5rem;
          margin: 1rem 0;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          border: 1px solid hsl(var(--border));
          cursor: pointer;
          transition: transform 0.2s ease;
        }

        .tiptap-content .ProseMirror img:hover {
          transform: scale(1.02);
        }

        .tiptap-content .ProseMirror img[src^="data:"] {
          /* 特殊样式用于截图图片 */
          border: 2px solid hsl(var(--primary));
        }

        .tiptap-content .ProseMirror p.is-editor-empty:first-child::before {
          content: attr(data-placeholder);
          float: left;
          color: #9ca3af;
          pointer-events: none;
          height: 0;
          opacity: 0.6;
        }

        .tiptap-content .ProseMirror:focus p.is-editor-empty:first-child::before {
          opacity: 0.8;
        }

        .tiptap-content .ProseMirror:focus {
          outline: none;
        }

        .tiptap-content .ProseMirror strong {
          font-weight: 600;
        }

        .tiptap-content .ProseMirror em {
          font-style: italic;
        }
      `}</style>

      {/* AI 写作面板 */}
      {showAIQuery && (
        <div className="mt-4 relative">
          <AIQueryPanel
            onClose={handleCloseAIQuery}
            onInsertResponse={handleInsertAIResponse}
            currentVideoTime={currentVideoTime}
          />
        </div>
      )}

      {/* 选择文本浮动菜单 */}
      <SelectionMenu
        isVisible={selectionMenu.isVisible}
        position={selectionMenu.position}
        selectedText={selectionMenu.selectedText}
        onAskAI={handleSelectionAskAI}
        onClose={handleSelectionMenuClose}
      />
    </div>
  );
}
