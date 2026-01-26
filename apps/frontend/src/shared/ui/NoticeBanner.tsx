"use client";

type NoticeBannerProps = {
  message: string;
};

export function NoticeBanner({ message }: NoticeBannerProps) {
  if (!message) {
    return null;
  }

  return (
    <div 
      data-testid="notice-banner-success"
      className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300 font-medium shadow-sm"
    >
      {message}
    </div>
  );
}
