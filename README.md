# cf-compound-selection-demo

Demo for the agentic AI system to select cardiac fibrosis compounds!

## Overview

This repository contains an agentic AI system for compound prioritization in cardiac fibrosis drug discovery. The system uses multiple specialized agents that work together to assess compound efficacy and toxicity, ultimately prioritizing candidates for experimental validation.

Fibrolytix aims to incoporate proprietary assay data from our [SOTA phenotypic screen](https://www.ahajournals.org/doi/full/10.1161/CIRCULATIONAHA.124.071956) that can measure a compound's efficacy for reversing cardiac fibrosis. Long-term, we envision a lab-in-the-loop (LITL) agent that can reference previous agent predictions and assay results to learn how the two are related.

## Compound Nomination Agent

The primary goal of this system is to **predict the efficacy of compounds in reversing the failing cardiac fibroblast phenotype** using a custom Cell Painting + ML readout assay. The system evaluates compounds in a hierarchical agent structure:

- **CF Efficacy Agent**: Predicts compound efficacy (0-1 scale) for reversing failing cardiac fibroblasts to a nonfailing/quiescent-like state
- **Toxicity Screening Agent**: Estimates the percentage of cells remaining after compound treatment to assess cytotoxicity
- **Compound Prioritization Agent**: Coordinates the sub-agents and generates an overall priority score combining efficacy and safety profiles

The assay context: 10 µM compound (in DMSO) applied to failing primary human ventricular fibroblasts for 72 hours, with multiplexed Cell Painting imaging and ML-based classification to score each cell's predicted nonfailing probability ([Travers et al., 2025](https://www.ahajournals.org/doi/full/10.1161/CIRCULATIONAHA.124.071956))

## Architecture

This system leverages [DSPy](https://dspy.ai/) for its modular, trainable, and evaluatable architecture:

- **Modular Design**: Each agent is a `dspy.Module` with clearly defined signatures specifying inputs, outputs, and task descriptions
- **ReAct Pattern**: The efficacy and toxicity agents use `dspy.ReAct` (Reasoning + Acting) to iteratively gather information through tool calls and refine predictions
- **Chain-of-Thought**: The prioritization coordinator uses `dspy.ChainOfThought` to synthesize information from sub-agents
- **Trainable**: DSPy's signature-based approach enables optimization of prompts and agent behavior through systematic evaluation
- **Evaluatable**: Structured outputs (predicted efficacy, confidence scores) enable quantitative assessment of agent performance

The hierarchical structure allows for both independent agent evaluation and holistic system assessment.

## Language Models

The system primarily uses **Google Gemini models**:

- **Gemini 2.5 Pro**: Used for complex reasoning tasks including agent runs, previous run reflections, and LITL reasoning
- **Gemini 2.5 Flash Lite**: Used where complex reasoning is not required including summarizing API outputs and agent runs.

We also experimented with **Grok models**, which seem significantly better at following sepcific instructions and have a 2M token context window.

## Tools

The agents have access to specialized tools organized into four categories:

### PubChem Tools
16 tools for chemical property and bioactivity data. More info at [backend/agentic_system/tools/pubchem_tools.py](backend/agentic_system/tools/pubchem_tools.py).

### ChEMBL Tools
12 tools for curated bioactivity and drug development data. More info at [backend/agentic_system/tools/chembl_tools.py](backend/agentic_system/tools/chembl_tools.py).

### Search Tools
Web and literature information:
- **Web Search**: Tavily-powered web search with relevance scoring and content extraction
- **PubMed Search**: Scientific literature search with abstract retrieval, date filtering, and relevance sorting
More info at [backend/agentic_system/tools/search_tools.py](backend/agentic_system/tools/search_tools.py).

### LITL Tools (Lab-in-the-Loop)
Experimental data from previous assay runs:
- **Efficacy Reasoning**: Identify similar compounds from past screens and provide detailed mechanistic comparisons
- **Get All Compounds**: Retrieve full dataset of screened compounds with efficacy scores
- **Get Runs**: Access complete past agent trajectories for specific reference compounds
- **RAG Query**: Semantic search over past agent runs to learn from previous successes and failures
More info at [backend/agentic_system/tools/litl_tools.py](backend/agentic_system/tools/litl_tools.py).

Tool notes:
- All tools implement caching and rate limiting to ensure efficient and responsible API usage.
- Pubchem, ChemBL, and Search tools are wrapped with `ai_summarized_output`, which will add an additional `goal` param to each tool call (for the intended information the agent wants when calling this tool) and translates each raw API result into output relevant to this goal with a simple DSPy module. We have found that this reduces agent token usage (and cost) by about 50% and makes the tool results much more human-readable.

## Results

Our current proprietary assay results include efficacy and toxicity (percent of cells remaining after applying compound) measurements for 50 compounds. We only thoroughly evaluate the efficacy predictions. 8 out of these 50 compounds had less than 20% of cells remaining, our cutoff for useful efficacy data. Thus, we have about 42 compound efficacy results we can use to evaluate our system.

We evaluate 3 efficay agents for efficacy accuracy:
- Gemini (No LITL): Gemini 2.5 Pro model without any LITL tools.
- Gemini (LITL): Gemini 2.5 Pro model with LITL tools.
- Grok (LITL): Grok 4 fast reasoning model with LITL tools.

**None of these agents performed significantly better than a random baseline for predicting compound efficacy.**

![alt text](image.png)
