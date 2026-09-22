// SUU-248: 주(State)별 벌금 총액을 미국 지도 색으로. us-atlas(states-10m) + @visx/geo AlbersUsa.
"use client";

import { useState } from "react";
import { AlbersUsa } from "@visx/geo";
import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import type { Feature, Geometry } from "geojson";
import topology from "us-atlas/states-10m.json";

// us-atlas 는 FIPS 번호만 준다. 우리 데이터는 우편 약자(TX)라 이 표로 잇는다
const FIPS_TO_STATE: Record<string, string> = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
  "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
  "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
  "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
  "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
  "56": "WY", "72": "PR",
};

type StateFeature = Feature<Geometry, { name: string }> & { id: string };

const topo = topology as unknown as Topology<{ states: GeometryCollection<{ name: string }> }>;
const STATES = (feature(topo, topo.objects.states) as unknown as { features: StateFeature[] }).features;

// d3 albersUsa 기본: 975×610 화면에 scale 1300, 가운데 translate
const WIDTH = 975;
const HEIGHT = 610;

export type StateValue = { state: string; value: number; label: string };

export function UsStateMap({ values, name }: { values: StateValue[]; name: string }) {
  const [hover, setHover] = useState<StateValue | null>(null);
  const byState = new Map(values.map((v) => [v.state, v]));
  const max = Math.max(0, ...values.map((v) => v.value));

  // 큰 값일수록 밝게. 제곱근이라 1등 하나가 나머지를 다 어둡게 만들지 않는다
  const fillFor = (code: string | undefined) => {
    const v = code ? byState.get(code) : undefined;
    if (!v || !max || v.value <= 0) return "rgba(255,255,255,0.06)";
    return `rgba(255,255,255,${(0.12 + 0.78 * Math.sqrt(v.value / max)).toFixed(3)})`;
  };

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={name} className="block h-auto w-full">
        <AlbersUsa<StateFeature> data={STATES} scale={1300} translate={[WIDTH / 2, HEIGHT / 2]}>
          {({ features }) =>
            features.map(({ feature: f, path }) => {
              const code = FIPS_TO_STATE[f.id];
              const v = code ? byState.get(code) : undefined;
              return (
                <path
                  key={f.id}
                  d={path ?? ""}
                  data-state={code}
                  fill={fillFor(code)}
                  stroke="var(--color-canvas, #090909)"
                  strokeWidth={1}
                  onMouseEnter={() => setHover(v ?? { state: code ?? f.properties.name, value: 0, label: "—" })}
                  onMouseLeave={() => setHover(null)}
                >
                  <title>{`${f.properties.name}: ${v?.label ?? "—"}`}</title>
                </path>
              );
            })
          }
        </AlbersUsa>
      </svg>
      <p data-testid="map-hover" className="mt-1 h-5 text-center text-sm text-ink tabular-nums">
        {hover ? `${hover.state} · ${hover.label}` : " "}
      </p>
    </div>
  );
}
