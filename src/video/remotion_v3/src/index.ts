/**
 * V3 Remotion 진입점.
 *
 * 격리 모드 — V1/V2 (src/video/remotion/)와 완전히 분리된 패키지.
 */
import { registerRoot } from "remotion";
import { Root } from "./Root";

registerRoot(Root);
