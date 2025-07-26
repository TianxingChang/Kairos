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
import {
  Bold,
  Italic,
  Strikethrough,
  Code,
  Code2,
  Quote,
  List,
  ListOrdered,
  Heading1,
  Heading2,
  Heading3,
  Link as LinkIcon,
  Image as ImageIcon,
  Camera,
  Undo,
  Redo,
  Clock,
} from "lucide-react";
import { useCallback } from "react";
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
  placeholder = "开始记录你的笔记...",
  className = "",
  onScreenshot,
}: TiptapEditorProps) {
  const { currentVideoTime } = useAppStore();
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
      SlashCommand(onScreenshot, currentVideoTime),
    ],
    content,
    immediatelyRender: false, // 修复SSR水合问题
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
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

  const addLink = useCallback(() => {
    const previousUrl = editor?.getAttributes("link").href;
    const url = window.prompt("URL", previousUrl);

    if (url === null) {
      return;
    }

    if (url === "") {
      editor?.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }

    editor?.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
  }, [editor]);

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

  const takeScreenshot = useCallback(async () => {
    if (!onScreenshot) {
      console.error("截图功能暂不可用，请检查视频播放器状态");
      return;
    }

    try {
      const base64Image = await onScreenshot();
      // 直接插入截图，不显示任何提示
      editor?.chain().focus().setImage({ src: base64Image }).run();
    } catch (error) {
      console.error("截图失败:", error);
    }
  }, [editor, onScreenshot]);

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

  if (!editor) {
    return null;
  }

  return (
    <div className="h-full flex flex-col border-0">
      {/* 工具栏 */}
      <div className="flex-shrink-0 border-b border-border p-2 bg-background/50">
        <div className="flex gap-1">
          {/* 基础格式 */}
          <Button
            variant={editor.isActive("bold") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleBold().run()}
          >
            <Bold className="h-4 w-4" />
          </Button>
          <Button
            variant={editor.isActive("italic") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleItalic().run()}
          >
            <Italic className="h-4 w-4" />
          </Button>
          <Button
            variant={editor.isActive("code") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleCode().run()}
          >
            <Code className="h-4 w-4" />
          </Button>
          <Button
            variant={editor.isActive("codeBlock") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          >
            <Code2 className="h-4 w-4" />
          </Button>

          {/* 分割线 */}
          <div className="w-px h-6 bg-border mx-2" />

          {/* 列表 */}
          <Button
            variant={editor.isActive("bulletList") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleBulletList().run()}
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={editor.isActive("orderedList") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
          >
            <ListOrdered className="h-4 w-4" />
          </Button>

          {/* 分割线 */}
          <div className="w-px h-6 bg-border mx-2" />

          {/* 链接和媒体 */}
          <Button
            variant={editor.isActive("link") ? "default" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={addLink}
            title="插入链接"
          >
            <LinkIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={addImage}
            title="插入图片"
          >
            <ImageIcon className="h-4 w-4" />
          </Button>
          {onScreenshot && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={takeScreenshot}
              title="截取视频画面"
            >
              <Camera className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={insertTimestamp}
            title="插入当前时间戳"
          >
            <Clock className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 编辑器内容区域 */}
      <div className="flex-1 overflow-y-auto">
        <EditorContent
          editor={editor}
          className="h-full focus-within:outline-none tiptap-content"
        />
      </div>

      <style jsx global>{`
        .tiptap-content .ProseMirror {
          min-height: 100%;
          padding: 1rem;
          font-size: 14px;
          line-height: 1.6;
          color: hsl(var(--foreground));
          background: transparent;
          border: none;
          outline: none;
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
    </div>
  );
}
