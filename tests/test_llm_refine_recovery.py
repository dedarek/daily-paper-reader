import importlib.util
import pathlib
import sys
import unittest


def _load_module(module_name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class LlmRefineRecoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[1]
        src_dir = root / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        cls.mod = _load_module("llm_refine_mod_recovery", src_dir / "4.llm_refine_papers.py")

    def relevant_result(self, paper_id="p-1", score=8):
        return {
            "id": paper_id,
            "matched_requirement_index": 1,
            "evidence_en": "relevant method",
            "evidence_cn": "相关方法",
            "tldr_en": "This paper is relevant because it studies a method that matches the requested research direction and provides useful technical evidence.",
            "tldr_cn": "这篇论文围绕用户关注的研究方向展开，提出了与需求高度相关的方法框架。它不仅说明了核心问题和技术路线，也给出了可用于判断相关性的实验或理论依据。整体上，该论文可以作为后续精读和方法比较的重要候选，并帮助用户快速判断是否值得继续阅读原文，同时为相近主题的论文筛选提供稳定参考。",
            "title_zh": "中文标题",
            "motivation_cn": "论文动机直接对应用户检索需求，关注当前方法在目标任务中仍然存在的关键不足。",
            "method_cn": "论文方法围绕需求中的技术核心展开，给出了较明确的建模思路、算法流程或实现策略。",
            "result_cn": "论文结果显示该方法在相关任务或实验设置中取得了有效提升，具备进一步参考价值。",
            "conclusion_cn": "论文结论表明该方向具有继续探索价值，并能为用户关注的问题提供可复用思路。",
            "motivation_quality": "strong",
            "data_benchmark_status": "public",
            "public_resource_evidence": "doc",
            "public_resource_basis": "named_established_resource",
            "quality_gate_reason_cn": "动机具体且基准公开。",
            "score": score,
        }

    def test_recover_filter_results_retries_for_missing_ids(self):
        docs = [
            {"id": "p-1", "content": "doc1"},
            {"id": "p-2", "content": "doc2"},
        ]
        calls = []

        def runner(batch_docs, attempt, retry_note):
            calls.append((tuple(item["id"] for item in batch_docs), attempt, retry_note))
            if attempt == 1:
                return [
                    self.relevant_result("p-1"),
                ]
            return [
                self.relevant_result("p-1"),
                self.relevant_result("p-2", score=7),
            ]

        out = self.mod.recover_filter_results(docs, runner, max_attempts=2, debug_tag="batch_test")
        self.assertEqual([item["id"] for item in out], ["p-1", "p-2"])
        self.assertEqual(len(calls), 2)
        self.assertIn("p-1, p-2", calls[1][2])
        self.assertIn("missing ids=p-2", calls[1][2])

    def test_recover_filter_results_split_batch_after_retry_exhausted(self):
        docs = [
            {"id": "p-1", "content": "doc1"},
            {"id": "p-2", "content": "doc2"},
        ]
        calls = []

        def runner(batch_docs, attempt, retry_note):
            doc_ids = tuple(item["id"] for item in batch_docs)
            calls.append((doc_ids, attempt))
            if len(batch_docs) == 1:
                return [
                    self.relevant_result(batch_docs[0]["id"], score=6)
                ]
            return [
                self.relevant_result("p-1", score=6),
            ]

        out = self.mod.recover_filter_results(docs, runner, max_attempts=1, debug_tag="split_test")
        self.assertEqual([item["id"] for item in out], ["p-1", "p-2"])
        self.assertIn((("p-1",), 1), calls)
        self.assertIn((("p-2",), 1), calls)

    def test_recover_filter_results_splits_immediately_on_truncated_output(self):
        docs = [
            {"id": "p-1", "content": "doc1"},
            {"id": "p-2", "content": "doc2"},
        ]
        calls = []

        def runner(batch_docs, attempt, retry_note):
            doc_ids = tuple(item["id"] for item in batch_docs)
            calls.append((doc_ids, attempt))
            if len(batch_docs) > 1:
                raise self.mod.FilterOutputTruncatedError("unexpected finish_reason: length")
            return [
                self.relevant_result(batch_docs[0]["id"], score=6)
            ]

        out = self.mod.recover_filter_results(docs, runner, max_attempts=3, debug_tag="length_test")

        self.assertEqual([item["id"] for item in out], ["p-1", "p-2"])
        self.assertEqual(calls.count((("p-1", "p-2"), 1)), 1)
        self.assertNotIn((("p-1", "p-2"), 2), calls)
        self.assertIn((("p-1",), 1), calls)
        self.assertIn((("p-2",), 1), calls)

    def test_recover_filter_results_accepts_short_best_effort_fields(self):
        docs = [
            {"id": "p-1", "content": "doc1"},
        ]
        calls = []

        def runner(batch_docs, attempt, retry_note):
            calls.append((tuple(item["id"] for item in batch_docs), attempt, retry_note))
            return [
                {
                    **self.relevant_result("p-1", score=8),
                    "tldr_cn": "相关，但摘要信息有限。",
                    "motivation_cn": "信息有限。",
                    "method_cn": "信息有限。",
                    "result_cn": "信息有限。",
                    "conclusion_cn": "信息有限。",
                }
            ]

        out = self.mod.recover_filter_results(docs, runner, max_attempts=3, debug_tag="short_test")

        self.assertEqual(out[0]["id"], "p-1")
        self.assertEqual(out[0]["tldr_cn"], "相关，但摘要信息有限。")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 1)
        self.assertEqual(calls[0][2], "")

    def test_call_filter_repeats_user_prompt_with_separator(self):
        captured = {}
        test_case = self

        class FakeClient:
            model = "gemini-3-flash-preview-nothinking"

            def chat_structured(self, messages, schema_name, schema, strict, allow_json_object_fallback):
                captured["messages"] = messages
                captured["schema_name"] = schema_name
                captured["schema"] = schema
                captured["strict"] = strict
                captured["allow_json_object_fallback"] = allow_json_object_fallback
                return {
                    "content": (
                        '{"results":[{"id":"p-1","matched_requirement_index":1,'
                        '"evidence_en":"ok","evidence_cn":"相关","tldr_en":"ok","tldr_cn":"相关","score":8}]}'
                    ),
                    "parsed": {
                        "results": [test_case.relevant_result("p-1")]
                    },
                    "parse_error": None,
                    "refusal": "",
                    "finish_reason": "stop",
                }

        out = self.mod.call_filter(
            client=FakeClient(),
            all_requirements=[
                {
                    "id": "req-1",
                    "query": "symbolic regression methods",
                    "tag": "query:sr",
                    "kind": "direct",
                    "description_en": "Find papers relevant to symbolic regression methods",
                }
            ],
            docs=[{"id": "p-1", "content": "Title: A\nAbstract: B"}],
            debug_dir="",
            debug_tag="prompt_test",
        )

        self.assertEqual(out[0]["id"], "p-1")
        self.assertEqual(out[0]["title_zh"], "中文标题")
        self.assertIn("论文方法围绕需求", out[0]["method_cn"])
        user_content = captured["messages"][1]["content"]
        self.assertEqual(captured["schema_name"], "rerank_batch")
        self.assertTrue(captured["strict"])
        self.assertTrue(captured["allow_json_object_fallback"])
        self.assertIn("Let me repeat that:", user_content)
        self.assertEqual(user_content.count("User requirements list:"), 2)
        self.assertEqual(user_content.count("Papers:"), 2)
        self.assertIn("method_cn", user_content)
        self.assertIn("title_zh", user_content)
        self.assertIn("QUALITY ASSESSMENT AND LIMITED HARD REJECTIONS", user_content)
        self.assertIn("obvious distinction", user_content)
        self.assertIn("absence of evidence is unclear", user_content)
        self.assertIn("Code, model weights, a GitHub repository", user_content)
        self.assertIn("data_benchmark_status", user_content)
        self.assertIn("public_resource_basis", user_content)
        self.assertIn("150-220 Chinese characters", user_content)
        self.assertIn("30-70 Chinese characters", user_content)
        self.assertIn("length targets are guidance", user_content)
        self.assertIn("same style as a paper-page TLDR abstract", user_content)
        self.assertNotIn("<= 60 Chinese characters", user_content)
        self.assertTrue(user_content.rstrip().endswith("Output must be strict JSON only, no markdown, no fences, no extra text."))

    def test_quality_gate_rejects_weak_motivation(self):
        item = self.relevant_result(score=9)
        item["motivation_quality"] = "weak"

        normalized = self.mod._normalize_filter_result_item(item)

        self.assertFalse(normalized["quality_gate_pass"])
        self.assertEqual(normalized["score"], 0)
        self.assertEqual(normalized["matched_requirement_index"], 0)
        self.assertIn("研究动机薄弱", normalized["quality_gate_reason_cn"])

    def test_quality_gate_relaxes_unverified_dataset_or_benchmark(self):
        item = self.relevant_result(score=9)
        item["data_benchmark_status"] = "unclear"

        normalized = self.mod._normalize_filter_result_item(item)

        self.assertTrue(normalized["quality_gate_pass"])
        self.assertEqual(normalized["quality_tier"], "relaxed")
        self.assertEqual(normalized["score"], 9)
        self.assertIn("缺少可验证的公开证据", normalized["quality_gate_reason_cn"])

    def test_quality_gate_rejects_explicitly_non_public_dataset(self):
        item = self.relevant_result(score=9)
        item["data_benchmark_status"] = "not_public"

        normalized = self.mod._normalize_filter_result_item(item)

        self.assertFalse(normalized["quality_gate_pass"])
        self.assertEqual(normalized["quality_tier"], "rejected")
        self.assertEqual(normalized["score"], 0)
        self.assertIn("明确未公开", normalized["quality_gate_reason_cn"])

    def test_quality_gate_accepts_strong_non_empirical_paper(self):
        item = self.relevant_result(score=8)
        item["data_benchmark_status"] = "not_applicable"
        item["public_resource_basis"] = "not_applicable"

        normalized = self.mod._normalize_filter_result_item(item)

        self.assertTrue(normalized["quality_gate_pass"])
        self.assertEqual(normalized["score"], 8)

    def test_quality_gate_relaxes_public_label_without_evidence(self):
        item = self.relevant_result(score=9)
        item["public_resource_evidence"] = ""

        normalized = self.mod._normalize_filter_result_item(item)

        self.assertTrue(normalized["quality_gate_pass"])
        self.assertEqual(normalized["quality_tier"], "relaxed")
        self.assertEqual(normalized["score"], 9)
        self.assertIn("未提供公开证据", normalized["quality_gate_reason_cn"])

    def test_quality_gate_relaxes_ungrounded_public_evidence(self):
        item = self.relevant_result(score=9)
        item["public_resource_evidence"] = "a benchmark never mentioned in the paper"

        normalized = self.mod.validate_filter_results(
            [{"id": "p-1", "content": "Title: Test\nAbstract: We report experiments."}],
            [item],
        )[0]

        self.assertTrue(normalized["quality_gate_pass"])
        self.assertEqual(normalized["quality_tier"], "relaxed")
        self.assertEqual(normalized["score"], 9)
        self.assertIn("逐字定位", normalized["quality_gate_reason_cn"])

    def test_quality_gate_accepts_grounded_public_evidence(self):
        item = self.relevant_result(score=9)
        item["public_resource_evidence"] = "PublicBench"

        normalized = self.mod.validate_filter_results(
            [{"id": "p-1", "content": "Title: Test\nAbstract: Evaluated on PublicBench."}],
            [item],
        )[0]

        self.assertTrue(normalized["quality_gate_pass"])
        self.assertEqual(normalized["score"], 9)

    def test_quality_gate_relaxes_code_release_as_public_data_evidence(self):
        item = self.relevant_result(score=9)
        item["public_resource_evidence"] = "Our code is available at https://github.com/example/repo"
        item["public_resource_basis"] = "named_established_resource"

        normalized = self.mod._normalize_filter_result_item(item)

        self.assertTrue(normalized["quality_gate_pass"])
        self.assertEqual(normalized["quality_tier"], "relaxed")
        self.assertEqual(normalized["score"], 9)
        self.assertIn("代码或模型公开不能替代", normalized["quality_gate_reason_cn"])

    def test_quality_gate_accepts_explicit_public_dataset_statement(self):
        item = self.relevant_result(score=9)
        item["public_resource_evidence"] = "five public agent-security datasets"
        item["public_resource_basis"] = "explicit_public_statement"

        normalized = self.mod._normalize_filter_result_item(item)

        self.assertTrue(normalized["quality_gate_pass"])
        self.assertEqual(normalized["score"], 9)


if __name__ == "__main__":
    unittest.main()
