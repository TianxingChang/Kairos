"use client";

import { NodeViewWrapper } from '@tiptap/react';
import { TimestampBadge } from '@/components/TimestampBadge';

const TimestampNodeView = ({ node }: { node: { attrs: { timestamp: number } } }) => {
  const timestamp = node.attrs.timestamp || 0;

  return (
    <NodeViewWrapper className="inline">
      <TimestampBadge timestamp={timestamp} />
    </NodeViewWrapper>
  );
};

export default TimestampNodeView;