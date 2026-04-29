"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

const COLOR_MAP: Record<string, { label: string; fill: string }> = {
  W: { label: "White", fill: "#f9f4e8" },
  U: { label: "Blue", fill: "#0e68ab" },
  B: { label: "Black", fill: "#3d3329" },
  R: { label: "Red", fill: "#d3202a" },
  G: { label: "Green", fill: "#00733e" },
  C: { label: "Colorless", fill: "#9da1a4" },
};

interface Props {
  colorDistribution: Record<string, { name: string; count: number }> | { color: string; count: number }[];
}

export default function ColorDistributionChart({ colorDistribution }: Props) {
  // Normalize to array format
  const entries = Array.isArray(colorDistribution)
    ? colorDistribution.map((c) => ({ key: c.color, count: c.count }))
    : Object.entries(colorDistribution).map(([key, info]) => ({
        key,
        count: typeof info === "object" ? info.count : Number(info),
      }));

  const data = entries
    .filter((c) => c.count > 0)
    .map((c) => ({
      name: COLOR_MAP[c.key]?.label || c.key,
      value: c.count,
      fill: COLOR_MAP[c.key]?.fill || "#9da1a4",
    }));

  if (data.length === 0) return null;

  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <div>
      <div className="text-xxs text-text-muted uppercase tracking-wider mb-2">
        Color Distribution
      </div>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width={100} height={100}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              cx="50%"
              cy="50%"
              innerRadius={25}
              outerRadius={45}
              strokeWidth={1}
              stroke="#0a0a0f"
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#12121a",
                border: "1px solid #2a2a3a",
                borderRadius: 4,
                fontSize: 12,
                color: "#e0e0e8",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex-1 space-y-1">
          {data.map((d) => (
            <div key={d.name} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ background: d.fill }}
                />
                <span className="text-text-secondary">{d.name}</span>
              </div>
              <span className="text-text-primary">
                {d.value} <span className="text-text-muted">({Math.round((d.value / total) * 100)}%)</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}