"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Navbar from "@/components/navbar";
import { useState } from "react";
import { useAnalysis } from "@/context/AnalysisContext";
import toast from "react-hot-toast";

export default function AnalyzePage() {
  const router = useRouter();
  const { setResult } = useAnalysis();
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Analyzing...");
  const [compoundName, setCompoundName] = useState("");

  const handlePrioritize = async () => {
    console.log("Prioritizing compound:", compoundName);

    if (!compoundName.trim()) {
      toast.error("Please enter a compound name.");
      return;
    }
    setIsLoading(true);
    setLoadingMessage("Fetching data and running analysis...");

    try {
      console.log("Calling backend:", process.env.NEXT_PUBLIC_BACKEND_URL);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            compound_name: compoundName,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to analyze compound");
      }

      const data = await response.json();
      console.log("Analysis result:", data);
      setResult({
        compound_prioritization: {
          result: {
            confidence: data.compound_prioritization.result.confidence,
            priority_score: data.compound_prioritization.result.priority_score,
            reasoning: data.compound_prioritization.result.reasoning,
          },
          sub_agents: {
            cf_efficacy: {
              result: {
                confidence: data.compound_prioritization.sub_agents.cf_efficacy.result.confidence,
                predicted_efficacy: data.compound_prioritization.sub_agents.cf_efficacy.result.predicted_efficacy,
                reasoning: data.compound_prioritization.sub_agents.cf_efficacy.result.reasoning,
                trajectory: data.compound_prioritization.sub_agents.cf_efficacy.result.trajectory,
              }
            },
            toxicity_screening: {
              result: {
                confidence: data.compound_prioritization.sub_agents.toxicity_screening.result.confidence,
                percent_remaining_cells: data.compound_prioritization.sub_agents.toxicity_screening.result.percent_remaining_cells,
                reasoning: data.compound_prioritization.sub_agents.toxicity_screening.result.reasoning,
                trajectory: data.compound_prioritization.sub_agents.toxicity_screening.result.trajectory,
              }
            }
          }
        }
      });

      router.push("/analyze/result");
    } catch (error) {
      console.error("Error analyzing compound:", error);
      let errorMessage = "An unexpected error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      toast.error(`Analysis Failed: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 p-8 text-gray-100">
      <Navbar />

      <div className="mx-auto max-w-2xl rounded-md bg-white p-8 text-gray-900 shadow-md">
        <h2 className="mb-4 text-xl font-semibold">
          Prioritize Compound for Cardiac Fibrosis Reversal Screening
        </h2>

        <div className="space-y-4">
          <div>
            <Label htmlFor="compound-name" className="mb-1 block font-semibold">
              Compound Name
            </Label>
            <Input
              id="compound-name"
              placeholder="Enter compound name (e.g., Givinostat)"
              className="mt-1"
              value={compoundName}
              onChange={(e) => setCompoundName(e.target.value)}
            />
          </div>

          <div className="flex justify-end">
            <Button
              className="mt-4"
              onClick={handlePrioritize}
              disabled={isLoading || !compoundName}
            >
              {isLoading ? loadingMessage : "Prioritize Compound"}
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}
