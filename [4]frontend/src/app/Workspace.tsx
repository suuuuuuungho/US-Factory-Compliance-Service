"use client";
// SUU-193: Subparts · Checklist · 조문 칸을 VSCode처럼 끌어서 크기·위치를 바꾼다 (dockview).
// 조문은 인용마다 칸 하나(id "section:<key>")로 열려 여러 개를 나란히 놓을 수 있다.
// 칸 배치는 localStorage에 저장한다.
// SUU-199: 질문 폼(question)과 메모(memo)도 칸이다.
// SUU-200: 기본 배치 = 왼쪽 열 Question(위, 높이 25%)/Subparts(아래) | Memo(폭 18%) | Checklist(폭 25%). Memo도 처음부터 열린다.
// 조문은 Subparts 옆(같은 열)에 열린다. 위쪽 버튼 줄은 없고, 각 칸 머리의 + 메뉴로 Question·Subparts·Checklist·Memo·조문을
// 그 칸에 탭으로 넣는다(이미 열려 있으면 옮겨 온다). 지우기는 탭의 ✕. Reset 버튼은 없고, 칸을 전부 닫으면 기본 배치로 돌아온다.
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import {
  DockviewReact,
  themeDark,
  type DockviewApi,
  type DockviewGroupPanel,
  type DockviewReadyEvent,
  type IDockviewHeaderActionsProps,
  type IDockviewPanelProps,
} from "dockview-react";
import "dockview/dist/styles/dockview.css";

export type Panels = Record<string, { title: string; node: ReactNode }>;
export type SectionItem = { key: string; title: string }; // + 메뉴의 조문 항목 (답변에 인용된 조문)
const FIXED = ["question", "subparts", "checklist", "memo"];
const DEFAULT = ["question", "checklist", "subparts", "memo"]; // 추가 순서. position()이 자리를 정한다

const STORAGE_KEY = "workspace-layout-v3"; // v2까지는 위쪽 버튼 줄이 있던 배치
const PanelContent = createContext<Panels>({});

type Menu = {
  sections: SectionItem[];
  add: (id: string, group: DockviewGroupPanel) => void;
  openSection: (key: string, group: DockviewGroupPanel) => void;
};
const MenuCtx = createContext<Menu | null>(null);

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

