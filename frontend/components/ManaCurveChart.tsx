"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface Props {
  manaCurve: { cmc: number; count: number }[] | Record<string, number>;
  averageCmc: number;
}

export default function ManaCurveChart({ manaCurve, averageCmc }: Props) {
  // Handle both array and object formats
  const data = Array.from({ length: 8 }, (_, i) => {
    const label = i === 7 ? "7+" : String(i);
    let count = 0;

    if (Array.isArray(manaCurve)) {
      const entry = manaCurve.find((m) => m.cmc === i);
      count = entry?.count || 0;
    } else {
      // Object format: {"0": 0, "1": 4, "2": 8, "7+": 11}
      const key = i === 7 ? "7+" : String(i);
      count = manaCurve[key] || 0;
    }

    return { cmc: label, count };
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xxs text-text-muted uppercase tracking-wider">
          Mana Curve
        </span>
        <span className="text-xxs text-text-secondary">
          avg cmc: {averageCmc.toFixed(2)}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="cmc"
            tick={{ fill: "#8888a0", fontSize: 10 }}
            axisLine={{ stroke: "#2a2a3a" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#8888a0", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: "#12121a",
              border: "1px solid #2a2a3a",
              borderRadius: 4,
              fontSize: 12,
              color: "#e0e0e8",
            }}
            cursor={{ fill: "rgba(74, 222, 128, 0.05)" }}
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.count > 0 ? "#4ade80" : "#2a2a3a"}
                fillOpacity={0.7}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}