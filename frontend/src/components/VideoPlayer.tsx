"use client";

import { Card } from "@/components/ui/card";
import { motion } from "framer-motion";
import { useAppStore } from "@/store";
import { PrerequisiteKnowledge } from "./PrerequisiteKnowledge";
import { VideoPlayerSimple } from "./VideoPlayerSimple";

export function VideoPlayer() {
  const { currentVideo } = useAppStore();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="h-full flex flex-col max-w-none"
    >
      {/* Video Player Container with responsive max-width */}
      <motion.div
        initial={{ y: 20 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="aspect-video w-full max-w-3xl lg:max-w-4xl xl:max-w-5xl 2xl:max-w-6xl mx-auto"
      >
        <Card className="w-full h-full rounded-xl overflow-hidden p-0 py-0 gap-0">
          <VideoPlayerSimple />
        </Card>
      </motion.div>
      {/* Video Info Section */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="mt-4 space-y-2 max-w-3xl lg:max-w-4xl xl:max-w-5xl 2xl:max-w-6xl mx-auto w-full"
      >
        <h2 className="text-xl font-semibold">{currentVideo.title}</h2>
        <p className="text-muted-foreground text-sm">{currentVideo.description}</p>
      </motion.div>

      {/* Prerequisites Section */}
      <div className="max-w-3xl lg:max-w-4xl xl:max-w-5xl 2xl:max-w-6xl mx-auto w-full">
        <PrerequisiteKnowledge />
      </div>
    </motion.div>
  );
}
