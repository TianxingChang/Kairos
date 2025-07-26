import { Extension } from '@tiptap/core'
import { ReactRenderer } from '@tiptap/react'
import Suggestion from '@tiptap/suggestion'

export interface SlashCommandItem {
  title: string
  description: string
  icon: React.ReactNode
  command: (props: any) => void
}

// 创建命令列表
export const createSlashCommands = (editor: any, onScreenshot?: () => Promise<string>, currentVideoTime?: number, onShowAIQuery?: () => void): SlashCommandItem[] => {
  const commands: SlashCommandItem[] = [
    {
      title: 'Heading 1',
      description: '大号标题',
      icon: 'H1',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setNode('heading', { level: 1 })
          .run()
      },
    },
    {
      title: 'Heading 2',
      description: '中号标题',
      icon: 'H2',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setNode('heading', { level: 2 })
          .run()
      },
    },
    {
      title: 'Heading 3',
      description: '小号标题',
      icon: 'H3',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setNode('heading', { level: 3 })
          .run()
      },
    },
    {
      title: 'Text',
      description: '普通文本段落',
      icon: 'T',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setNode('paragraph')
          .run()
      },
    },
    {
      title: 'Bullet List',
      description: '创建一个简单的无序列表',
      icon: '●',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleBulletList()
          .run()
      },
    },
    {
      title: 'Numbered List',
      description: '创建一个带编号的有序列表',
      icon: '№',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleOrderedList()
          .run()
      },
    },
    {
      title: 'Quote',
      description: '创建一个引用块',
      icon: '"',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleBlockquote()
          .run()
      },
    },
    {
      title: 'Code',
      description: '创建一个代码块',
      icon: '{ }',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleCodeBlock()
          .run()
      },
    },
    {
      title: 'Image',
      description: '插入图片',
      icon: '🖼',
      command: ({ editor, range }: any) => {
        editor.chain().focus().deleteRange(range).run()
        
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = 'image/*'
        input.onchange = (e) => {
          const file = (e.target as HTMLInputElement).files?.[0]
          if (file) {
            const reader = new FileReader()
            reader.onload = () => {
              const base64 = reader.result as string
              editor.chain().focus().setImage({ src: base64 }).run()
            }
            reader.readAsDataURL(file)
          }
        }
        input.click()
      },
    },
    {
      title: 'AI 写作',
      description: 'AI 帮你写作',
      icon: 'AI',
      command: ({ editor, range }: any) => {
        editor.chain().focus().deleteRange(range).run()
        if (onShowAIQuery) {
          onShowAIQuery()
        }
      },
    },
    {
      title: '费曼笔记',
      description: '生成学习框架',
      icon: '🎓',
      command: ({ editor, range }: any) => {
        editor.chain().focus().deleteRange(range).run()
        // 通过全局事件触发费曼笔记功能
        const event = new CustomEvent('feynman-notes-trigger')
        window.dispatchEvent(event)
      },
    },
  ]

  // 如果有截图功能，添加截图命令
  if (onScreenshot) {
    commands.push({
      title: 'Screenshot',
      description: '截取视频画面',
      icon: '📸',
      command: async ({ editor, range }: any) => {
        editor.chain().focus().deleteRange(range).run()
        try {
          const base64Image = await onScreenshot()
          editor.chain().focus().setImage({ src: base64Image }).run()
        } catch (error) {
          console.error('截图失败:', error)
        }
      },
    })
  }

  // 如果有视频时间，添加时间戳命令
  if (currentVideoTime !== undefined) {
    commands.push({
      title: 'Timestamp',
      description: '插入当前视频时间戳',
      icon: '⏱',
      command: ({ editor, range }: any) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .insertContent({
            type: 'timestamp',
            attrs: { timestamp: currentVideoTime },
          })
          .run()
      },
    })
  }

  return commands
}

