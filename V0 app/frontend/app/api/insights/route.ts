import { generateText, Output } from "ai";
import { z } from "zod";

// Schema for the AI insights response
const insightsSchema = z.object({
  risk_summary: z.string().describe("A 2-3 sentence explanation of why this project is at risk"),
  root_causes: z.array(z.string()).describe("Top 3-5 root causes driving margin erosion"),
  recovery_actions: z.array(
    z.object({
      action: z.string().describe("Specific, actionable recommendation"),
      estimated_impact: z.string().describe("Dollar amount or percentage impact estimate"),
    })
  ).describe("3-5 specific recovery recommendations with estimated dollar impact"),
});

// Simple in-memory cache for insights
const insightsCache = new Map<string, { data: z.infer<typeof insightsSchema>; timestamp: number }>();
const CACHE_TTL = 1000 * 60 * 30; // 30 minutes

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const {
      project_id,
      risk_score,
      risk_category,
      cpi,
      early_rfi_count,
      early_ot_ratio_pct,
      variance_at_completion,
      cause_chain,
    } = body;

    // Check cache first
    const cacheKey = `${project_id}-${risk_score}-${cpi}`;
    const cached = insightsCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return Response.json(cached.data);
    }

    // Build context about the project
    const projectContext = `
Project: ${project_id}
Risk Score: ${risk_score}/100 (${risk_category})
Cost Performance Index (CPI): ${cpi} ${cpi < 1 ? "(Under budget performance - costs exceeding earned value)" : "(On or above target)"}
Early RFI Count: ${early_rfi_count} ${early_rfi_count > 10 ? "(High - indicates design uncertainty)" : early_rfi_count > 5 ? "(Moderate)" : "(Low)"}
Overtime Ratio: ${early_ot_ratio_pct}% ${early_ot_ratio_pct > 20 ? "(High - schedule pressure)" : early_ot_ratio_pct > 10 ? "(Moderate)" : "(Low)"}
${variance_at_completion ? `Variance at Completion: $${variance_at_completion.toLocaleString()} ${variance_at_completion < 0 ? "(Projected loss)" : "(Projected gain)"}` : ""}

${cause_chain ? `
Risk Driver Breakdown:
- Design Rework Chain: ${cause_chain.chain_a_design_rework}%
- Material Idle Chain: ${cause_chain.chain_b_material_idle}%
- RFI Standby Chain: ${cause_chain.chain_c_rfi_standby}%
- Rejected CO Loss Chain: ${cause_chain.chain_d_rejected_co_loss}%
- Early CO Signals Chain: ${cause_chain.chain_e_early_co_signals}%
` : ""}
`.trim();

    const { output } = await generateText({
      model: "anthropic/claude-sonnet-4.6",
      output: Output.object({
        schema: insightsSchema,
      }),
      messages: [
        {
          role: "system",
          content: `You are an HVAC construction project analyst specializing in margin risk assessment and recovery. 
Your role is to analyze project metrics and provide actionable insights.

Key metrics to consider:
- CPI < 1.0 indicates cost overruns (earned value is less than actual costs)
- High early RFI counts suggest design documentation issues
- High overtime ratios indicate schedule pressure and potential burnout
- Negative variance at completion means projected losses

When providing recovery actions, give specific dollar estimates based on typical HVAC project economics:
- Labor cost reduction opportunities typically range $5,000-$50,000
- Material optimization can save 3-8% of material costs
- Change order management improvements can recover $10,000-$100,000
- Schedule optimization can prevent $2,000-$10,000 per week in overtime

Be specific and quantitative in your recommendations.`,
        },
        {
          role: "user",
          content: `Analyze this HVAC project and provide risk insights:

${projectContext}

Provide a concise risk summary, identify root causes, and recommend specific recovery actions with dollar-quantified impact estimates.`,
        },
      ],
    });

    if (!output) {
      throw new Error("Failed to generate insights");
    }

    // Cache the result
    insightsCache.set(cacheKey, { data: output, timestamp: Date.now() });

    return Response.json(output);
  } catch (error) {
    console.error("Error generating insights:", error);
    
    // Return a fallback response
    return Response.json({
      risk_summary: "Unable to generate AI analysis at this time. The project shows concerning metrics that warrant attention.",
      root_causes: [
        "CPI below target indicates cost overruns",
        "Review RFI patterns for design documentation issues",
        "Monitor overtime trends for schedule pressure",
      ],
      recovery_actions: [
        { action: "Conduct detailed cost variance analysis", estimated_impact: "$10,000 - $25,000" },
        { action: "Review and optimize labor allocation", estimated_impact: "$15,000 - $40,000" },
        { action: "Accelerate pending change order approvals", estimated_impact: "$20,000 - $50,000" },
      ],
    });
  }
}
