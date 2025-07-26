"use client";

import React, { useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Bot, Copy, Trash2 } from "lucide-react";

interface SelectionMenuProps {
  isVisible: boolean;
  position: { x: number; y: number };
  selectedText: string;
  onAskAI: (selectedText: string) => void;
  onCopy: () => void;
  onDelete: () => void;
  onClose: () => void;
}

export function SelectionMenu({
  isVisible,
  position,
  selectedText,
  onAskAI,
  onCopy,
  onDelete,
  onClose,
}: SelectionMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (isVisible) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isVisible, onClose]);

  if (!isVisible) return null;

  return (
    <div
      ref={menuRef}
      className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-xl py-1 min-w-[160px] max-w-[200px] backdrop-blur-sm"
      style={{
        left: position.x,
        top: position.y,
        transform: "translateX(-50%)",
        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      }}
    >
      {/* Ask AI 按钮 */}
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start h-8 px-3 text-sm hover:bg-gray-100"
        onClick={() => {
          onAskAI(selectedText);
          onClose();
        }}
      >
        <Bot className="w-4 h-4 mr-2" />
        Ask AI
      </Button>

      {/* 复制按钮 */}
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start h-8 px-3 text-sm hover:bg-gray-100"
        onClick={() => {
          onCopy();
          onClose();
        }}
      >
        <Copy className="w-4 h-4 mr-2" />
        复制
      </Button>

      {/* 删除按钮 */}
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start h-8 px-3 text-sm hover:bg-gray-100 text-red-600 hover:text-red-700 hover:bg-red-50"
        onClick={() => {
          onDelete();
          onClose();
        }}
      >
        <Trash2 className="w-4 h-4 mr-2" />
        删除
      </Button>
    </div>
  );
}
