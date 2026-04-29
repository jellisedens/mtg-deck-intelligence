"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLOR_LABELS: Record<string, { label: string; fill: string }> = {
  W: { label: "White", fill: "#f9f4e8" },
  U: { label: "Blue", fill: "#0e68ab" },
  B: { label: "Black", fill: "#3d3329" },
  R: { label: "Red", fill: "#d3202a" },
  G: { label: "Green", fill: "#00733e" },
};

export interface TurnData {
  turn: number;
  avg_lands_on_board: number;
  avg_total_mana_available: number;
  avg_cards_in_hand: number;
  avg_creatures_on_board: number;
  avg_total_power_on_board: number;
  avg_permanents_on_board: number;
  avg_spells_cast: number;
  avg_castable_after_land: number;
  avg_uncastable_cards: number;
  avg_color_sources: Record<string, number>;
  on_curve_rate: number;
  all_colors_rate: number;
  color_access_rates: Record<string, number>;
  mana_on_curve_rate: number;
}

interface Props {
  turnData: TurnData[];
  gamesSimulated: number;
}

type Tab = "overview" | "mana" | "board" | "colors" | "chart";

function grade(value: number, good: number, ok: number): string {
  if (value >= good) return "text-accent-green";
  if (value >= ok) return "text-accent-yellow";
  return "text-accent-red";
}

function Insight({ label, status }: { label: string; status: "good" | "warn" | "bad" }) {
  const icon = status === "good" ? "✓" : status === "warn" ? "!" : "✕";
  const color = status === "good" ? "text-accent-green" : status === "warn" ? "text-accent-yellow" : "text-accent-red";
  return (
    <div className="flex items-start gap-1.5 text-xs">
      <span className={`${color} flex-shrink-0`}>{icon}</span>
      <span className="text-text-secondary">{label}</span>
    </div>
  );
}

function OverviewTab({ turnData }: { turnData: TurnData[] }) {
  const t3 = turnData[2];
  const t5 = turnData[4];
  const t7 = turnData[6];

  if (!t3 || !t5) return null;

  // Generate insights
  const insights: { label: string; status: "good" | "warn" | "bad" }[] = [];

  // Mana development
  if (t3.mana_on_curve_rate >= 85) {
    insights.push({ label: `Mana development is strong — ${t3.mana_on_curve_rate}% on curve by T3`, status: "good" });
  } else if (t3.mana_on_curve_rate >= 70) {
    insights.push({ label: `Mana development is adequate — ${t3.mana_on_curve_rate}% on curve by T3`, status: "warn" });
  } else {
    insights.push({ label: `Mana development is poor — only ${t3.mana_on_curve_rate}% on curve by T3. Add more ramp or lands`, status: "bad" });
  }

  // Ramp effectiveness
  const rampDiff = t5.avg_total_mana_available - t5.avg_lands_on_board;
  if (rampDiff >= 1.5) {
    insights.push({ label: `Ramp is effective — ${rampDiff.toFixed(1)} extra mana beyond lands by T5`, status: "good" });
  } else if (rampDiff >= 0.5) {
    insights.push({ label: `Ramp is modest — only ${rampDiff.toFixed(1)} extra mana beyond lands by T5`, status: "warn" });
  } else {
    insights.push({ label: `Ramp is weak — mana barely exceeds land count. Add mana rocks or ramp spells`, status: "bad" });
  }

  // Board presence
  if (t5.avg_creatures_on_board >= 2) {
    insights.push({ label: `Board develops well — ${t5.avg_creatures_on_board.toFixed(1)} creatures by T5`, status: "good" });
  } else if (t5.avg_creatures_on_board >= 1) {
    insights.push({ label: `Board develops slowly — only ${t5.avg_creatures_on_board.toFixed(1)} creatures by T5`, status: "warn" });
  } else {
    insights.push({ label: `Board is empty too long — ${t5.avg_creatures_on_board.toFixed(1)} creatures by T5. Threats deploy late`, status: "bad" });
  }

  // Castability
  if (t5.avg_uncastable_cards <= 1.5) {
    insights.push({ label: `Card flow is smooth — only ${t5.avg_uncastable_cards.toFixed(1)} stuck cards by T5`, status: "good" });
  } else if (t5.avg_uncastable_cards <= 3) {
    insights.push({ label: `Some cards stuck — ${t5.avg_uncastable_cards.toFixed(1)} uncastable in hand by T5`, status: "warn" });
  } else {
    insights.push({ label: `Hand is clogged — ${t5.avg_uncastable_cards.toFixed(1)} uncastable cards by T5. Curve too high or fixing insufficient`, status: "bad" });
  }

  // Color access
  if (t5.all_colors_rate >= 80) {
    insights.push({ label: `Color fixing is strong — all colors available ${t5.all_colors_rate}% of the time by T5`, status: "good" });
  } else if (t5.all_colors_rate >= 60) {
    insights.push({ label: `Color fixing is adequate — all colors available ${t5.all_colors_rate}% by T5`, status: "warn" });
  } else {
    insights.push({ label: `Color fixing is poor — all colors available only ${t5.all_colors_rate}% by T5. Add more fixing`, status: "bad" });
  }

  // Spell casting rate
  if (t5.on_curve_rate >= 75) {
    insights.push({ label: `Casting spells on curve ${t5.on_curve_rate}% of the time by T5`, status: "good" });
  } else if (t5.on_curve_rate >= 55) {
    insights.push({ label: `On-curve rate is ${t5.on_curve_rate}% by T5 — sometimes falling behind`, status: "warn" });
  } else {
    insights.push({ label: `Only casting on curve ${t5.on_curve_rate}% by T5 — deck is too slow`, status: "bad" });
  }

  // Late game power
  if (t7) {
    if (t7.avg_total_power_on_board >= 15) {
      insights.push({ label: `Strong late game — ${t7.avg_total_power_on_board.toFixed(0)} power on board by T7`, status: "good" });
    } else if (t7.avg_total_power_on_board >= 8) {
      insights.push({ label: `Moderate late game — ${t7.avg_total_power_on_board.toFixed(0)} power by T7`, status: "warn" });
    } else {
      insights.push({ label: `Weak late game — only ${t7.avg_total_power_on_board.toFixed(0)} power by T7`, status: "bad" });
    }
  }

  return (
    <div className="space-y-1.5">
      {insights.map((insight, i) => (
        <Insight key={i} label={insight.label} status={insight.status} />
      ))}
    </div>
  );
}

