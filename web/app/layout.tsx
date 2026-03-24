import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "ContentsMaker", description: "블라인드 쇼츠 생성기" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="ko"><body className="bg-gray-950 text-white min-h-screen">{children}</body></html>);
}
