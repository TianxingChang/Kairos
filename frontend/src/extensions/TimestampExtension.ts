import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import TimestampNodeView from './TimestampNodeView';

export interface TimestampOptions {
  HTMLAttributes: Record<string, unknown>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    timestamp: {
      insertTimestamp: (timestamp: number) => ReturnType;
    };
  }
}

export const TimestampExtension = Node.create<TimestampOptions>({
  name: 'timestamp',

  group: 'inline',

  inline: true,

  atom: true,

  addAttributes() {
    return {
      timestamp: {
        default: 0,
        parseHTML: element => parseInt(element.getAttribute('data-timestamp') || '0'),
        renderHTML: attributes => ({
          'data-timestamp': attributes.timestamp,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-timestamp]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes)];
  },

  addNodeView() {
    return ReactNodeViewRenderer(TimestampNodeView);
  },

  addCommands() {
    return {
      insertTimestamp:
        (timestamp: number) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: { timestamp },
          });
        },
    };
  },
});