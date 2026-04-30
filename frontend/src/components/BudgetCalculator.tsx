import { useState } from "react";

const DESTINATIONS = [
  "Bali", "Bangkok", "Lisbon", "Queenstown",
  "Florence", "Kyoto", "Santorini", "Dubai",
  "Maldives", "Patagonia",
];

type CostEntry = { accommodation: number; food: number; activities: number; transport: number };
type StyleKey = "budget" | "moderate" | "luxury";

const DAILY_COSTS: Record<StyleKey, Record<string, CostEntry>> = {
  budget: {
    Bali:        { accommodation: 18,  food: 10,  activities: 12, transport: 5  },
    Bangkok:     { accommodation: 15,  food: 8,   activities: 8,  transport: 4  },
    Lisbon:      { accommodation: 35,  food: 20,  activities: 10, transport: 8  },
    Queenstown:  { accommodation: 30,  food: 22,  activities: 20, transport: 12 },
    Florence:    { accommodation: 40,  food: 25,  activities: 15, transport: 10 },
    Kyoto:       { accommodation: 35,  food: 20,  activities: 15, transport: 10 },
    Santorini:   { accommodation: 50,  food: 30,  activities: 15, transport: 12 },
    Dubai:       { accommodation: 60,  food: 25,  activities: 20, transport: 15 },
    Maldives:    { accommodation: 100, food: 40,  activities: 30, transport: 20 },
    Patagonia:   { accommodation: 30,  food: 20,  activities: 15, transport: 20 },
  },
  moderate: {
    Bali:        { accommodation: 60,  food: 25,  activities: 30, transport: 15 },
    Bangkok:     { accommodation: 50,  food: 20,  activities: 20, transport: 10 },
    Lisbon:      { accommodation: 80,  food: 35,  activities: 20, transport: 15 },
    Queenstown:  { accommodation: 90,  food: 40,  activities: 60, transport: 25 },
    Florence:    { accommodation: 100, food: 50,  activities: 30, transport: 15 },
    Kyoto:       { accommodation: 90,  food: 35,  activities: 25, transport: 20 },
    Santorini:   { accommodation: 120, food: 50,  activities: 30, transport: 15 },
    Dubai:       { accommodation: 150, food: 60,  activities: 50, transport: 25 },
    Maldives:    { accommodation: 250, food: 80,  activities: 60, transport: 50 },
    Patagonia:   { accommodation: 80,  food: 35,  activities: 40, transport: 30 },
  },
  luxury: {
    Bali:        { accommodation: 200, food: 80,  activities: 80,  transport: 50  },
    Bangkok:     { accommodation: 180, food: 70,  activities: 60,  transport: 40  },
    Lisbon:      { accommodation: 250, food: 100, activities: 60,  transport: 40  },
    Queenstown:  { accommodation: 300, food: 120, activities: 150, transport: 80  },
    Florence:    { accommodation: 350, food: 150, activities: 80,  transport: 50  },
    Kyoto:       { accommodation: 300, food: 120, activities: 80,  transport: 60  },
    Santorini:   { accommodation: 350, food: 130, activities: 80,  transport: 50  },
    Dubai:       { accommodation: 400, food: 150, activities: 120, transport: 80  },
    Maldives:    { accommodation: 500, food: 180, activities: 100, transport: 120 },
    Patagonia:   { accommodation: 250, food: 100, activities: 120, transport: 80  },
  },
};

function resolveDestination(name: string): string {
  const match = DESTINATIONS.find(
    (d) => d.toLowerCase() === name.toLowerCase() || name.toLowerCase().includes(d.toLowerCase())
  );
  return match ?? DESTINATIONS[0];
}

interface Props {
  defaultDestination?: string;
}

const BREAKDOWN_ITEMS = [
  { label: "Accommodation", icon: "🏨", key: "accommodation" },
  { label: "Food & Drink",  icon: "🍽", key: "food" },
  { label: "Activities",    icon: "🎯", key: "activities" },
  { label: "Transport",     icon: "🚌", key: "transport" },
] as const;

