"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import toast from "react-hot-toast";

export default function WaitlistPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      toast.error("Please enter a valid email address");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          timestamp: new Date().toISOString(),
          source: "waitlist_page",
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to submit");
      }

      toast.success("Thanks for joining the waitlist! We'll be in touch soon.");
      setEmail("");
    } catch {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Biotech MCP Servers
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            High-performance chemical and bioactivity data APIs powered by
            ChEMBL and PubChem databases. Built for researchers, developers, and
            biotech companies.
          </p>
        </div>

        {/* MCP Servers Grid */}
        <div className="grid md:grid-cols-2 gap-8 mb-16">
          {/* ChEMBL MCP Server */}
          <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-200">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">C</span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 ml-4">
                ChEMBL MCP Server
              </h3>
            </div>
            <p className="text-gray-600 mb-6">
              Access the world&apos;s largest open bioactivity database with
              comprehensive compound information, bioactivities, drug
              mechanisms, and target data.
            </p>
            <div className="space-y-3">
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-3"></span>
                Search compounds by name, synonym, or ChEMBL ID
              </div>
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-3"></span>
                Retrieve bioactivity data with filtering options
              </div>
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-3"></span>
                Access drug mechanisms of action and indications
              </div>
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-3"></span>
                Target information and active compounds data
              </div>
            </div>
          </div>

          {/* PubChem MCP Server */}
          <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-200">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">P</span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 ml-4">
                PubChem MCP Server
              </h3>
            </div>
            <p className="text-gray-600 mb-6">
              Comprehensive chemical information and structure analysis from the
              world&apos;s largest collection of freely accessible chemical
              data.
            </p>
            <div className="space-y-3">
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                Search by SMILES, InChI, CAS numbers, and names
              </div>
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                Similarity and substructure searching
              </div>
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                3D conformer analysis and stereochemistry
              </div>
              <div className="flex items-center text-sm text-gray-700">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                Safety, toxicity, and bioassay data
              </div>
            </div>
          </div>
        </div>

        {/* API Features */}
        <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-200 mb-16">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Enterprise-Ready API Features
          </h3>
          <div className="grid md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🚀</span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">
                High Performance
              </h4>
              <p className="text-sm text-gray-600">
                Optimized for speed with async processing
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🔒</span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">
                Secure & Reliable
              </h4>
              <p className="text-sm text-gray-600">
                Enterprise-grade security and uptime
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">📊</span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Rich Data</h4>
              <p className="text-sm text-gray-600">
                Comprehensive chemical and bioactivity data
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">⚡</span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">
                Easy Integration
              </h4>
              <p className="text-sm text-gray-600">
                RESTful API with comprehensive docs
              </p>
            </div>
          </div>
        </div>

        {/* Waitlist Form */}
        <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-8 border border-gray-200">
          <div className="text-center mb-6">
            <h3 className="text-2xl font-bold text-gray-900 mb-2">
              Join the Early Access Waitlist
            </h3>
            <p className="text-gray-600">
              Be the first to access our premium biotech MCP servers with custom
              rate limits and priority support.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label
                htmlFor="email"
                className="text-sm font-medium text-gray-700"
              >
                Email Address
              </Label>
              <Input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@company.com"
                className="mt-1"
                required
              />
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
            >
              {isSubmitting ? "Joining..." : "Join Waitlist"}
            </Button>
          </form>

          <p className="text-xs text-gray-500 text-center mt-4">
            We&apos;ll never share your email and you can unsubscribe at any
            time.
          </p>
        </div>

        {/* Footer */}
        <div className="text-center mt-16 pt-8 border-t border-gray-200">
          <p className="text-gray-600">
            Built with ❤️ for the biotech research community
          </p>
          <p className="text-sm text-gray-500 mt-2">
            API Base URL:{" "}
            <code className="bg-gray-100 px-2 py-1 rounded">
              https://birdhouse--biotech-mcp-servers-biotech-mcp-api.modal.run
            </code>
          </p>
        </div>
      </div>
    </div>
  );
}