// 渲染命令的辅助函数
const renderCommands = (container: HTMLElement, items: SlashCommandItem[], command: (item: SlashCommandItem) => void) => {
  container.innerHTML = ''
  
  if (items.length === 0) {
    container.innerHTML = '<div style="padding: 12px; color: #9ca3af; font-size: 13px; text-align: center; font-style: italic;">没有找到匹配的命令</div>'
    return
  }
  
  items.forEach((item, index) => {
    const div = document.createElement('div')
    div.style.cssText = `
      padding: 8px 12px;
      margin: 2px 0;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 10px;
      border-radius: 6px;
      font-size: 13px;
      transition: all 0.15s ease;
      color: #374151;
    `
    div.innerHTML = `
      <span style="
        font-size: 12px; 
        width: 24px; 
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f3f4f6;
        border-radius: 4px;
        font-weight: 500;
        color: #6b7280;
      ">${item.icon}</span>
      <div style="
        font-weight: 500; 
        font-size: 13px;
        color: #374151;
        letter-spacing: -0.01em;
      ">${item.title}</div>
    `
    
    div.addEventListener('click', () => {
      command(item)
    })
    
    div.addEventListener('mouseenter', () => {
      div.style.backgroundColor = '#f8fafc'
      div.style.borderColor = '#e2e8f0'
      const iconSpan = div.querySelector('span') as HTMLElement
      if (iconSpan) {
        iconSpan.style.backgroundColor = '#e2e8f0'
        iconSpan.style.color = '#475569'
      }
    })
    
    div.addEventListener('mouseleave', () => {
      div.style.backgroundColor = 'transparent'
      div.style.borderColor = 'transparent'
      const iconSpan = div.querySelector('span') as HTMLElement
      if (iconSpan) {
        iconSpan.style.backgroundColor = '#f3f4f6'
        iconSpan.style.color = '#6b7280'
      }
    })
    
    container.appendChild(div)
  })
}

export const SlashCommand = (onScreenshot?: () => Promise<string>, currentVideoTime?: number, onShowAIQuery?: () => void) =>
  Extension.create({
    name: 'slashCommand',

    addProseMirrorPlugins() {
      return [
        Suggestion({
          editor: this.editor,
          char: '/',
          allowSpaces: false,
          startOfLine: false,
          command: ({ editor, range, props }) => {
            props.command({ editor, range })
          },
          items: ({ query }) => {
            const commands = createSlashCommands(this.editor, onScreenshot, currentVideoTime, onShowAIQuery)
            return commands.filter((item: SlashCommandItem) =>
              item.title.toLowerCase().includes(query.toLowerCase()) ||
              item.description.toLowerCase().includes(query.toLowerCase())
            )
          },
          render: () => {
            let component: ReactRenderer | null = null
            let popup: HTMLElement | null = null

            return {
              onStart: (props) => {
                // 直接在编辑器下方显示简单的下拉菜单，不使用 tippy.js
                popup = document.createElement('div')
                popup.className = 'slash-commands-popup'
                popup.style.cssText = `
                  position: absolute;
                  z-index: 1000;
                  background: #ffffff;
                  border: 1px solid #e1e5e9;
                  border-radius: 8px;
                  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.05);
                  max-height: 280px;
                  overflow-y: auto;
                  width: 260px;
                  font-size: 13px;
                  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                  padding: 4px;
                `
                
                if (props.clientRect) {
                  const rect = props.clientRect()
                  if (rect) {
                    popup.style.top = `${rect.bottom + 5}px`
                    popup.style.left = `${rect.left}px`
                  }
                }
                
                document.body.appendChild(popup)
                
                // 渲染命令列表
                renderCommands(popup, props.items, props.command)
              },

              onUpdate: (props) => {
                if (popup && props.clientRect) {
                  const rect = props.clientRect()
                  if (rect) {
                    popup.style.top = `${rect.bottom + 5}px`
                    popup.style.left = `${rect.left}px`
                  }
                }
                
                if (popup) {
                  renderCommands(popup, props.items, props.command)
                }
              },

              onKeyDown: (props) => {
                if (props.event.key === 'Escape') {
                  return true
                }
                return false
              },

              onExit: () => {
                if (popup) {
                  document.body.removeChild(popup)
                  popup = null
                }
                if (component) {
                  component.destroy()
                  component = null
                }
              },
            }
          },
        }),
      ]
    },
  })

export default SlashCommand 