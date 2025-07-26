import { useEffect, useCallback, RefObject } from 'react';

interface UseAutoResizeOptions {
  minHeight?: number;
  maxHeight?: number;
}

export function useAutoResize(
  ref: RefObject<HTMLTextAreaElement | null>,
  value: string,
  options: UseAutoResizeOptions = {}
) {
  const { minHeight = 44, maxHeight = 72 } = options;

  const adjustHeight = useCallback(() => {
    const textarea = ref.current;
    if (!textarea) return;

    // 重置高度以获取正确的scrollHeight
    textarea.style.height = 'auto';
    
    // 计算新高度
    const scrollHeight = textarea.scrollHeight;
    const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
    
    // 应用新高度
    textarea.style.height = `${newHeight}px`;
  }, [ref, minHeight, maxHeight]);

  // 当值改变时调整高度
  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  return { adjustHeight };
} 