import { useEffect } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";

export function AnimatedCounter({
  value,
  duration = 1.5,
}: {
  value: number;
  duration?: number;
}) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, Math.round);

  useEffect(() => {
    const animation = animate(count, value, { duration });
    return animation.stop;
  }, [value, duration, count]);

  return <motion.span>{rounded}</motion.span>;
}

export function CircularProgress({
  value,
  label,
  colorClass,
}: {
  value: number;
  label: string;
  colorClass: string;
}) {
  const circumference = 2 * Math.PI * 40;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-6 bg-bg-card border border-border-subtle rounded-xl">
      <div className="relative w-20 h-20 mb-4">
        <svg
          className="w-full h-full transform -rotate-90"
          viewBox="0 0 100 100"
        >
          <circle
            className="text-border-subtle"
            strokeWidth="6"
            stroke="currentColor"
            fill="transparent"
            r="40"
            cx="50"
            cy="50"
          />
          <motion.circle
            className={colorClass}
            strokeWidth="6"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
            strokeLinecap="round"
            stroke="currentColor"
            fill="transparent"
            r="40"
            cx="50"
            cy="50"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-semibold text-text-main">
            <AnimatedCounter value={value} />
          </span>
        </div>
      </div>
      <span className="text-sm text-text-muted font-medium text-center">
        {label}
      </span>
    </div>
  );
}
