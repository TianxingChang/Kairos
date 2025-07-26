import { useEffect, useRef } from 'react';

interface UseScrollToBottomOptions {
  behavior?: ScrollBehavior;
  block?: ScrollLogicalPosition;
  dependencies?: unknown[];
  enabled?: boolean;
}

export function useScrollToBottom<T extends HTMLElement>(
  options: UseScrollToBottomOptions = {}
) {
  const {
    behavior = 'smooth',
    block = 'end',
    dependencies = [],
    enabled = true,
  } = options;

  const ref = useRef<T | null>(null);

  useEffect(() => {
    if (!enabled || !ref.current) return;

    ref.current.scrollIntoView({
      behavior,
      block,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...(dependencies || []), enabled, behavior, block]);

  return ref;
} 