function ManaTab({ turnData }: { turnData: TurnData[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-text-muted border-b border-border">
            <th className="text-left py-1.5 pr-2 font-medium">turn</th>
            <th className="text-right py-1.5 px-2 font-medium">lands</th>
            <th className="text-right py-1.5 px-2 font-medium">mana</th>
            <th className="text-right py-1.5 px-2 font-medium">ramp+</th>
            <th className="text-right py-1.5 px-2 font-medium">on curve</th>
            <th className="text-right py-1.5 pl-2 font-medium">castable</th>
          </tr>
        </thead>
        <tbody>
          {turnData.map((t) => {
            const rampBonus = t.avg_total_mana_available - t.avg_lands_on_board;
            return (
              <tr key={t.turn} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                <td className="py-1.5 pr-2 text-text-secondary">T{t.turn}</td>
                <td className="py-1.5 px-2 text-right text-accent-green">{t.avg_lands_on_board.toFixed(1)}</td>
                <td className="py-1.5 px-2 text-right text-accent-blue">{t.avg_total_mana_available.toFixed(1)}</td>
                <td className={`py-1.5 px-2 text-right ${rampBonus >= 1 ? "text-accent-green" : "text-text-muted"}`}>
                  +{rampBonus.toFixed(1)}
                </td>
                <td className={`py-1.5 px-2 text-right ${grade(t.mana_on_curve_rate, 80, 60)}`}>
                  {t.mana_on_curve_rate}%
                </td>
                <td className="py-1.5 pl-2 text-right text-text-primary">{t.avg_castable_after_land.toFixed(1)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BoardTab({ turnData }: { turnData: TurnData[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-text-muted border-b border-border">
            <th className="text-left py-1.5 pr-2 font-medium">turn</th>
            <th className="text-right py-1.5 px-2 font-medium">creatures</th>
            <th className="text-right py-1.5 px-2 font-medium">power</th>
            <th className="text-right py-1.5 px-2 font-medium">permanents</th>
            <th className="text-right py-1.5 px-2 font-medium">hand</th>
            <th className="text-right py-1.5 pl-2 font-medium">stuck</th>
          </tr>
        </thead>
        <tbody>
          {turnData.map((t) => (
            <tr key={t.turn} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
              <td className="py-1.5 pr-2 text-text-secondary">T{t.turn}</td>
              <td className="py-1.5 px-2 text-right text-accent-yellow">{t.avg_creatures_on_board.toFixed(1)}</td>
              <td className="py-1.5 px-2 text-right text-accent-red">{t.avg_total_power_on_board.toFixed(1)}</td>
              <td className="py-1.5 px-2 text-right text-text-primary">{t.avg_permanents_on_board.toFixed(1)}</td>
              <td className="py-1.5 px-2 text-right text-text-primary">{t.avg_cards_in_hand.toFixed(1)}</td>
              <td className={`py-1.5 pl-2 text-right ${grade(5 - t.avg_uncastable_cards, 3.5, 2)}`}>
                {t.avg_uncastable_cards.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ColorsTab({ turnData }: { turnData: TurnData[] }) {
  const colors = ["W", "U", "B", "R", "G"];
  const keyTurns = [1, 3, 5, 7, 10];
  const filtered = turnData.filter((t) => keyTurns.includes(t.turn));

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border">
              <th className="text-left py-1.5 pr-2 font-medium">turn</th>
              {colors.map((c) => (
                <th key={c} className="text-right py-1.5 px-1 font-medium">
                  <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLOR_LABELS[c].fill }} />
                </th>
              ))}
              <th className="text-right py-1.5 pl-2 font-medium">all 5</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.turn} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                <td className="py-1.5 pr-2 text-text-secondary">T{t.turn}</td>
                {colors.map((c) => {
                  const rate = t.color_access_rates?.[c] || 0;
                  return (
                    <td key={c} className={`py-1.5 px-1 text-right ${grade(rate, 85, 70)}`}>
                      {rate.toFixed(0)}%
                    </td>
                  );
                })}
                <td className={`py-1.5 pl-2 text-right font-medium ${grade(t.all_colors_rate, 75, 50)}`}>
                  {t.all_colors_rate.toFixed(0)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Color sources at T5 */}
      {turnData[4] && (
        <div>
          <div className="text-xxs text-text-muted mb-1">avg sources by T5</div>
          <div className="flex gap-3">
            {colors.map((c) => (
              <div key={c} className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full" style={{ background: COLOR_LABELS[c].fill }} />
                <span className="text-xs text-text-secondary">
                  {(turnData[4].avg_color_sources?.[c] || 0).toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ChartView({ turnData }: { turnData: TurnData[] }) {
  const data = turnData.map((t) => ({
    turn: `T${t.turn}`,
    lands: Number(t.avg_lands_on_board.toFixed(1)),
    mana: Number(t.avg_total_mana_available.toFixed(1)),
    creatures: Number(t.avg_creatures_on_board.toFixed(1)),
    power: Number(t.avg_total_power_on_board.toFixed(1)),
  }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
        <XAxis dataKey="turn" tick={{ fill: "#8888a0", fontSize: 10 }} axisLine={{ stroke: "#2a2a3a" }} tickLine={false} />
        <YAxis tick={{ fill: "#8888a0", fontSize: 10 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={{ background: "#12121a", border: "1px solid #2a2a3a", borderRadius: 4, fontSize: 11, color: "#e0e0e8" }} />
        <Legend wrapperStyle={{ fontSize: 10, color: "#8888a0" }} />
        <Line type="monotone" dataKey="mana" stroke="#60a5fa" strokeWidth={1.5} dot={false} name="mana" />
        <Line type="monotone" dataKey="lands" stroke="#4ade80" strokeWidth={1.5} dot={false} name="lands" />
        <Line type="monotone" dataKey="creatures" stroke="#facc15" strokeWidth={1.5} dot={false} name="creatures" />
        <Line type="monotone" dataKey="power" stroke="#f87171" strokeWidth={1.5} dot={false} name="power" />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function GameSimChart({ turnData, gamesSimulated }: Props) {
  const [tab, setTab] = useState<Tab>("overview");

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "insights" },
    { key: "mana", label: "mana" },
    { key: "board", label: "board" },
    { key: "colors", label: "colors" },
    { key: "chart", label: "chart" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xxs text-text-muted uppercase tracking-wider">
          Simulation
        </span>
        <span className="text-xxs text-text-muted">{gamesSimulated} games</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-0.5 bg-bg-primary rounded p-0.5 mb-3">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 px-1.5 py-1 text-xxs rounded transition-colors ${
              tab === t.key
                ? "bg-bg-tertiary text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab turnData={turnData} />}
      {tab === "mana" && <ManaTab turnData={turnData} />}
      {tab === "board" && <BoardTab turnData={turnData} />}
      {tab === "colors" && <ColorsTab turnData={turnData} />}
      {tab === "chart" && <ChartView turnData={turnData} />}
    </div>
  );
}