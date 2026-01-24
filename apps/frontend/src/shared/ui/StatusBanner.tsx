"use client";

type StatusBannerProps = {
  message: string;
};

export function StatusBanner({ message }: StatusBannerProps) {
  if (!message) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-300 font-medium shadow-sm">
      {message}
    </div>
  );
}
