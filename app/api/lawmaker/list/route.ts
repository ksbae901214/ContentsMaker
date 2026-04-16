import { NextResponse } from "next/server";

// Popular female National Assembly lawmakers.
// Party reflects the 22nd National Assembly (elected June 2024).
// Update as needed when assembly composition changes.
const POPULAR_FEMALE_LAWMAKERS = [
  {
    name: "나경원",
    party: "국민의힘",
    role: "의원",
    description: "전 원내대표, 장기 경력 보수 중진",
    emoji: "🎤",
    searchQuery: "나경원 국회 발언",
  },
  {
    name: "배현진",
    party: "국민의힘",
    role: "의원",
    description: "전 MBC 앵커 출신, 날카로운 언변",
    emoji: "📺",
    searchQuery: "배현진 의원 국회 발언",
  },
  {
    name: "김예지",
    party: "국민의힘",
    role: "의원",
    description: "올림픽 펜싱 은메달리스트 출신",
    emoji: "🤺",
    searchQuery: "김예지 의원 국회 발언",
  },
  {
    name: "한지아",
    party: "국민의힘",
    role: "의원",
    description: "의사 출신, 보건복지위 전문 활동",
    emoji: "👩‍⚕️",
    searchQuery: "한지아 의원 국회 발언",
  },
  {
    name: "진선미",
    party: "더불어민주당",
    role: "의원",
    description: "전 장관, 여성가족위 활발 활동",
    emoji: "⚖️",
    searchQuery: "진선미 의원 국회 발언",
  },
  {
    name: "남인순",
    party: "더불어민주당",
    role: "의원",
    description: "보건복지위 여성의원 베테랑",
    emoji: "🏥",
    searchQuery: "남인순 의원 국회 발언",
  },
  {
    name: "서영교",
    party: "더불어민주당",
    role: "의원",
    description: "4선 여성의원, 법제사법위 활동",
    emoji: "🔨",
    searchQuery: "서영교 의원 국회 발언",
  },
  {
    name: "고민정",
    party: "더불어민주당",
    role: "의원",
    description: "전 청와대 대변인 출신",
    emoji: "💬",
    searchQuery: "고민정 의원 국회 발언",
  },
];

export async function GET() {
  return NextResponse.json({ lawmakers: POPULAR_FEMALE_LAWMAKERS });
}
