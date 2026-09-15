import React from "react";
import { Link } from "react-router-dom";

interface HiveMarkProps {
  to?: string;
  onClick?: () => void;
  className?: string;
  size?: "sm" | "md";
}

export default function HiveMark({
  to = "/",
  onClick,
  className = "",
  size = "md",
}: HiveMarkProps) {
  const inner = (
    <>
      <svg className="mark-glyph" viewBox="0 0 28 28" aria-hidden="true">
        <rect width="28" height="28" rx="6" fill="#1158E5" />
        <path
          d="M8 7v14h3.2V16.2H14c2.6 0 4.3-1.4 4.3-3.6S16.6 9 14 9H11.2V7H8zm3.2 4.6H13.8c1.1 0 1.7.5 1.7 1.3s-.6 1.3-1.7 1.3h-2.6v-2.6zM17.2 21l3.4-7.2h-2.5L16 18.6 13.9 13.8H11.4L15 21h2.2z"
          fill="#fff"
        />
      </svg>
      <span className="mark-word">HiveRank</span>
    </>
  );

  const classes = `mark ${className}`.trim();

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={classes}
        style={{ background: "none", border: "none", padding: 0, cursor: "pointer" }}
        aria-label="HiveRank home"
      >
        {inner}
      </button>
    );
  }

  return (
    <Link to={to} className={classes} aria-label="HiveRank home">
      {inner}
    </Link>
  );
}
