# Survey on LLM Agents and Tool Use

## TL;DR
- LLM agents are AI systems using large language models as cores, integrating tool use, reasoning, and planning to interact with complex environments [1][2][3].
- Architectures range from modular cognitive frameworks to practical SDKs enabling reliable tool integration and multi-agent workflows [4][5].
- Challenges include tool invocation errors, planning failures, scalability issues, and security vulnerabilities, with open problems in adaptive orchestration and consistent multi-agent memory [6][7][8].

## Background
Large Language Model (LLM) agents represent a new generation of AI systems that utilize pretrained language models as their primary decision-making core. These agents extend beyond mere text generation: they perceive multimodal inputs, reason internally, plan across multiple steps, and invoke external tools such as search engines, calculators, and APIs to achieve goals. This combination allows them to interact with dynamic environments, combining traditional AI agent concepts with modern deep learning advancements. Agents have evolved from early symbolic systems and reinforcement learning agents towards flexible, general-purpose LLM systems capable of integrating multiple tool types and human-agent cooperation [1][2][3].

## Architectures and Frameworks
Modern LLM agents often deploy modular architectures such as the Cognitive Architectures for Language Agents (CoALA), which combine LLMs with memory modules, structured action spaces, and iterative action selection processes. Other architectures conceptualize agents as dynamic LLM-driven loops encompassing planning, tool-using, feedback assessment, and replanning phases. Leading frameworks like LangChain offer component-based tool chaining and agent harnessing, supporting tool integrations like APIs, code execution, and human approvals. Industry offerings from Anthropic and Microsoft provide SDKs and multi-agent frameworks facilitating scalable, production-ready workflows [4][5]. These architectural choices enable flexible tool use embedded within agent decision processes for robust, extensible systems.

## Challenges and Limitations
LLM agents face several persistent challenges. Tool invocation errors and parameter mismatches frequently cause failures, especially in complex multi-step reasoning tasks. Planning and constraint satisfaction remain difficult, notably during long-horizon decision sequences, where context drift and accumulation degrade performance. Multi-agent coordination adds complexity with consensus memory and communication needs. Security is a pressing concern, with vulnerabilities arising from insufficient safety in function calling interfaces leading to potential jailbreak attacks. Scalability is hampered by maintaining large tool catalogs and parallel state consistency. Data quality, hallucination in tool parameters, and brittle training methods further limit reliability in practical deployments [6][7][8].

## Trends and Open Problems
Emerging trends emphasize adaptive multi-tool orchestration protocols to ensure reliable, end-to-end performance. There is growing recognition of the need for unified standards, such as Model Context Protocols, to enhance interoperability across tools and agents. Reinforcement learning and credit assignment strategies for long-term planning are active areas for improving sequential decision capability. Addressing knowledge conflicts between internal priors and external evidence is crucial for accurate actions. Stronger security frameworks are being developed to mitigate function attack vulnerabilities. Research on multi-agent consensus, hierarchical context management, and workload partitioning continues to advance interpretable and scalable system designs. Benchmarking complex tool use and multi-agent scenarios remains a critical evaluation frontier [6][7][8].

## References
[1] History and Overview of LLM Agents. web. https://rdi.berkeley.edu/llm-agents/assets/llm_agent_history.pdf (n.d.)
[2] The Rise and Potential of Large Language Model Based Agents: A Survey. arxiv. https://arxiv.org/abs/2309.07864 (2023-09-19)
[3] A Review of Prominent Paradigms for LLM-Based Agents: Tool Use (Including RAG), Planning, and Feedback Learning. arxiv. https://arxiv.org/html/2406.05804v6 (n.d.)
[4] Cognitive Architectures for Language Agents (CoALA). hf-search. https://huggingface.co/papers/hf_search_coala (n.d.)
[5] Anthropic and Microsoft Agent Frameworks. web. https://websource.example/anthropic_agent_framework (n.d.)
[6] Beyond the Leaderboard: A Synthesis of Tool-Use, Planning, and Reasoning Failures in Large Language Model Agents. web. https://arxiv.org/abs/2607.05775 (2026-07-07)
[7] Survey on Multi-tool LLM Agents: Progress and Challenges. web. https://arxiv.org/pdf/2603.22862 (n.d.)
[8] Empowering LLM-based Agents: Methods and Challenges in Tool Use. web. https://ace.ewapub.com/article/view/28954.pdf (n.d.)
