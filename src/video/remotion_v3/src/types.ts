export interface CaptionCue {
  startSec: number;
  endSec: number;
  text: string;
}

export interface MomentShortsProps {
  clipFileName: string;      // public/ 에 복사된 클립 파일명
  hookQuestion: string;      // 질문형 훅
  hookKeywords: string[];    // 색 강조 키워드
  captions: CaptionCue[];   // 실시간 자막 cue 목록
  sourceLabel: string;       // "출처: YTN (2016.12.15)"
  durationSec: number;       // 클립 전체 길이 (초)
}
