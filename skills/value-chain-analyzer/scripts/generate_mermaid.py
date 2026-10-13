#!/usr/bin/env python3
import argparse
import sys

def generate_mermaid(industry_name, upstream_items, midstream_items, downstream_items, lang="en"):
    """
    Generates a professional Mermaid flowchart for a value chain.
    """
    # Labels based on language
    if lang == "ko":
        up_label = "상류 (Upstream: 원자재/기초소재)"
        mid_label = "중류 (Midstream: 핵심부품/모듈)"
        down_label = "하류 (Downstream: 완제품/애플리케이션)"
    else:
        up_label = "Upstream: Materials & Basics"
        mid_label = "Midstream: Components & Modules"
        down_label = "Downstream: Final Assembly & Applications"

    mermaid_code = f"```mermaid\n"
    mermaid_code += f"graph LR\n"
    mermaid_code += f"    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px;\n"
    mermaid_code += f"    classDef upstream fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;\n"
    mermaid_code += f"    classDef midstream fill:#fff3e0,stroke:#f57c00,stroke-width:2px;\n"
    mermaid_code += f"    classDef downstream fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;\n"
    mermaid_code += f"    classDef target fill:#ffebee,stroke:#d32f2f,stroke-width:3px,font-weight:bold;\n"
    mermaid_code += f"    classDef peer fill:#fff8e1,stroke:#f57f17,stroke-width:2px;\n"
    mermaid_code += f"    classDef bottleneck fill:#ede7f6,stroke:#512da8,stroke-width:2px;\n\n"
    
    def get_item_class(item, default_class):
        # Match tag prefixes so combined roles such as "[병목협력·경쟁]" keep their colour
        if "[타겟" in item or "[Target" in item:
            return "target"
        elif "[병목협력" in item or "[Bottleneck" in item:
            return "bottleneck"
        elif "[직접경쟁" in item or "[Peer" in item:
            return "peer"
        return default_class

    # Subgraph for Upstream
    mermaid_code += f"    subgraph U [\"{up_label}\"]\n"
    for i, item in enumerate(upstream_items):
        cls = get_item_class(item, "upstream")
        mermaid_code += f"        U{i}(\"{item}\"):::{cls}\n"
    mermaid_code += f"    end\n\n"

    # Subgraph for Midstream
    mermaid_code += f"    subgraph M [\"{mid_label}\"]\n"
    for i, item in enumerate(midstream_items):
        cls = get_item_class(item, "midstream")
        mermaid_code += f"        M{i}(\"{item}\"):::{cls}\n"
    mermaid_code += f"    end\n\n"

    # Subgraph for Downstream
    mermaid_code += f"    subgraph D [\"{down_label}\"]\n"
    for i, item in enumerate(downstream_items):
        cls = get_item_class(item, "downstream")
        mermaid_code += f"        D{i}(\"{item}\"):::{cls}\n"
    mermaid_code += f"    end\n\n"
    
    # Connections between subgraphs
    mermaid_code += f"    U --> M\n"
    mermaid_code += f"    M --> D\n"
    
    mermaid_code += f"```\n"
    
    return mermaid_code

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Mermaid diagram for a value chain.")
    parser.add_argument("--industry", type=str, required=True, help="Name of the industry")
    parser.add_argument("--upstream", type=str, required=True, help="Comma-separated list of upstream components")
    parser.add_argument("--midstream", type=str, required=True, help="Comma-separated list of midstream components")
    parser.add_argument("--downstream", type=str, required=True, help="Comma-separated list of downstream components")
    parser.add_argument("--lang", type=str, choices=["en", "ko"], default="en", help="Language for subgraph labels (en or ko)")
    
    args = parser.parse_args()
    
    def parse_items(text):
        # A double quote would close the Mermaid node label early, so swap it for a single quote
        return [item.strip().replace('"', "'") for item in text.split(',') if item.strip()]

    up = parse_items(args.upstream)
    mid = parse_items(args.midstream)
    down = parse_items(args.downstream)
    
    result = generate_mermaid(args.industry, up, mid, down, args.lang)
    print(result)
