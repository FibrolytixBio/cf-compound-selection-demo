"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Navbar from "@/components/navbar";
import { useState, useEffect } from "react";
import { useAnalysis } from "@/context/AnalysisContext";
import toast from "react-hot-toast";

export default function AnalyzePage() {
  const router = useRouter();
  const { setResult } = useAnalysis();
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Analyzing...");
  const [compoundName, setCompoundName] = useState("");
  const [elapsedTime, setElapsedTime] = useState(0);

  // Timer effect for loading progress
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isLoading) {
      const startTime = Date.now();
      interval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setElapsedTime(elapsed);
        
        if (elapsed < 60) {
          setLoadingMessage(`Running analysis... ${elapsed}s elapsed (usually takes ~3 minutes)`);
        } else {
          const minutes = Math.floor(elapsed / 60);
          const seconds = elapsed % 60;
          setLoadingMessage(`Running analysis... ${minutes}m ${seconds}s elapsed (usually takes ~3 minutes)`);
        }
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLoading]);

  const handlePrioritize = async () => {
    console.log("Prioritizing compound:", compoundName);

    if (!compoundName.trim()) {
      toast.error("Please enter a compound name.");
      return;
    }
    setIsLoading(true);

    try {
      // Create AbortController with a 5-minute timeout (300 seconds)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000);

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
          signal: controller.signal,
        }
      );

      clearTimeout(timeoutId);

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
        if (error.name === 'AbortError') {
          errorMessage = "Analysis timed out after 5 minutes. Please try again.";
        } else if (error.message.includes('fetch')) {
          errorMessage = "Network error: Unable to connect to the analysis service.";
        } else {
          errorMessage = error.message;
        }
      }
      
      toast.error(`Analysis Failed: ${errorMessage}`);
    } finally {
      setIsLoading(false);
      setElapsedTime(0);
      setLoadingMessage("Analyzing...");
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