// 칸 머리 오른쪽의 + 버튼. 누르면 이 칸에 넣을 것을 고르는 메뉴가 열린다.
function AddMenu({ group }: IDockviewHeaderActionsProps) {
  const menu = useContext(MenuCtx);
  const panels = useContext(PanelContent);
  const [open, setOpen] = useState(false);
  if (!menu) return null;
  const pick = (fn: () => void) => () => {
    fn();
    setOpen(false);
  };
  const ITEM = "block w-full px-3 py-1.5 text-left text-ink hover:bg-surface-1";
  return (
    <div className="relative flex h-full items-center px-1">
      <button
        type="button"
        aria-label="Add panel"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="rounded px-2 text-lg leading-none text-ink-muted hover:text-ink"
      >
        +
      </button>
      {open && (
        <ul role="menu" className="absolute right-0 top-full z-20 min-w-44 rounded-md border border-hairline bg-surface-2 py-1 text-sm shadow-lg">
          {FIXED.filter((id) => panels[id]).map((id) => (
            <li key={id} role="none">
              <button type="button" role="menuitem" onClick={pick(() => menu.add(id, group))} className={ITEM}>
                {panels[id].title}
              </button>
            </li>
          ))}
          {menu.sections.length > 0 && (
            <li role="none" className="mt-1 border-t border-hairline px-3 pt-1.5 text-xs text-ink-muted">
              Sections
            </li>
          )}
          {menu.sections.map((s) => (
            <li key={s.key} role="none">
              <button type="button" role="menuitem" onClick={pick(() => menu.openSection(s.key, group))} className={ITEM}>
                {s.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function position(api: DockviewApi, id: string) {
  // 조문은 이미 열린 조문 칸에 탭으로, 첫 조문은 subparts 오른쪽. subparts는 question 아래, memo는 checklist 왼쪽.
  // 그 외는 checklist(없으면 마지막 칸) 오른쪽에.
  const section = id.startsWith("section:");
  const sibling = section ? api.panels.find((p) => p.id.startsWith("section:") && p.id !== id) : undefined;
  if (sibling) return { referenceGroup: sibling.group };
  if (section && api.getPanel("subparts")) return { referencePanel: "subparts", direction: "right" as const };
  if (id === "subparts" && api.getPanel("question")) return { referencePanel: "question", direction: "below" as const };
  if (id === "memo" && api.getPanel("checklist")) return { referencePanel: "checklist", direction: "left" as const };
  const ref = api.getPanel("checklist") ?? api.panels[api.panels.length - 1];
  return ref ? { referencePanel: ref.id, direction: "right" as const } : undefined;
}

function addPanel(api: DockviewApi, id: string, title: string, group?: DockviewGroupPanel) {
  api.addPanel({ id, title, component: "panel", position: group ? { referenceGroup: group } : position(api, id) });
}

function addDefaultPanels(api: DockviewApi, panels: Panels) {
  for (const id of DEFAULT) addPanel(api, id, panels[id].title);
  // 기본 크기 비율. jsdom처럼 api.width/height가 0이면 건너뛴다.
  if (!api.width || !api.height) return;
  api.getPanel("question")?.api.setSize({ height: Math.round(api.height * 0.25) });
  api.getPanel("memo")?.api.setSize({ width: Math.round(api.width * 0.18) });
  api.getPanel("checklist")?.api.setSize({ width: Math.round(api.width * 0.25) });
}

export default function Workspace({
  panels,
  sections = [],
  active,
  onClose,
  onOpenSection,
  className = "",
}: {
  panels: Panels;
  sections?: SectionItem[]; // + 메뉴에 보일 조문
  active?: string; // 이 id의 칸을 앞으로 가져온다 (인용 클릭)
  onClose?: (id: string) => void; // 사용자가 탭 ✕로 칸을 닫음
  onOpenSection?: (key: string) => void; // + 메뉴에서 조문을 고름 → 부모가 panels에 넣어 준다
  className?: string;
}) {
  const [api, setApi] = useState<DockviewApi | null>(null);
  const prevIds = useRef<string[]>([]); // 직전 panels의 id. 새로 생긴 id만 칸으로 추가하려고
  const pendingGroup = useRef<DockviewGroupPanel | null>(null); // + 메뉴로 고른 조문이 들어갈 칸

  function onReady({ api }: DockviewReadyEvent) {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) api.fromJSON(JSON.parse(saved));
    } catch {
      api.clear();
    }
    // 저장된 배치에 남아 있지만 지금은 내용이 없는 칸(지난번 조문)은 뺀다.
    for (const p of [...api.panels]) if (!panels[p.id]) api.removePanel(p);
    if (api.panels.length === 0) addDefaultPanels(api, panels);
    prevIds.current = Object.keys(panels);
    const save = () => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(api.toJSON()));
      } catch {}
    };
    save();
    api.onDidLayoutChange(save);
    api.onDidRemovePanel((p) => {
      onClose?.(p.id);
      if (api.panels.length === 0) addDefaultPanels(api, panels); // 전부 닫으면 + 버튼도 없어지므로 기본으로
    });
    setApi(api);
  }

  // 새로 생긴 id(인용 클릭·+ 메뉴로 열린 조문)만 칸으로 추가한다. 이미 있던 id는 사용자가 닫았을 수 있으니 건드리지 않는다.
  // 조문 칸을 ✕로 닫으면 onClose로 panels에서 빠지므로, 같은 인용을 다시 클릭하면 "새로 생긴 id"가 되어 다시 열린다.
  useEffect(() => {
    if (!api) return;
    for (const [id, { title }] of Object.entries(panels)) {
      if (!prevIds.current.includes(id) && !api.getPanel(id)) {
        const group = pendingGroup.current && api.getGroup(pendingGroup.current.id) ? pendingGroup.current : undefined;
        pendingGroup.current = null;
        addPanel(api, id, title, group);
      }
    }
    prevIds.current = Object.keys(panels);
  }, [api, panels]);

  useEffect(() => {
    if (api && active) api.getPanel(active)?.api.setActive();
  }, [api, active]);

  // 이미 열려 있으면 그 칸으로 옮겨 오고, 없으면 그 칸에 탭으로 새로 연다.
  function moveOrAdd(id: string, title: string, group: DockviewGroupPanel) {
    if (!api) return;
    const p = api.getPanel(id);
    if (p) {
      if (p.group !== group) p.api.moveTo({ group });
      p.api.setActive();
    } else addPanel(api, id, title, group);
  }

  const menu: Menu = {
    sections,
    add: (id, group) => moveOrAdd(id, panels[id].title, group),
    openSection: (key, group) => {
      const id = `section:${key}`;
      if (panels[id]) return moveOrAdd(id, panels[id].title, group);
      pendingGroup.current = group;
      onOpenSection?.(key);
    },
  };

  return (
    <PanelContent.Provider value={panels}>
      <MenuCtx.Provider value={menu}>
        {/* SUU-194: dockview 루트는 height:100%인데 flex로 늘어난 칸에서는 0이 된다 → absolute로 꽉 채운다 */}
        <div className={`relative min-h-0 overflow-hidden rounded-lg border border-hairline [&>div]:absolute [&>div]:inset-0 ${className}`}>
          <DockviewReact
            theme={themeDark}
            components={components}
            rightHeaderActionsComponent={AddMenu}
            onReady={onReady}
          />
        </div>
      </MenuCtx.Provider>
    </PanelContent.Provider>
  );
}