const STYLE_COLORS: Record<StyleKey, { bg: string; text: string; badge: string }> = {
  budget:   { bg: "#f0fdf4", text: "#15803d", badge: "#dcfce7" },
  moderate: { bg: "#eff6ff", text: "#1d4ed8", badge: "#dbeafe" },
  luxury:   { bg: "#fdf4ff", text: "#7e22ce", badge: "#f3e8ff" },
};

export default function BudgetCalculator({ defaultDestination = "" }: Props) {
  const [destination, setDestination] = useState(resolveDestination(defaultDestination));
  const [days, setDays] = useState(7);
  const [people, setPeople] = useState(2);
  const [style, setStyle] = useState<StyleKey>("moderate");

  const costs = DAILY_COSTS[style][destination];
  const daily = costs.accommodation + costs.food + costs.activities + costs.transport;
  const total = daily * days * people;
  const fmt = (n: number) => `$${Math.round(n).toLocaleString()}`;
  const colors = STYLE_COLORS[style];

  return (
    <div className="mt-3 rounded-xl overflow-hidden shadow-sm" style={{ border: "1px solid #e2e8f0" }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between"
           style={{ background: "linear-gradient(135deg, #0f172a, #1e1b4b)" }}>
        <div className="flex items-center gap-2">
          <span className="text-lg">💰</span>
          <span className="text-sm font-semibold text-white">Trip Budget Estimator</span>
        </div>
        <span className="text-xs font-medium rounded-full px-2.5 py-1"
              style={{ background: colors.badge, color: colors.text }}>
          {style.charAt(0).toUpperCase() + style.slice(1)}
        </span>
      </div>

      {/* Controls */}
      <div className="bg-white px-4 py-4">
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="text-xs font-medium text-slate-500 mb-1 block">Destination</label>
            <select
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50"
            >
              {DESTINATIONS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 mb-1 block">Travel Style</label>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value as StyleKey)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50"
            >
              <option value="budget">Budget</option>
              <option value="moderate">Moderate</option>
              <option value="luxury">Luxury</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 mb-1 block">Days</label>
            <input
              type="number" min={1} max={90} value={days}
              onChange={(e) => setDays(Math.max(1, Number(e.target.value)))}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 mb-1 block">Travellers</label>
            <input
              type="number" min={1} max={20} value={people}
              onChange={(e) => setPeople(Math.max(1, Number(e.target.value)))}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50"
            />
          </div>
        </div>

        {/* Breakdown */}
        <div className="rounded-lg px-3 py-3 space-y-2 mb-3" style={{ background: colors.bg }}>
          {BREAKDOWN_ITEMS.map(({ label, icon, key }) => (
            <div key={key} className="flex justify-between items-center text-xs">
              <span className="text-slate-600">{icon} {label}</span>
              <span className="font-semibold" style={{ color: colors.text }}>
                {fmt(costs[key] * people)}<span className="font-normal text-slate-400">/day</span>
              </span>
            </div>
          ))}
          <div className="border-t pt-2 flex justify-between items-center text-xs font-semibold" style={{ borderColor: `${colors.text}22` }}>
            <span className="text-slate-600">Daily total ({people} pax)</span>
            <span style={{ color: colors.text }}>{fmt(daily * people)}</span>
          </div>
        </div>

        {/* Total */}
        <div className="flex items-center justify-between rounded-xl px-4 py-3"
             style={{ background: "linear-gradient(135deg, #0f172a, #1e1b4b)" }}>
          <div>
            <p className="text-xs text-slate-400">{days} days · {people} traveller{people > 1 ? "s" : ""}</p>
            <p className="text-xs text-slate-500 mt-0.5">Rough estimate only</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-400 mb-0.5">Total</p>
            <p className="text-xl font-bold text-white">{fmt(total)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
