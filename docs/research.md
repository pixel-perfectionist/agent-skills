# Research notes

These papers provide context for Crossfire and AI ping pong. The connections below are design interpretations, not claims that the papers validate this implementation. None evaluates these skills or the default Opus 5.5/GPT-6 Astra pair.

The implementation combines a short council with an explicitly requested, uncapped cross-model review loop. That exact combination has not been benchmarked. In particular, the cited studies do not establish that unlimited rounds or unanimous approval guarantee a correct plan.

## Debate and different perspectives

### Improving Factuality and Reasoning in Language Models through Multiagent Debate

Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, and Igor Mordatch. **ICML 2024**, PMLR 235:11733–11763. [Published paper and proceedings](https://proceedings.mlr.press/v235/du24e.html).

Multiple agents first answer independently, then update their answers after reading peers' responses. Experiments primarily use GPT-3.5 with three agents and two debate rounds across arithmetic, mathematical reasoning, chess, and factuality tasks. The method improves results against the tested baselines.

**Connection:** Crossfire separates the initial Advocate and Critic assessments before cross-examination. AI ping pong also makes critique available for revision.

**Boundary:** This is an analogy to the interaction pattern. The paper does not evaluate this role structure or open-ended software plans. Its limitations include extra computation, context difficulties during extended debate, and confident agreement on wrong answers.

### ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs

Justin Chih-Yao Chen, Swarnadeep Saha, and Mohit Bansal. **ACL 2024**, pp. 7066–7085. [Published paper and proceedings](https://aclanthology.org/2024.acl-long.381/).

ReConcile combines ChatGPT, Bard, and Claude 2 in up to three discussion rounds on seven reasoning benchmarks. It incorporates confidence-weighted voting and examples of corrective explanations. Ablations link model diversity to improved performance in the evaluated settings.

**Connection:** This is the closest cited comparison for deliberately using different model providers.

**Boundary:** Crossfire does not vote, and AI ping pong requires two approvals rather than weighted consensus. ReConcile's components and model pairings differ. More rounds are not uniformly helpful: its StrategyQA results saturate and then decline slightly. The paper does not justify an uncapped loop.

### Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate

Tian Liang et al. **EMNLP 2024**, pp. 17889–17904. [Published paper and proceedings](https://aclanthology.org/2024.emnlp-main.992/).

Affirmative and negative debaters exchange arguments under a judge. Evaluations include commonsense translation and counterintuitive arithmetic using GPT-3.5, GPT-4, and Vicuna variants. The work examines how disagreement, the judge, and the number of participants affect outcomes.

**Connection:** Advocate, Critic, and Observer separate argument generation from scrutiny of those arguments.

**Boundary:** Crossfire's Observer audits reasoning rather than functioning as the paper's answer-selecting judge. The experiments do not imply that maximum disagreement is desirable: forced opposition and additional agents can hurt performance. The paper also reports model-family preferences in judging. Its debate is bounded.

## Feedback, revision, and evidence

### Self-Refine: Iterative Refinement with Self-Feedback

Aman Madaan et al. **NeurIPS 2023**, volume 36. [Published paper and proceedings](https://papers.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html).

A model generates a response, gives itself specific feedback, and revises without updating its weights. Evaluation spans seven language and code tasks with at most four refinement iterations. Gains vary by task; mathematical correction is limited when the model cannot reliably identify its own errors.

**Connection:** AI ping pong retains actionable objections and responses so revision addresses specific problems.

**Boundary:** Self-Refine uses a single model rather than the two-provider approval protocol. It does not validate unanimous approval, this project's roles, or unlimited iterations. Its aggregate gains should not be presented as expected gains for these skills.

### Reflexion: Language Agents with Verbal Reinforcement Learning

Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, and Shunyu Yao. **NeurIPS 2023**, volume 36. [Published paper and proceedings](https://papers.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html).

Agents turn feedback into written reflections retained for subsequent attempts. Evaluations include ALFWorld, HotPotQA, and Python/Rust programming. Reflections improve several results without weight updates.

**Connection:** Preserved objections and responses help later reviews retain the reasons earlier versions were rejected.

**Boundary:** Reflexion includes task execution and evaluation. HotPotQA uses exact-match success feedback; coding attempts use executable tests. Agreement about a plan lacks those correctness signals. Published programming results follow iterative refinement, not one model call, and inadequate self-generated tests can mislead the process.

### CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing

Zhibin Gou, Zhihong Shao, Yeyun Gong, Yelong Shen, Yujiu Yang, Nan Duan, and Weizhu Chen. **ICLR 2024**. [Published paper and proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/fef126561bbf9d4467dbb8d27334b8fe-Abstract-Conference.html).

Models critique and revise using external feedback, including web search, Python execution, and a toxicity API. Evaluations with text-davinci-003, GPT-3.5, and LLaMA-2 variants show benefits from tool-supported correction. Removing reliable feedback weakens results and can make revisions harmful.

**Connection:** Crossfire labels evidence, while AI ping pong can return `needs_evidence` instead of forcing a verdict.

**Boundary:** Our constrained CLI reviewers assess a supplied packet; they do not implement CRITIC's interactive verification procedure. The host must obtain relevant evidence. Another model's opinion is not equivalent to an execution result or an independently checked fact.

## Counterevidence and failure modes

### Large Language Models Cannot Self-Correct Reasoning Yet

Jie Huang et al. **ICLR 2024**. [Published paper and proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html).

The paper examines intrinsic correction without external feedback using then-available GPT and LLaMA-2 models. Asking models to reconsider often fails to improve reasoning and can reduce accuracy. Its comparisons also challenge assuming debate outperforms simpler sampling approaches.

**Connection:** The workflow preserves missing evidence and unresolved objections instead of treating additional reasoning as sufficient.

**Boundary:** These results concern the tested models and protocols. They do not prove that every newer model, external review process, or tool-grounded correction method fails. They do warrant separating a procedural approval from verified correctness.

### Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs

Andries P. Smit et al. **ICML 2024**, PMLR 235:45883–45905. [Published paper and proceedings](https://proceedings.mlr.press/v235/smit24a.html).

An evaluation of debate strategies across seven question-answering and reasoning datasets, primarily with GPT-3.5, finds that original debate implementations do not reliably outperform self-consistency and ensemble alternatives. Adjusting prompts, settings, and agreement behavior improves some results.

**Connection:** Crossfire uses proportional modes and a bounded cross-examination instead of assuming every decision benefits from a long council.

**Boundary:** The paper neither establishes debate as universally ineffective nor validates this workflow. Useful evaluation must compare against simpler methods and account for the resources each method consumes.

### CONSENSAGENT: Towards Efficient and Effective Consensus in Multi-Agent LLM Interactions Through Sycophancy Mitigation

Priya Pitre, Naren Ramakrishnan, and Xuan Wang. **Findings of ACL 2025**, pp. 22112–22133. [Published paper and proceedings](https://aclanthology.org/2025.findings-acl.1141/).

The paper investigates agreement dynamics across six datasets using pairs of Llama 3, Mistral, and GPT-4o variants. It identifies incorrect consensus, copying, cyclic answer changes, and stalled debates, and proposes prompt optimization to reduce these problems.

**Connection:** Preserving objections, constraints, and their sources is intended to discourage agreement achieved by quietly discarding the original problem.

**Boundary:** This project does not implement CONSENSAGENT's optimization method. Its preliminary two-agent experiments stop at agreement or five rounds; they do not establish whether this project's uncapped loop will converge. Preserving a transcript alone does not eliminate sycophancy.

## What is established here

The repository's tests check the transport and approval protocol: matching packets, verdict validation, model and reasoning records, and failure handling. Live CLI checks establish that both provider paths can return a review and pass the combined check on a small test packet.

These checks do not measure planning quality. A future evaluation could compare a single review, single-model refinement, Crossfire alone, and Crossfire followed by AI ping pong using fixed task sets, independently assessed outcomes, and explicit token/time budgets. It should report missed defects, unnecessary changes, cost, and runs that do not converge, alongside successful reviews. That evaluation has not been performed.
