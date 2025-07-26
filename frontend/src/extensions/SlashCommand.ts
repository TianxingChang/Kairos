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
export const createSlashCommands = (editor: any, onScreenshot?: () => Promise<string>, currentVideoTime?: number): SlashCommandItem[] => {
  const commands: SlashCommandItem[] = [
    {
      title: '标题 1',
      description: '大号标题',
      icon: '📝',
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
      title: '标题 2',
      description: '中号标题',
      icon: '📄',
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
      title: '标题 3',
      description: '小号标题',
      icon: '📃',
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
      title: '文本',
      description: '普通文本段落',
      icon: '📝',
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
      title: '无序列表',
      description: '创建一个简单的无序列表',
      icon: '•',
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
      title: '有序列表',
      description: '创建一个带编号的有序列表',
      icon: '1.',
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
      title: '引用',
      description: '创建一个引用块',
      icon: '💬',
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
      title: '代码块',
      description: '创建一个代码块',
      icon: '💻',
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
      title: '图片',
      description: '插入图片',
      icon: '🖼️',
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
  ]

  // 如果有截图功能，添加截图命令
  if (onScreenshot) {
    commands.push({
      title: '截图',
      description: '截取视频画面',
      icon: '📷',
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
      title: '时间戳',
      description: '插入当前视频时间戳',
      icon: '⏰',
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
    container.innerHTML = '<div style="padding: 6px 10px; color: #999; font-size: 12px;">没有找到匹配的命令</div>'
    return
  }
  
  items.forEach((item, index) => {
    const div = document.createElement('div')
    div.style.cssText = `
      padding: 6px 10px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      border-bottom: 1px solid #eee;
      font-size: 13px;
    `
    div.innerHTML = `
      <span style="font-size: 14px; width: 16px; text-align: center;">${item.icon}</span>
      <div>
        <div style="font-weight: 500; font-size: 13px;">${item.title}</div>
        <div style="font-size: 11px; color: #666; margin-top: 1px;">${item.description}</div>
      </div>
    `
    
    div.addEventListener('click', () => {
      command(item)
    })
    
    div.addEventListener('mouseenter', () => {
      div.style.backgroundColor = '#f5f5f5'
    })
    
    div.addEventListener('mouseleave', () => {
      div.style.backgroundColor = 'transparent'
    })
    
    container.appendChild(div)
  })
}

export const SlashCommand = (onScreenshot?: () => Promise<string>, currentVideoTime?: number) =>
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
            const commands = createSlashCommands(this.editor, onScreenshot, currentVideoTime)
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
                  background: white;
                  border: 1px solid #ccc;
                  border-radius: 6px;
                  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                  max-height: 240px;
                  overflow-y: auto;
                  width: 240px;
                  font-size: 13px;
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