"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { Upload, Link, Play, FileVideo } from "lucide-react";
import { useAppStore } from "@/store";

export function VideoUpload() {
  const [uploadType, setUploadType] = useState<"url" | "file">("url");
  const [videoUrl, setVideoUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const router = useRouter();
  const { setCurrentVideo } = useAppStore();

  const validateYouTubeUrl = (url: string) => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/;
    return youtubeRegex.test(url);
  };

  const extractVideoId = (url: string) => {
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : null;
  };

  const extractYouTubeInfo = async (videoId: string) => {
    try {
      // 使用 YouTube oEmbed API 获取视频信息
      const response = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
      if (response.ok) {
        const data = await response.json();
        return {
          title: data.title || "YouTube 视频",
          description: `来自 ${data.author_name || "YouTube"} 的视频`
        };
      }
    } catch (error) {
      console.error("Failed to fetch YouTube info:", error);
    }
    return {
      title: "YouTube 视频",
      description: "YouTube 视频学习"
    };
  };

  const handleUrlSubmit = async () => {
    if (!videoUrl.trim()) return;
    
    setIsLoading(true);
    
    try {
      let finalUrl = videoUrl;
      let finalTitle = "视频学习";
      let finalDescription = "开始学习这个视频内容";
      
      // 如果是 YouTube URL，转换为标准格式并获取视频信息
      if (validateYouTubeUrl(videoUrl)) {
        const videoId = extractVideoId(videoUrl);
        if (videoId) {
          finalUrl = `https://www.youtube.com/watch?v=${videoId}`;
          // 自动获取 YouTube 视频信息
          const youtubeInfo = await extractYouTubeInfo(videoId);
          finalTitle = youtubeInfo.title;
          finalDescription = youtubeInfo.description;
        }
      } else {
        // 非 YouTube 链接，使用通用标题
        finalTitle = "在线视频学习";
        finalDescription = "学习在线视频内容";
      }

      // 更新视频信息到 store
      setCurrentVideo({
        url: finalUrl,
        title: finalTitle,
        description: finalDescription,
        prerequisites: [], // 新上传的视频暂时没有预设的先决条件
      });

      // 跳转到学习页面
      console.log("Video uploaded successfully, navigating to /learn");
      // 使用window.location确保跳转成功
      window.location.href = '/learn';
    } catch (error) {
      console.error("Failed to load video:", error);
      alert("视频加载失败，请检查链接是否正确");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSubmit = async () => {
    if (!selectedFile) return;
    
    setIsLoading(true);
    
    try {
      // 创建本地 URL
      const fileUrl = URL.createObjectURL(selectedFile);
      
      // 自动从文件名提取标题（移除扩展名）
      const fileName = selectedFile.name.replace(/\.[^/.]+$/, "");
      const fileTitle = fileName || "本地视频";
      const fileDescription = `学习本地视频文件: ${selectedFile.name}`;
      
      // 更新视频信息到 store
      setCurrentVideo({
        url: fileUrl,
        title: fileTitle,
        description: fileDescription,
        prerequisites: [], // 新上传的视频暂时没有预设的先决条件
      });

      // 跳转到学习页面
      console.log("Video uploaded successfully, navigating to /learn");
      // 使用window.location确保跳转成功
      window.location.href = '/learn';
    } catch (error) {
      console.error("Failed to load file:", error);
      alert("文件加载失败，请重试");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // 检查文件类型
      if (!file.type.startsWith('video/')) {
        alert('请选择视频文件');
        return;
      }
      
      setSelectedFile(file);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-2xl"
      >
        <Card className="p-8 shadow-xl">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-center mb-8"
          >
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Play className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">开始视频学习</h1>
            <p className="text-gray-600">上传视频或提供视频链接，开始 AI 辅助学习</p>
          </motion.div>

          {/* 上传方式选择 */}
          <div className="flex gap-4 mb-6">
            <Button
              variant={uploadType === "url" ? "default" : "outline"}
              onClick={() => setUploadType("url")}
              className="flex-1"
            >
              <Link className="w-4 h-4 mr-2" />
              视频链接
            </Button>
            <Button
              variant={uploadType === "file" ? "default" : "outline"}
              onClick={() => setUploadType("file")}
              className="flex-1"
            >
              <FileVideo className="w-4 h-4 mr-2" />
              上传文件
            </Button>
          </div>

          <motion.div
            key={uploadType}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="space-y-4"
          >
            {uploadType === "url" ? (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    视频链接 *
                  </label>
                  <Input
                    type="url"
                    placeholder="https://www.youtube.com/watch?v=... 或其他视频链接"
                    value={videoUrl}
                    onChange={(e) => setVideoUrl(e.target.value)}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    支持 YouTube、Bilibili 等主流平台链接
                  </p>
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    选择视频文件 *
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-primary transition-colors">
                    <input
                      type="file"
                      accept="video/*"
                      onChange={handleFileChange}
                      className="hidden"
                      id="video-file"
                    />
                    <label htmlFor="video-file" className="cursor-pointer">
                      <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                      <p className="text-gray-600">
                        {selectedFile ? selectedFile.name : "点击选择视频文件或拖拽到此处"}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        支持 MP4, MOV, AVI 等格式
                      </p>
                    </label>
                  </div>
                </div>
              </>
            )}


            <Button
              onClick={uploadType === "url" ? handleUrlSubmit : handleFileSubmit}
              disabled={
                isLoading ||
                (uploadType === "url" ? !videoUrl.trim() : !selectedFile)
              }
              className="w-full"
              size="lg"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  {uploadType === "url" ? "获取视频信息..." : "加载中..."}
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  开始学习
                </>
              )}
            </Button>
          </motion.div>
        </Card>
      </motion.div>
    </div>
  );
}