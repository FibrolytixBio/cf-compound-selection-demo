"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface Trajectory {
  [key: `thought_${number}`]: string;
  [key: `tool_name_${number}`]: string;
  [key: `tool_args_${number}`]: object;
  [key: `observation_${number}`]: string;
}

interface CompoundPrioritizationResult {
  confidence: number;
  priority_score: number;
  reasoning: string;
}

interface CfEfficacyResult {
  confidence: number;
  predicted_efficacy: number;
  reasoning: string;
  trajectory: Trajectory;
}

interface ToxicityScreeningResult {
  confidence: number;
  percent_remaining_cells: number;
  reasoning: string;
  trajectory: Trajectory;
}

interface AnalysisResult {
  compound_prioritization: {
    result: CompoundPrioritizationResult;
    sub_agents: {
      cf_efficacy: {
        result: CfEfficacyResult;
      };
      toxicity_screening: {
        result: ToxicityScreeningResult;
      };
    };
  };
}

interface AnalysisContextType {
  result: AnalysisResult | null;
  setResult: (result: AnalysisResult) => void;
  clearResult: () => void;
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(
  undefined
);

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const clearResult = () => {
    setResult(null);
  };

  return (
    <AnalysisContext.Provider value={{ result, setResult, clearResult }}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (context === undefined) {
    throw new Error("useAnalysis must be used within an AnalysisProvider");
  }
  return context;
}
