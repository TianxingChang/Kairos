import { motion } from "framer-motion";

interface LoadingDotsAltProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function LoadingDotsAlt({ size = "md", className = "" }: LoadingDotsAltProps) {
  const sizeClasses = {
    sm: "w-1 h-1",
    md: "w-1.5 h-1.5",
    lg: "w-2 h-2",
  };

  const dotVariants = {
    animate: {
      y: [0, -10, 0],
      transition: {
        duration: 0.6,
        repeat: Infinity,
        ease: "easeInOut" as const,
      },
    },
  };

  return (
    <div className={`flex items-center justify-center space-x-1 ${className}`}>
      {[0, 1, 2].map((index) => (
        <motion.div
          key={index}
          className={`bg-current rounded-full ${sizeClasses[size]}`}
          variants={dotVariants}
          animate="animate"
          transition={{
            delay: index * 0.1,
          }}
        />
      ))}
    </div>
  );
}
