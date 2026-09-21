"use client";
// SUU-193: Subparts · Checklist · 조문 세 칸을 VSCode처럼 끌어서 크기·위치를 바꾼다 (dockview).
// 칸 배치는 localStorage에 저장하고, "Reset layout"으로 기본 3열로 되돌린다.
import { createContext, useContext, useRef, type ReactNode } from "react";
import {
  DockviewReact,
  themeDark,
  type DockviewApi,
  type DockviewReadyEvent,
  type IDockviewPanelProps,
} from "dockview-react";
import "dockview/dist/styles/dockview.css";

export const PANELS = [
  { id: "subparts", title: "Subparts" },
  { id: "checklist", title: "Checklist" },
  { id: "section", title: "Section text" },
] as const;
export type PanelId = (typeof PANELS)[number]["id"];

const STORAGE_KEY = "workspace-layout";
const PanelContent = createContext<Partial<Record<PanelId, ReactNode>>>({});

// SUU-188의 칸(COLUMN) 역할: 칸은 overflow-hidden, 카드가 flex-1로 채우고 카드 안에서 스크롤.
function Panel(props: IDockviewPanelProps) {
  const content = useContext(PanelContent)[props.api.id as PanelId];
  return (
    <div data-panel={props.api.id} className="flex h-full min-h-0 flex-col overflow-hidden p-3">
      {content}
    </div>
  );
}
const components = { panel: Panel };

function addDefaultPanels(api: DockviewApi) {
  PANELS.forEach((p, i) => {
    api.addPanel({
      id: p.id,
      title: p.title,
      component: "panel",
      position: i === 0 ? undefined : { referencePanel: PANELS[i - 1].id, direction: "right" },
    });
  });
}

export default function Workspace({
  panels,
  className = "",
}: {
  panels: Partial<Record<PanelId, ReactNode>>;
  className?: string;
}) {
  const apiRef = useRef<DockviewApi | null>(null);

  function onReady({ api }: DockviewReadyEvent) {
    apiRef.current = api;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) api.fromJSON(JSON.parse(saved));
    } catch {
      api.clear();
    }
    if (api.panels.length === 0) addDefaultPanels(api);
    const save = () => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(api.toJSON()));
      } catch {}
    };
    save();
    api.onDidLayoutChange(save);
  }

  function reset() {
    const api = apiRef.current;
    if (!api) return;
    api.clear();
    addDefaultPanels(api);
  }

  return (
    <PanelContent.Provider value={panels}>
      <div className={`flex flex-col gap-2 ${className}`}>
        <button
          type="button"
          onClick={reset}
          className="self-end text-sm text-ink-muted underline hover:text-ink"
        >
          Reset layout
        </button>
        <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-hairline">
          <DockviewReact theme={themeDark} components={components} onReady={onReady} />
        </div>
      </div>
    </PanelContent.Provider>
  );
}
