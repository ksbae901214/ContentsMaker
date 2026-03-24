import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ContentsMaker - 블라인드 쇼츠 생성기",
  description: "블라인드 인기글을 만화 쇼츠 영상으로 자동 변환",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-950 text-white min-h-screen">{children}</body>
    </html>
  );
}
