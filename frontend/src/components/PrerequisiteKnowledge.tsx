"use client";

import { Card } from "@/components/ui/card";
import { motion, AnimatePresence } from "framer-motion";
import { useAppStore } from "@/store";
import { ChevronDown, ChevronRight, Clock, Play } from "lucide-react";
import type { KnowledgePoint } from "@/types";

function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function KnowledgePointItem({ point }: { point: KnowledgePoint }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -10 }}
      className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors cursor-pointer group"
    >
      <div className="flex-shrink-0 mt-1">
        <Play className="w-4 h-4 text-primary opacity-60 group-hover:opacity-100 transition-opacity" />
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-sm mb-1 group-hover:text-primary transition-colors">
          {point.title}
        </h4>
        <p className="text-xs text-muted-foreground mb-2 line-clamp-2">{point.description}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>{formatTime(point.timestamp)}</span>
          {point.duration && (
            <>
              <span>•</span>
              <span>{point.duration}秒</span>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export function PrerequisiteKnowledge() {
  const { currentVideo, togglePrerequisiteModule } = useAppStore();

  if (!currentVideo.prerequisites || currentVideo.prerequisites.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.6 }}
      className="mt-6 space-y-4"
    >
      <h3 className="text-lg font-semibold mb-4">前置知识模块</h3>

      <div className="space-y-3">
        {currentVideo.prerequisites.map((module) => (
          <Card key={module.id} className="overflow-hidden">
            <div
              className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => togglePrerequisiteModule(module.id)}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">
                  {module.isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-base mb-1">{module.title}</h4>
                  <p className="text-sm text-muted-foreground">{module.description}</p>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {module.knowledgePoints.length} 个知识点
                  </div>
                </div>
              </div>
            </div>

            <AnimatePresence>
              {module.isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="border-t"
                >
                  <div className="p-4 space-y-3">
                    {module.knowledgePoints.map((point) => (
                      <KnowledgePointItem key={point.id} point={point} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
        ))}
      </div>
    </motion.div>
  );
}
