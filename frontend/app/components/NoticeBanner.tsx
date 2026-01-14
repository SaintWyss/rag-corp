"use client";

type NoticeBannerProps = {
  message: string;
};

export function NoticeBanner({ message }: NoticeBannerProps) {
  if (!message) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
      {message}
    </div>
  );
}
