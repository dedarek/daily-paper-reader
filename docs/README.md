<div class="dpr-home-notice-card">
  <h3 class="dpr-home-notice-title">🚀 Start Here</h3>
  <ul class="dpr-home-notice-list">
    <li><a href="#/tutorial/README">使用教程</a></li>
  </ul>
</div>

## 每次日报
- 最新运行日期：2026-05-26 ~ 2026-06-04
- 运行时间：2026-06-04 21:13:49 UTC
- 运行状态：成功
- 本次总论文数：17
- 精读区：6
- 速读区：11

### 今日简报（AI）
近期共梳理17篇论文，精读6篇，重点关注LLM输出的神经符号验证与智能体工具调用的访问控制安全。

最值得深入的是《Neuro-Symbolic Verification of LLM Outputs》和《AgentGuard》，分别开创了数据敏感领域的严格验证与基于属性的工具调用防护。

普通读者可优先阅读《Prompt Injection Detection is Regime-Dependent》及《Evaluating using Mock Tool Calls》，了解提示注入检测的部署依赖性及沙箱隔离评估方法。
- 详情：[/20260526-20260604/README](/20260526-20260604/README)

### 精读区论文标签
1. [Neuro-Symbolic Verification of LLM Outputs for Data-Sensitive Domains (extended preprint)](/20260526-20260604/2605.26942v2-neuro-symbolic-verification-of-llm-outputs-for-data-sensitive-domains-extended-preprint)  
   标签：评分：9.0/10、query:llm-security
   evidence：混合验证架构确保LLM输出安全
2. [AgentGuard: An Attribute-Based Access Control Framework for Tool-Use LLM-Based Agent](/20260526-20260604/2605.28071v1-agentguard-an-attribute-based-access-control-framework-for-tool-use-llm-based-agent)  
   标签：评分：9.0/10、query:llm-security
   evidence：基于属性访问控制的安全机制
3. [Robust and Efficient Guardrails with Latent Reasoning](/20260526-20260604/2605.29068v1-robust-and-efficient-guardrails-with-latent-reasoning)  
   标签：评分：9.0/10、query:llm-security
   evidence：基于隐式推理的输出护栏
4. [COMPASS: Cognitive MCTS-Guided Process Alignment for Safe Search Agents](/20260526-20260604/2605.30838v1-compass-cognitive-mcts-guided-process-alignment-for-safe-search-agents)  
   标签：评分：9.0/10、query:llm-security
   evidence：为基于LLM的搜索智能体提供安全对齐框架
5. [AgentRedBench: Dynamic Redteaming and Integration-Aware Defense for LLM Agents over SaaS Integrations](/20260526-20260604/2606.02240v2-agentredbench-dynamic-redteaming-and-integration-aware-defense-for-llm-agents-over-saas-integrations)  
   标签：评分：9.0/10、query:llm-security
   evidence：针对LLM智能体的动态红队测试和集成感知防御，防御间接提示注入
6. [Caught in the Act(ivation): Toward Pre-Output and Multi-Turn Detection of Credential Exfiltration by LLM Agents](/20260526-20260604/2606.04141v1-caught-in-the-activation-toward-pre-output-and-multi-turn-detection-of-credential-exfiltration-by-llm-agents)  
   标签：评分：9.0/10、query:llm-security
   evidence：针对智能体提示注入的防御

### 速读区论文标签
1. [Neuro-Symbolic Verification of LLM Outputs for Data-Sensitive Domains (extended preprint)](/20260526-20260604/2605.26942v1-neuro-symbolic-verification-of-llm-outputs-for-data-sensitive-domains-extended-preprint)  
   标签：评分：8.0/10、query:llm-security
   evidence：神经符号输出验证保障安全
2. [Prompt Injection Detection is Regime-Dependent: A Deployment-Aware Evaluation with Interpretable Structural Signals](/20260526-20260604/2605.26999v1-prompt-injection-detection-is-regime-dependent-a-deployment-aware-evaluation-with-interpretable-structural-signals)  
   标签：评分：8.0/10、query:llm-security
   evidence：提示注入检测的部署感知评估
3. [Evaluating using Mock Tool Calls to Quarantine Untrusted Prompt Inputs](/20260526-20260604/2605.30521v1-evaluating-using-mock-tool-calls-to-quarantine-untrusted-prompt-inputs)  
   标签：评分：8.0/10、query:llm-security
   evidence：评估模拟工具调用隔离不可信输入作为抵御提示注入的防御方法
4. [Dialectics of Alignment: Harnessing Unsafe Knowledge for Dynamic Safety Routing](/20260526-20260604/2606.00686v1-dialectics-of-alignment-harnessing-unsafe-knowledge-for-dynamic-safety-routing)  
   标签：评分：8.0/10、query:llm-security
   evidence：提出SafeMoE框架，利用不安全知识实现动态安全路由和细粒度安全生成
5. [MemGuard: Preventing Memory Contamination in Long-Term Memory-Augmented Large Language Models](/20260526-20260604/2605.28009v1-memguard-preventing-memory-contamination-in-long-term-memory-augmented-large-language-models)  
   标签：评分：7.0/10、query:llm-security
   evidence：LLM代理的内存安全机制
6. [Configurable Reward Model for Balanced Safety Alignment](/20260526-20260604/2605.30487v1-configurable-reward-model-for-balanced-safety-alignment)  
   标签：评分：7.0/10、query:llm-security
   evidence：提出可配置安全奖励模型用于平衡的内容安全对齐
7. [DataShield: Safety-degrading Data Filtering for LLM Benign Instruction Fine-Tuning](/20260526-20260604/2606.00160v1-datashield-safety-degrading-data-filtering-for-llm-benign-instruction-fine-tuning)  
   标签：评分：7.0/10、query:llm-security
   evidence：从良性微调数据中过滤安全降级样本以维护内容安全
8. [SafeSteer: Localized On-Policy Distillation for Efficient Safety Alignment](/20260526-20260604/2606.02530v1-safesteer-localized-on-policy-distillation-for-efficient-safety-alignment)  
   标签：评分：7.0/10、query:llm-security
   evidence：通过在安全令牌上局部策略蒸馏的安全对齐方法
9. [SPARD: Defending Harmful Fine-Tuning Attack via Safety Projection with Relevance-Diversity Data Selection](/20260526-20260604/2605.28030v1-spard-defending-harmful-fine-tuning-attack-via-safety-projection-with-relevance-diversity-data-selection)  
   标签：评分：6.0/10、query:llm-security
   evidence：针对对抗性微调攻击的缓解方法
10. [SilentRetrieval: Hijacking Retrieval-Augmented Generation via Semantically-Preserving Adversarial Data Poisoning](/20260526-20260604/2605.28074v1-silentretrieval-hijacking-retrieval-augmented-generation-via-semantically-preserving-adversarial-data-poisoning)  
   标签：评分：6.0/10、query:llm-security
   evidence：针对RAG系统的数据投毒攻击，可视为提示注入的一种形式
11. [Aligned but Fragile: Enhancing LLM Safety Robustness via Zeroth-Order Optimization](/20260526-20260604/2605.29396v1-aligned-but-fragile-enhancing-llm-safety-robustness-via-zeroth-order-optimization)  
   标签：评分：6.0/10、query:llm-security
   evidence：通过优化方法增强安全鲁棒性


<div class="dpr-home-promo-card">
  <h3 class="dpr-home-promo-title">💬 社区与支持</h3>
  <ul class="dpr-home-promo-list">
    <li>欢迎 Star / Fork / Issue / PR</li>
    <li>QQ群：583867967（欢迎交流，已有：1151人）</li>
  </ul>
</div>
