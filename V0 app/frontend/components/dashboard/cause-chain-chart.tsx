"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface CauseChainData {
  chain_a_design_rework: number;
  chain_b_material_idle: number;
  chain_c_rfi_standby: number;
  chain_d_rejected_co_loss: number;
  chain_e_early_co_signals: number;
}

interface CauseChainChartProps {
  data: CauseChainData;
}

const CHAIN_COLORS = {
  chain_a_design_rework: "#ef4444",
  chain_b_material_idle: "#f97316",
  chain_c_rfi_standby: "#eab308",
  chain_d_rejected_co_loss: "#3b82f6",
  chain_e_early_co_signals: "#8b5cf6",
};

const CHAIN_LABELS = {
  chain_a_design_rework: "Design Rework",
  chain_b_material_idle: "Material Idle",
  chain_c_rfi_standby: "RFI Standby",
  chain_d_rejected_co_loss: "Rejected CO Loss",
  chain_e_early_co_signals: "Early CO Signals",
};

export function CauseChainChart({ data }: CauseChainChartProps) {
  const chartData = [
    {
      name: "Risk Drivers",
      "Design Rework": data.chain_a_design_rework || 0,
      "Material Idle": data.chain_b_material_idle || 0,
      "RFI Standby": data.chain_c_rfi_standby || 0,
      "Rejected CO Loss": data.chain_d_rejected_co_loss || 0,
      "Early CO Signals": data.chain_e_early_co_signals || 0,
    },
  ];

  return (
    <div className="h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <YAxis dataKey="name" type="category" hide />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "6px",
              fontSize: "12px",
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, ""]}
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
          <Bar dataKey="Design Rework" stackId="a" fill={CHAIN_COLORS.chain_a_design_rework} />
          <Bar dataKey="Material Idle" stackId="a" fill={CHAIN_COLORS.chain_b_material_idle} />
          <Bar dataKey="RFI Standby" stackId="a" fill={CHAIN_COLORS.chain_c_rfi_standby} />
          <Bar dataKey="Rejected CO Loss" stackId="a" fill={CHAIN_COLORS.chain_d_rejected_co_loss} />
          <Bar dataKey="Early CO Signals" stackId="a" fill={CHAIN_COLORS.chain_e_early_co_signals} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
