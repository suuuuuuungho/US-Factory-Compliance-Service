"use client";
// SUU-193: Subparts · Checklist · 조문 칸을 VSCode처럼 끌어서 크기·위치를 바꾼다 (dockview).
// 조문은 인용마다 칸 하나(id "section:<key>")로 열려 여러 개를 나란히 놓을 수 있다.
// 칸 배치는 localStorage에 저장하고, "Reset layout"으로 기본(Subparts | Checklist)으로 되돌린다.
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import {
  DockviewReact,
  themeDark,
  type DockviewApi,
  type DockviewReadyEvent,
  type IDockviewPanelProps,
} from "dockview-react";
import "dockview/dist/styles/dockview.css";

export type Panels = Record<string, { title: string; node: ReactNode }>;
export const FIXED = { subparts: "Subparts", checklist: "Checklist" } as const;

const STORAGE_KEY = "workspace-layout";
const PanelContent = createContext<Panels>({});

// SUU-188의 칸(COLUMN) 역할: 칸은 overflow-hidden, 카드가 flex-1로 채우고 카드 안에서 스크롤.
function Panel(props: IDockviewPanelProps) {
  const content = useContext(PanelContent)[props.api.id];
  return (
    <div data-panel={props.api.id} className="flex h-full min-h-0 flex-col overflow-hidden p-3">
      {content?.node}
    </div>
  );
}
const components = { panel: Panel };

function addPanel(api: DockviewApi, id: string, title: string) {
  // 조문은 이미 열린 조문 칸에 탭으로, 그 외(첫 조문 포함)는 맨 오른쪽 칸 옆에.
  const sibling = id.startsWith("section:")
    ? api.panels.find((p) => p.id.startsWith("section:") && p.id !== id)
    : undefined;
  const last = api.panels[api.panels.length - 1];
  api.addPanel({
    id,
    title,
    component: "panel",
    position: sibling
      ? { referenceGroup: sibling.group }
      : last
        ? { referencePanel: last.id, direction: "right" }
        : undefined,
  });
}

function addDefaultPanels(api: DockviewApi) {
  for (const [id, title] of Object.entries(FIXED)) addPanel(api, id, title);
}

export default function Workspace({
  panels,
  active,
  onClose,
  className = "",
}: {
  panels: Panels;
  active?: string; // 이 id의 칸을 앞으로 가져온다 (인용 클릭)
  onClose?: (id: string) => void; // 사용자가 탭 ✕로 칸을 닫음
  className?: string;
}) {
  const [api, setApi] = useState<DockviewApi | null>(null);
  const [, bump] = useState(0); // 칸이 열리고 닫힐 때 버튼 상태를 다시 그린다
  const prevIds = useRef<string[]>([]); // 직전 panels의 id. 새로 생긴 id만 칸으로 추가하려고

  function onReady({ api }: DockviewReadyEvent) {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) api.fromJSON(JSON.parse(saved));
    } catch {
      api.clear();
    }
    // 저장된 배치에 남아 있지만 지금은 내용이 없는 칸(지난번 조문)은 뺀다.
    for (const p of [...api.panels]) if (!panels[p.id]) api.removePanel(p);
    if (api.panels.length === 0) addDefaultPanels(api);
    prevIds.current = Object.keys(panels);
    const save = () => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(api.toJSON()));
      } catch {}
      bump((n) => n + 1);
    };
    save();
    api.onDidLayoutChange(save);
    api.onDidRemovePanel((p) => onClose?.(p.id));
    setApi(api);
  }

  // 새로 생긴 id(인용 클릭으로 열린 조문)만 칸으로 추가한다. 이미 있던 id는 사용자가 닫았을 수 있으니 건드리지 않는다.
  // 조문 칸을 ✕로 닫으면 onClose로 panels에서 빠지므로, 같은 인용을 다시 클릭하면 "새로 생긴 id"가 되어 다시 열린다.
  useEffect(() => {
    if (!api) return;
    for (const [id, { title }] of Object.entries(panels)) {
      if (!prevIds.current.includes(id) && !api.getPanel(id)) addPanel(api, id, title);
    }
    prevIds.current = Object.keys(panels);
  }, [api, panels]);

  useEffect(() => {
    if (api && active) api.getPanel(active)?.api.setActive();
  }, [api, active]);

  function toggle(id: string) {
    if (!api) return;
    const p = api.getPanel(id);
    if (p) api.removePanel(p);
    else addPanel(api, id, panels[id].title);
  }

  function reset() {
    if (!api) return;
    api.clear();
    addDefaultPanels(api);
  }

  const BTN = "rounded-full border border-hairline px-3 py-1 text-sm";
  return (
    <PanelContent.Provider value={panels}>
      <div className={`flex flex-col gap-2 ${className}`}>
        <div className="flex items-center gap-2">
          {Object.entries(FIXED).map(([id, title]) => {
            const open = !!api?.getPanel(id);
            return (
              <button
                key={id}
                type="button"
                aria-pressed={open}
                onClick={() => toggle(id)}
                className={`${BTN} ${open ? "bg-surface-2 text-ink" : "text-ink-muted"}`}
              >
                {title}
              </button>
            );
          })}
          <button type="button" onClick={reset} className={`${BTN} ml-auto text-ink-muted hover:text-ink`}>
            Reset layout
          </button>
        </div>
        {/* SUU-194: dockview 루트는 height:100%인데 flex로 늘어난 칸에서는 0이 된다 → absolute로 꽉 채운다 */}
        <div className="relative min-h-0 flex-1 overflow-hidden rounded-lg border border-hairline [&>div]:absolute [&>div]:inset-0">
          <DockviewReact theme={themeDark} components={components} onReady={onReady} />
        </div>
      </div>
    </PanelContent.Provider>
  );
}
