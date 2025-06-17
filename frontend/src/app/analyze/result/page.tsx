"use client";

import { useAnalysis } from "@/context/AnalysisContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Navbar from "@/components/navbar";

export default function ResultPage() {
  const { result } = useAnalysis();
  const router = useRouter();

  useEffect(() => {
    if (!result) {
      router.push("/analyze");
    }
  }, [result, router]);

  if (!result) {
    return <div>Loading...</div>;
  }

  return (
    <main className="min-h-screen bg-gray-900 p-8 text-gray-100">
      <Navbar />
      
      <div className="mx-auto max-w-4xl rounded-md bg-white p-8 text-gray-900 shadow-md">
        <ResultContent result={result} />
      </div>
    </main>
  );
}

function ResultContent({ result }) {
  const [selectedTrajectory, setSelectedTrajectory] = useState(null);

  const compoundResult = result.compound_prioritization.result;
  const efficacyResult = result.compound_prioritization.sub_agents.cf_efficacy.result;
  const toxicityResult = result.compound_prioritization.sub_agents.toxicity_screening.result;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Analysis Results</h1>
      
      {/* Compound Prioritization Section */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-700 mb-3">Compound Prioritization Agent</h2>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <span className="font-medium">Priority Score:</span> {compoundResult.priority_score}
            </div>
            <div>
              <span className="font-medium">Confidence:</span> {compoundResult.confidence}
            </div>
          </div>
          <div>
            <span className="font-medium">Reasoning:</span>
            <p className="mt-1 text-gray-600">{compoundResult.reasoning}</p>
          </div>
        </div>
      </div>

      {/* CF Efficacy Section */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-700 mb-3">CF Efficacy Subagent</h2>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <span className="font-medium">Predicted Efficacy:</span> {efficacyResult.predicted_efficacy}
            </div>
            <div>
              <span className="font-medium">Confidence:</span> {efficacyResult.confidence}
            </div>
          </div>
          <div className="mb-3">
            <span className="font-medium">Reasoning:</span>
            <p className="mt-1 text-gray-600">{efficacyResult.reasoning}</p>
          </div>
          {efficacyResult.trajectory && (
            <button
              onClick={() => setSelectedTrajectory(efficacyResult.trajectory)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded text-sm"
            >
              See Trajectory
            </button>
          )}
        </div>
      </div>

      {/* Toxicity Screening Section */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-700 mb-3">Toxicity Screening Subagent</h2>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <span className="font-medium">Percent Remaining Cells:</span> {toxicityResult.percent_remaining_cells}%
            </div>
            <div>
              <span className="font-medium">Confidence:</span> {toxicityResult.confidence}
            </div>
          </div>
          <div className="mb-3">
            <span className="font-medium">Reasoning:</span>
            <p className="mt-1 text-gray-600">{toxicityResult.reasoning}</p>
          </div>
          {toxicityResult.trajectory && (
            <button
              onClick={() => setSelectedTrajectory(toxicityResult.trajectory)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded text-sm"
            >
              See Trajectory
            </button>
          )}
        </div>
      </div>

      {/* Trajectory Modal */}
      {selectedTrajectory && (
        <TrajectoryModal 
          trajectory={selectedTrajectory} 
          onClose={() => setSelectedTrajectory(null)} 
        />
      )}
    </div>
  );
}

function TrajectoryModal({ trajectory, onClose }) {
  // Function to parse observation strings
  const parseTrajectoryData = (trajectory) => {
    const parsed = { ...trajectory };
    
    // Find all observation keys and parse their values
    Object.keys(parsed).forEach(key => {
      if (key.startsWith('observation_')) {
        try {
          // Remove escape characters and parse newlines
          const value = parsed[key];
          if (typeof value === 'string') {
            const cleanedValue = value
              .replace(/\\"/g, '"')  // Remove escaped quotes
              .replace(/\\n/g, '\n'); // Convert \n to actual newlines
            
            // Try to parse as JSON if it looks like JSON
            if (cleanedValue.trim().startsWith('{') || cleanedValue.trim().startsWith('[')) {
              parsed[key] = JSON.parse(cleanedValue);
            } else {
              parsed[key] = cleanedValue;
            }
          }
        } catch {
          // If parsing fails, just clean the string
          const value = parsed[key];
          if (typeof value === 'string') {
            parsed[key] = value
              .replace(/\\"/g, '"')
              .replace(/\\n/g, '\n');
          }
        }
      }
    });
    
    return parsed;
  };

  const parsedTrajectory = parseTrajectoryData(trajectory);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-6xl w-full max-h-[80vh] overflow-hidden">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="text-lg font-semibold">Agent Trajectory</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-xl"
          >
            ×
          </button>
        </div>
        <div className="p-4 overflow-auto max-h-[60vh]">
          <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded">
            {JSON.stringify(parsedTrajectory, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}