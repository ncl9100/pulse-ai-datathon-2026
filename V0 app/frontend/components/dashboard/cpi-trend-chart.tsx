"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

interface CPITrendData {
  period: string;
  cpi: number;
}

interface CPITrendChartProps {
  data: CPITrendData[];
  currentCPI: number;
}

export function CPITrendChart({ data, currentCPI }: CPITrendChartProps) {
  // If no trend data, show current CPI as a single point
  const chartData = data.length > 0 ? data : [{ period: "Current", cpi: currentCPI }];

  return (
    <div className="h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" tick={{ fontSize: 11 }} />
          <YAxis domain={[0.5, 1.5]} tick={{ fontSize: 11 }} tickFormatter={(v) => v.toFixed(2)} />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "6px",
              fontSize: "12px",
            }}
            formatter={(value: number) => [value.toFixed(3), "CPI"]}
          />
          <ReferenceLine y={1} stroke="#22c55e" strokeDasharray="3 3" label={{ value: "Target", fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="cpi"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 4, fill: "#3b82f6" }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
