"use client";
import { useState, useCallback, useRef } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: string;
  text: string;
  voice_text: string;
  emphasis: string;
}

interface Props {
  scenes: SceneData[];
  scriptPath: string;
  onScenesChange: (scenes: SceneData[]) => void;
  onSplit: (sceneId: number) => void;
  onMerge: (sceneId: number) => void;
}

const TYPE_COLORS: Record<string, string> = {
  title: "bg-yellow-600/80",
  body: "bg-blue-600/80",
  comment: "bg-purple-600/80",
};

const MIN_DURATION = 1.0;
const PIXELS_PER_SECOND = 60;

function SortableScene({
  scene,
  totalDuration,
  onResize,
  onSplit,
  onMerge,
  isLast,
}: {
  scene: SceneData;
  totalDuration: number;
  onResize: (sceneId: number, newDuration: number) => void;
  onSplit: (sceneId: number) => void;
  onMerge: (sceneId: number) => void;
  isLast: boolean;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: scene.id });

  const resizeRef = useRef<{ startX: number; startDur: number } | null>(null);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    width: `${scene.duration * PIXELS_PER_SECOND}px`,
    minWidth: `${MIN_DURATION * PIXELS_PER_SECOND}px`,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    resizeRef.current = { startX: e.clientX, startDur: scene.duration };

    const handleMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      const dx = ev.clientX - resizeRef.current.startX;
      const newDur = Math.max(
        MIN_DURATION,
        Math.min(30, resizeRef.current.startDur + dx / PIXELS_PER_SECOND)
      );
      onResize(scene.id, Math.round(newDur * 10) / 10);
    };

    const handleUp = () => {
      resizeRef.current = null;
      document.removeEventListener("mousemove", handleMove);
      document.removeEventListener("mouseup", handleUp);
    };

    document.addEventListener("mousemove", handleMove);
    document.addEventListener("mouseup", handleUp);
  };

  const typeLabel =
    scene.type === "title"
      ? "제목"
      : scene.type === "comment"
        ? "댓글"
        : "본문";

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative flex flex-col ${TYPE_COLORS[scene.type] || "bg-gray-600/80"} rounded-lg overflow-hidden select-none group`}
    >
      {/* Drag handle area */}
      <div
        {...attributes}
        {...listeners}
        className="flex-1 p-2 cursor-grab active:cursor-grabbing"
      >
        <div className="flex items-center gap-1 mb-1">
          <span className="text-[10px] font-bold text-white/80">
            {scene.id}
          </span>
          <span className="text-[10px] text-white/60">{typeLabel}</span>
        </div>
        <div className="text-[11px] text-white/90 leading-tight line-clamp-2 whitespace-pre-wrap">
          {scene.text.replace(/\\n/g, " ")}
        </div>
        <div className="text-[10px] text-white/50 mt-1">
          {scene.duration.toFixed(1)}s
        </div>
      </div>

      {/* Action buttons (visible on hover) */}
      <div className="absolute top-1 right-1 flex gap-0.5 opacity-0 group-hover:opacity-100 transition">
        <button
          onClick={() => onSplit(scene.id)}
          className="w-5 h-5 flex items-center justify-center bg-black/40 hover:bg-black/60 rounded text-[10px] text-white"
          title="분할"
        >
          ✂
        </button>
        {!isLast && (
          <button
            onClick={() => onMerge(scene.id)}
            className="w-5 h-5 flex items-center justify-center bg-black/40 hover:bg-black/60 rounded text-[10px] text-white"
            title="다음 씬과 병합"
          >
            ⊕
          </button>
        )}
      </div>

      {/* Resize handle (right edge) */}
      <div
        onMouseDown={handleResizeStart}
        className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-white/20 transition"
      />
    </div>
  );
}

export function Timeline({
  scenes,
  scriptPath,
  onScenesChange,
  onSplit,
  onMerge,
}: Props) {
  const [resizing, setResizing] = useState(false);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  const totalDuration = scenes.reduce((sum, s) => sum + s.duration, 0);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIdx = scenes.findIndex((s) => s.id === active.id);
      const newIdx = scenes.findIndex((s) => s.id === over.id);
      if (oldIdx === -1 || newIdx === -1) return;

      const newOrder = scenes.map((s) => s.id);
      const [moved] = newOrder.splice(oldIdx, 1);
      newOrder.splice(newIdx, 0, moved);

      try {
        const res = await fetch("/api/scene/split", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "reorder",
            new_order: newOrder,
            script_path: scriptPath,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          if (data.scenes) onScenesChange(data.scenes);
        }
      } catch {
        // revert on failure
      }
    },
    [scenes, scriptPath, onScenesChange]
  );

  const handleResize = useCallback(
    async (sceneId: number, newDuration: number) => {
      // Optimistic update
      const updated = scenes.map((s) =>
        s.id === sceneId ? { ...s, duration: newDuration } : s
      );
      // Recalculate timestamps
      let cursor = 0;
      const recalculated = updated.map((s) => {
        const scene = { ...s, timestamp: Math.round(cursor * 10) / 10 };
        cursor += s.duration;
        return scene;
      });
      onScenesChange(recalculated);
    },
    [scenes, onScenesChange]
  );

  // Time ruler marks
  const rulerMarks: number[] = [];
  for (let t = 0; t <= totalDuration; t += 5) {
    rulerMarks.push(t);
  }

  return (
    <div className="bg-gray-900 rounded-lg p-3 overflow-x-auto">
      {/* Time ruler */}
      <div
        className="relative h-5 mb-1 border-b border-gray-700"
        style={{ width: `${totalDuration * PIXELS_PER_SECOND}px`, minWidth: "100%" }}
      >
        {rulerMarks.map((t) => (
          <div
            key={t}
            className="absolute top-0 text-[10px] text-gray-500"
            style={{ left: `${t * PIXELS_PER_SECOND}px` }}
          >
            <div className="w-px h-2 bg-gray-600" />
            {t}s
          </div>
        ))}
      </div>

      {/* Scene bars */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={scenes.map((s) => s.id)}
          strategy={horizontalListSortingStrategy}
        >
          <div className="flex gap-1" style={{ minHeight: 80 }}>
            {scenes.map((scene, idx) => (
              <SortableScene
                key={scene.id}
                scene={scene}
                totalDuration={totalDuration}
                onResize={handleResize}
                onSplit={onSplit}
                onMerge={onMerge}
                isLast={idx === scenes.length - 1}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* Total duration */}
      <div className="text-right text-[11px] text-gray-500 mt-1">
        Total: {totalDuration.toFixed(1)}s
      </div>
    </div>
  );
}
