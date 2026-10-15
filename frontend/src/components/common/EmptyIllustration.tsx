/** Isometric "document with magnifying glass" artwork used by the empty states. */
export function EmptyIllustration({ width = 160 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 160 110" fill="none" aria-hidden focusable="false">
      {/* plant */}
      <path d="M104 30h18v14a9 9 0 0 1-18 0V30Z" fill="#FFFFFF" stroke="#90A4AE" strokeWidth="1.2" />
      <path d="M113 4l5 10 9-6-2 13 8 2-8 8h-24l-8-8 8-2-2-13 9 6 5-10Z" fill="#64B5F6" stroke="#1E88E5" strokeWidth="1" />
      <path d="M113 10v20M106 18l5 12M120 18l-5 12" stroke="#1E88E5" strokeWidth="0.8" />
      {/* document */}
      <path d="M14 66 70 42l46 24-56 26-46-26Z" fill="#BBDEFB" stroke="#64B5F6" strokeWidth="1.2" />
      <path d="M14 66v4l46 26v-4L14 66Z" fill="#90CAF9" />
      <path d="M60 92v4l56-26v-4L60 92Z" fill="#64B5F6" />
      <path d="M44 56l12-5 10 5-12 5-10-5Z" fill="#E3F2FD" stroke="#1E88E5" strokeWidth="0.8" />
      <circle cx="54" cy="55" r="2" fill="#1E88E5" />
      <path d="M36 66l30-13M42 70l30-13M48 74l22-9M54 78l16-7" stroke="#FFFFFF" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M70 56l16 8-6 3" stroke="#90A4AE" strokeWidth="0.8" />
      {/* book */}
      <path d="M118 62l16-7 12 6-16 7-12-6Z" fill="#42A5F5" stroke="#1565C0" strokeWidth="0.8" />
      <path d="M118 62v4l12 6v-4l-12-6Z" fill="#1E88E5" />
      <path d="M130 68v4l16-7v-4l-16 7Z" fill="#1565C0" />
      <path d="M126 60l8-3" stroke="#E3F2FD" strokeWidth="1" strokeLinecap="round" />
      {/* magnifier */}
      <ellipse cx="96" cy="86" rx="10" ry="7" fill="#E3F2FD" fillOpacity="0.6" stroke="#1E88E5" strokeWidth="2.4" />
      <path d="M87 91 72 100" stroke="#1E88E5" strokeWidth="3.2" strokeLinecap="round" />
    </svg>
  );
}
