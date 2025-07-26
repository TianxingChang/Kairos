"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowUp,
  Sparkles,
  BookOpen,
  Search,
  Link,
  GraduationCap,
  Brain,
  Upload,
} from "lucide-react";
import { useAutoResize } from "@/hooks/useAutoResize";
import { useRouter } from "next/navigation";

interface LearningPlanForm {
  topic: string;
  level: string;
  duration: string;
  goals: string;
  schedule: string;
}

export default function Home() {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [showPlanForm, setShowPlanForm] = useState(false);
  const [showCourseSearch, setShowCourseSearch] = useState(false);
  const [planForm, setPlanForm] = useState<LearningPlanForm>({
    topic: "",
    level: "beginner",
    duration: "",
    goals: "",
    schedule: "flexible",
  });
  const [searchQuery, setSearchQuery] = useState("");

  const inputRef = useRef<HTMLTextAreaElement>(null);
  useAutoResize(inputRef, inputValue);

  const handleSubmit = () => {
    if (!inputValue.trim()) return;

    // 处理用户输入的链接或问题
    console.log("User input:", inputValue);

    // 跳转到学习页面，并传递输入内容
    router.push(`/learn?content=${encodeURIComponent(inputValue)}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePlanSubmit = () => {
    console.log("Learning plan:", planForm);
    // 处理学习计划创建逻辑，跳转到学习页面
    router.push("/learn");
    setShowPlanForm(false);
  };

  const handleCourseSelect = (course: string) => {
    console.log("Selected course:", course);
    // 处理课程选择逻辑，跳转到学习页面
    router.push(`/learn?course=${course}`);
  };

  const popularCourses = [
    { id: "cs231n", name: "CS231n: Deep Learning for Computer Vision", university: "Stanford" },
    { id: "cs229", name: "CS229: Machine Learning", university: "Stanford" },
    { id: "mit6006", name: "6.006: Introduction to Algorithms", university: "MIT" },
    { id: "cs188", name: "CS188: Artificial Intelligence", university: "Berkeley" },
  ];

  return (
    <div className="app-container">
      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* Header */}
        <header className="w-full p-6 bg-white border-b border-gray-100">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">Gradient AI</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
          <div className="w-full max-w-2xl">
            {/* Hero Section */}
            <div className="text-center mb-12">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
                  让天下没有
                  <span className="text-indigo-600">难懂</span>
                  的知识
                </h1>
                <p className="text-lg text-gray-500 mb-8 max-w-xl mx-auto">
                  输入视频链接或提出问题，让AI为你创建个性化的学习体验
                </p>
              </motion.div>
            </div>

            {/* Input Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="mb-8"
            >
              <Card className="p-6 border border-gray-200 bg-white rounded-xl">
                <div className="relative">
                  <Textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="粘贴视频链接或问个问题..."
                    className="min-h-[120px] border-0 focus:ring-0 resize-none text-base leading-relaxed pr-12 placeholder:text-gray-400"
                    style={{ boxShadow: "none" }}
                  />

                  {/* Send Button */}
                  <motion.div
                    className="absolute bottom-3 right-3"
                    initial={false}
                    animate={{
                      scale: inputValue.trim() ? 1 : 0.8,
                      opacity: inputValue.trim() ? 1 : 0.5,
                    }}
                  >
                    <Button
                      onClick={handleSubmit}
                      disabled={!inputValue.trim()}
                      size="sm"
                      className="h-8 w-8 rounded-full p-0 bg-indigo-600 hover:bg-indigo-700 transition-colors"
                    >
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                  </motion.div>
                </div>

                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center space-x-6 text-sm text-gray-400">
                    <div className="flex items-center space-x-2">
                      <Link className="w-4 h-4" />
                      <span>支持视频链接</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Sparkles className="w-4 h-4" />
                      <span>AI智能解析</span>
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8"
            >
              {/* Create Learning Plan */}
              <Card className="p-6 hover:shadow-sm transition-all duration-200 cursor-pointer bg-white border border-gray-200 hover:border-indigo-200 rounded-xl">
                <Button
                  variant="ghost"
                  className="w-full h-auto p-0 flex flex-col items-start space-y-3"
                  onClick={() => setShowPlanForm(true)}
                >
                  <div className="flex items-center space-x-4 w-full">
                    <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                      <span className="text-lg">🎯</span>
                    </div>
                    <div className="text-left">
                      <h3 className="font-semibold text-gray-900">定制学习计划</h3>
                      <p className="text-sm text-gray-500">与AI共创个性化学习路径</p>
                    </div>
                  </div>
                </Button>
              </Card>

              {/* Browse Courses */}
              <Card className="p-6 hover:shadow-sm transition-all duration-200 cursor-pointer bg-white border border-gray-200 hover:border-emerald-200 rounded-xl">
                <Button
                  variant="ghost"
                  className="w-full h-auto p-0 flex flex-col items-start space-y-3"
                  onClick={() => setShowCourseSearch(true)}
                >
                  <div className="flex items-center space-x-4 w-full">
                    <div className="w-10 h-10 bg-emerald-600 rounded-lg flex items-center justify-center">
                      <span className="text-lg">📚</span>
                    </div>
                    <div className="text-left">
                      <h3 className="font-semibold text-gray-900">学习现有课程</h3>
                      <p className="text-sm text-gray-500">学习CS231n等热门课程</p>
                    </div>
                  </div>
                </Button>
              </Card>
            </motion.div>
          </div>
        </main>

        {/* Learning Plan Form Modal */}
        <AnimatePresence>
          {showPlanForm && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
              onClick={() => setShowPlanForm(false)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-xl p-6 w-full max-w-md max-h-[80vh] overflow-y-auto"
              >
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold flex items-center space-x-2">
                    <GraduationCap className="w-5 h-5 text-indigo-600" />
                    <span>创建学习计划</span>
                  </h2>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowPlanForm(false)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    ✕
                  </Button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">学习主题</label>
                    <Input
                      value={planForm.topic}
                      onChange={(e) => setPlanForm({ ...planForm, topic: e.target.value })}
                      placeholder="例：机器学习、前端开发..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">当前水平</label>
                    <select
                      value={planForm.level}
                      onChange={(e) => setPlanForm({ ...planForm, level: e.target.value })}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="beginner">初学者</option>
                      <option value="intermediate">中级</option>
                      <option value="advanced">高级</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">学习目标</label>
                    <Textarea
                      value={planForm.goals}
                      onChange={(e) => setPlanForm({ ...planForm, goals: e.target.value })}
                      placeholder="描述你想要达到的学习目标..."
                      className="min-h-[80px]"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">学习安排</label>
                    <select
                      value={planForm.schedule}
                      onChange={(e) => setPlanForm({ ...planForm, schedule: e.target.value })}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="flexible">灵活安排</option>
                      <option value="daily">每日学习</option>
                      <option value="weekend">周末集中</option>
                      <option value="intensive">密集学习</option>
                    </select>
                  </div>
                </div>

                <div className="flex space-x-3 mt-6">
                  <Button
                    variant="outline"
                    onClick={() => setShowPlanForm(false)}
                    className="flex-1"
                  >
                    取消
                  </Button>
                  <Button
                    onClick={handlePlanSubmit}
                    className="flex-1 bg-indigo-600 hover:bg-indigo-700"
                  >
                    创建计划
                  </Button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Course Search Modal */}
        <AnimatePresence>
          {showCourseSearch && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
              onClick={() => setShowCourseSearch(false)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto"
              >
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold flex items-center space-x-2">
                    <BookOpen className="w-5 h-5 text-emerald-600" />
                    <span>选择课程</span>
                  </h2>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowCourseSearch(false)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    ✕
                  </Button>
                </div>

                {/* Search Input */}
                <div className="relative mb-6">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="搜索课程..."
                    className="pl-10"
                  />
                </div>

                {/* Upload Link */}
                <div className="mb-6">
                  <Button
                    variant="outline"
                    className="w-full flex items-center justify-center space-x-2 border-dashed"
                    onClick={() => router.push("/upload")}
                  >
                    <Upload className="w-4 h-4" />
                    <span>上传课程链接</span>
                  </Button>
                </div>

                {/* Popular Courses */}
                <div>
                  <h3 className="font-medium text-gray-900 mb-4">热门课程</h3>
                  <div className="space-y-3">
                    {popularCourses
                      .filter(
                        (course) =>
                          searchQuery === "" ||
                          course.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          course.university.toLowerCase().includes(searchQuery.toLowerCase())
                      )
                      .map((course) => (
                        <Card
                          key={course.id}
                          className="p-4 hover:shadow-sm transition-all duration-200 cursor-pointer border border-gray-200 hover:border-gray-300 rounded-lg"
                          onClick={() => handleCourseSelect(course.id)}
                        >
                          <div className="flex items-start space-x-3">
                            <div className="w-10 h-10 bg-emerald-600 rounded-lg flex items-center justify-center flex-shrink-0">
                              <BookOpen className="w-5 h-5 text-white" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-gray-900 truncate">{course.name}</h4>
                              <p className="text-sm text-gray-500">{course.university}</p>
                            </div>
                          </div>
                        </Card>
                      ))}
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
