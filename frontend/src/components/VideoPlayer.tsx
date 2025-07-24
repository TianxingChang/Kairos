"use client";

import { Card } from "@/components/ui/card";
import { motion } from "framer-motion";
import { useAppStore } from "@/store/appStore";
import { PrerequisiteKnowledge } from "./PrerequisiteKnowledge";

export function VideoPlayer() {
  const { currentVideo } = useAppStore();

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="h-full flex flex-col"
    >
      <motion.div
        initial={{ y: 20 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="aspect-video"
      >
        <Card className="w-full h-full rounded-xl overflow-hidden">
          <div className="w-full h-full relative">
            <iframe
              src={currentVideo.url}
              title="Video Player"
              className="w-full h-full border-0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </Card>
      </motion.div>
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="mt-4 space-y-2"
      >
        <h2 className="text-xl font-semibold">{currentVideo.title}</h2>
        <p className="text-muted-foreground text-sm">
          {currentVideo.description}
        </p>
      </motion.div>
      
      <PrerequisiteKnowledge />
    </motion.div>
  );
}