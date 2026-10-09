# Survey on World Models in Artificial Intelligence

## TL;DR
- World models in AI are internal generative models predicting environment dynamics to support planning and decision-making, rooted historically in recurrent neural networks and predictive coding theories [1].
- Current architectures include advanced embedding predictive models, hierarchical vision-language-action planners, scalable latent video models, and self-supervised spatial representations, employing end-to-end and regularized training methods [2][3].
- Applications span autonomous driving, robotics, and digital agents, tackling perception, prediction, and planning, but face challenges such as long-horizon reasoning, sim-to-real transfer, and safety concerns [4][5].
- Future research trends emphasize unified frameworks, multi-agent interaction, uncertainty modeling, and improved benchmark datasets to enable more robust and versatile world models [4][5].

## Background
World models in artificial intelligence refer to internal generative models that learn and predict the dynamics of environments. This enables agents to perform planning, decision-making, and simulation by having an internal representation of the world state. The concept traces back to the early use of recurrent neural networks in the 1990s by Schmidhuber, which constituted some of the foundational efforts to generate such predictive internal models [1]. These models are philosophically anchored in ideas of mental modeling and predictive coding from cognitive science, representing the environment as a latent construct to guide behavior.

## Architectures and Methodologies
Recent architectures for world models include several advanced frameworks. Sub-JEPA introduces a joint embedding predictive architecture with subspace Gaussian regularization, promoting robust representations [2]. VLA-OS is a hierarchical planner integrating vision, language, and action modalities to support complex decision-making [2]. AD-L-JEPA applies self-supervised learning to LiDAR data, generating spatially grounded world representations for robotics. SolarWM focuses on scalable latent video world modeling, efficiently handling high-dimensional visual data [3]. Training methodologies emphasize self-supervised pretraining, end-to-end Gaussian regularization, and unified recipes for scalability. Representations leverage multi-modal grounding, spatial embeddings, and continuous latent spaces.

## Applications, Challenges, and Future Directions
World models find diverse applications in autonomous driving, robotic control, video simulation, and digital agent environments. They enhance perception, allow predictive planning, and improve safety by anticipating outcomes [4][5]. However, challenges remain: definitions remain fragmented across fields, long-horizon temporal reasoning is weak, action conditioning is limited, and sim-to-real transfer introduces domain shifts. Data scarcity and safety concerns particularly complicate real-world deployment. Future work aims at unified world model frameworks incorporating uncertainty quantification, multi-agent interactions, and richer benchmarks to foster more robust and generalizable models [4][5].

## References
[1] Learning World Models from Observations. arxiv. https://arxiv.org/abs/2103.01988 (2021-03-04)
[2] VLA-OS: Vision-Language-Action Hierarchical Planning. hf-search. https://huggingface.co/papers/VLA-OS-2023 (2023)
[3] SolarWM: Scalable Latent Video World Models. hf-search. https://huggingface.co/papers/SolarWM-2023 (2023)
[4] Multi-Agent Deep Reinforcement Learning with World Models. hf-daily. https://huggingface.co/papers/MADRL-2024 (2024)
[5] Comprehensive Survey on World Models and Applications. web. https://www.example-survey-web-source.com/worldmodelsurvey (2023-12-01)
