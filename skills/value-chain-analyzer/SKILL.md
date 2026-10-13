---
name: value-chain-analyzer
description: A comprehensive skill for analyzing industry value chains. Use when the user asks about the structure of an industry, the value chain of a specific sector, key players in an industry, or how a specific product/technology is made. This skill guides the systematic breakdown of industries into upstream, midstream, and downstream components, identifying key materials, components, and players.
version: 1.3.0
allowed-tools: run_command search_web read_url_content
---

# Value Chain Analyzer

## Overview

The Value Chain Analyzer provides a structured methodology for breaking down any industry or technology into its component parts. It helps identify the complete ecosystem from raw materials to end products, including key components, manufacturing processes, economic moats (경제적 해자), and major bottleneck companies operating at each stage.

## When to Use

Trigger this skill when the user asks questions like:
- "What is the value chain of the [X] industry?"
- "Who are the key players in the [X] market?"
- "What components are needed to build [X]?"
- "Analyze the ecosystem of [X]."

## Core Workflow

Follow these steps to conduct a comprehensive value chain analysis:

### Step 1: Define the Industry Scope and Core Product
1. Clearly define the industry or technology being analyzed (e.g., Physical AI/Robotics, Electric Vehicles, Semiconductor).
2. Identify the core product or service that represents the final output of this industry.
3. Establish the boundaries of the analysis (what is included and excluded).

### Step 2: Structure the Value Chain
Break the industry down into logical stages. The standard model is:
- **Upstream (Raw Materials & Basic Components):** Foundational materials and basic parts.
- **Midstream (Sub-assemblies & Core Modules):** Complex components and systems built from upstream parts.
- **Downstream (Final Assembly & Application):** The finished product and its end-use applications.

*Note: Adapt this structure to fit the specific industry. For example, software might be structured as Infrastructure -> Platform -> Application.*

### Step 3: Deep Dive and Research each Stage
1. Use `search_web` or browser capabilities to search for the latest market data, industry studies, corporate news, and official specifications.
2. For each stage identified in Step 2, determine:
   - **Key Components/Processes:** What exactly is being made or done here?
   - **Technological Importance:** Why is this step critical? What are the barriers to entry?
   - **Cost/Value Contribution:** What share of the final product's value is created here? Give a percentage only when a source states it (cite it); otherwise describe it qualitatively (e.g., "가장 높은 마진 구간").
3. **CRITICAL**: For every piece of information or statistic you find, collect the exact webpage title and URL. You will need these for references.

### Step 4: Identify Key Players (Market Mapping)
For the most critical components identified in Step 3:
1. Search the web to identify the dominant companies globally and domestically.
2. Note their market share or relative market position if available.
3. Distinguish between pure-play companies and diversified conglomerates.
4. Identify critical bottlenecks/choke points (components dominated by a few players or having high barriers to entry/pricing power).
5. Collect the source URLs and titles for these findings.

### Step 5: Synthesize and Present Findings (With Citations & Diagram)
1. Run the python script `scripts/generate_mermaid.py` using the project virtual environment to generate a professional, Left-to-Right diagram with subgraphs representing the value chain stages. Match the output language of the report (e.g., use `--lang ko` if the report is in Korean, or `--lang en` if in English):
   ```bash
   venv/bin/python3 .agents/skills/value-chain-analyzer/scripts/generate_mermaid.py --industry "[Industry Name]" --upstream "[U1, U2]" --midstream "[M1, M2]" --downstream "[D1, D2]" --lang ko
   ```
   - Items are separated by commas, so do not put a comma inside an item name (use `·` instead). Double quotes inside an item are converted to single quotes.
   - When the diagram feeds an investment report, tag nodes with roles (`[타겟]`, `[직접경쟁]`, `[병목협력]`). If a company plays two roles relative to the target (e.g., a bottleneck partner that also competes with one of the target's divisions), show both (`[병목협력·경쟁]`).
2. Structure the final report using the template provided in `templates/report_template.md`.
3. Populate the report sections using your findings. Add inline citation tags (e.g., `[1]`, `[2]`) in the body text next to any key claims, market shares, or cost figures.
4. At the bottom of the report, create a `## References` section listing all collected sources as clickable markdown links (e.g. `[1] [Source Title](URL) - Description`).

## Best Practices for Analysis

- **Focus on the Bottlenecks:** Every value chain has "choke points" (components that are hard to make, dominated by a few players, or highly profitable). Highlight these. For example, in robotics, precision reducers and high-end servo motors are choke points.
- **Differentiate by Quality/Tier:** Note if the market is segmented (e.g., high-end vs. low-end components).
- **Follow the Money:** Try to identify which part of the value chain captures the most margin.
- **Use Web Search and Browsing actively:** Always run search queries to verify market shares and statistics; do not rely on pre-trained knowledge for current numbers.

## Resources

- **`templates/report_template.md`**: Use this template to structure the final report delivered to the user.
- **`scripts/generate_mermaid.py`**: A helper script to generate a Mermaid.js diagram of the value chain for visual presentation.
