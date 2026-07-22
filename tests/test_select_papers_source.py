import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


def _load_module(module_name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class SelectPapersSourceTagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[1]
        src_dir = root / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        cls.mod = _load_module("select_mod", src_dir / "5.select_papers.py")

    def test_build_candidates_marks_selection_source(self):
        scored = [
            {"id": "fresh-1", "title": "Fresh", "llm_score": 8.2, "quality_gate_pass": True},
            {"id": "fresh-2", "title": "Fresh2", "llm_score": 8.1, "quality_gate_pass": True},
        ]
        carryover = [
            {"id": "carry-1", "title": "Carry", "llm_score": 9.0, "quality_gate_pass": True},
        ]
        out = self.mod.build_candidates(scored, carryover, set())
        source_map = {item.get("id"): item.get("selection_source") for item in out}
        self.assertEqual(source_map.get("fresh-1"), "fresh_fetch")
        self.assertEqual(source_map.get("fresh-2"), "fresh_fetch")
        self.assertEqual(source_map.get("carry-1"), "carryover_cache")

    def test_build_candidates_rejects_missing_or_failed_quality_gate(self):
        scored = [
            {"id": "pass", "llm_score": 8.5, "quality_gate_pass": True},
            {"id": "fail", "llm_score": 9.5, "quality_gate_pass": False},
            {"id": "legacy", "llm_score": 9.8},
        ]

        out = self.mod.build_candidates(scored, [], set())

        self.assertEqual([item["id"] for item in out], ["pass"])

    def test_build_candidates_honors_user_exclusions(self):
        scored = [
            {"id": "keep", "llm_score": 8.5, "quality_gate_pass": True},
            {"id": "2607.13594v1", "llm_score": 9.5, "quality_gate_pass": True},
        ]

        out = self.mod.build_candidates(
            scored,
            [],
            set(),
            excluded_ids={"2607.13594V1"},
        )

        self.assertEqual([item["id"] for item in out], ["keep"])

    def test_topic_gate_rejects_generic_methods_but_keeps_safety_targets(self):
        self.assertFalse(
            self.mod.is_topic_relevant(
                {"title": "SmartRAG: Native Graph-Based RAG for Mobile Device", "abstract": "A graph RAG assistant."}
            )
        )
        self.assertFalse(
            self.mod.is_topic_relevant(
                {"title": "Domain-Conditional Position Offsets", "abstract": "Improves language model perplexity."}
            )
        )
        self.assertTrue(
            self.mod.is_topic_relevant(
                {"title": "A Lightweight Hate Speech Detector", "abstract": "Content moderation for abusive language."}
            )
        )

    def test_build_candidates_applies_topic_gate(self):
        scored = [
            {"id": "generic", "title": "Generic RAG", "abstract": "A retrieval system.", "llm_score": 9.0, "quality_gate_pass": True},
            {"id": "safety", "title": "Toxicity Guard", "abstract": "A toxicity classifier for content moderation.", "llm_score": 6.0, "quality_gate_pass": True},
        ]
        out = self.mod.build_candidates(scored, [], set())
        self.assertEqual([item["id"] for item in out], ["safety"])

    def test_novelty_fallback_prefers_unseen_lower_score_over_replay(self):
        candidates = [
            {
                "id": "new-weak-match",
                "llm_score": 4.5,
                "quality_gate_pass": True,
                "selection_source": "fresh_fetch",
            },
            {
                "id": "old-replay",
                "llm_score": 9.0,
                "quality_gate_pass": True,
                "selection_source": "recent_replay",
            },
            {
                "id": "too-low",
                "llm_score": 3.0,
                "quality_gate_pass": True,
                "selection_source": "fresh_fetch",
            },
        ]

        result = self.mod.process_novelty_fallback(candidates, "standard")

        self.assertEqual([item["id"] for item in result["quick_skim"]], ["new-weak-match"])
        self.assertTrue(result["stats"]["novelty_floor_used"])

    def test_daily_minimum_fills_three_deep_and_five_quick(self):
        candidates = [
            {
                "id": f"paper-{idx}",
                "llm_score": score,
                "quality_gate_pass": True,
                "quality_tier": "strict" if idx % 2 else "relaxed",
                "selection_source": "fresh_fetch",
            }
            for idx, score in enumerate([8.5, 7.2, 6.4, 5.8, 5.2, 4.8, 3.5, 1.0], start=1)
        ]
        regular = self.mod.process_mode(
            candidates=candidates,
            tag_count=1,
            mode="standard",
            cfg=self.mod.MODES["standard"],
            carryover_ratio=0.5,
        )

        result = self.mod.ensure_daily_minimum_sections(regular, candidates)

        self.assertEqual(len(result["deep_dive"]), 3)
        self.assertEqual(len(result["quick_skim"]), 5)
        self.assertEqual(result["stats"]["minimum_shortfall"], 0)
        self.assertTrue(result["stats"]["minimum_fill_used"])
        selected = result["deep_dive"] + result["quick_skim"]
        self.assertTrue(all(float(item["llm_score"]) > 0 for item in selected))

    def test_daily_minimum_never_uses_failed_quality_gate_or_zero_score(self):
        candidates = [
            {"id": "good", "llm_score": 4.0, "quality_gate_pass": True},
            {"id": "zero", "llm_score": 0.0, "quality_gate_pass": True},
            {"id": "bad-gate", "llm_score": 9.0, "quality_gate_pass": False},
        ]
        result = self.mod.ensure_daily_minimum_sections(
            {"deep_dive": [], "quick_skim": [], "stats": {}},
            candidates,
        )

        selected_ids = {
            item["id"] for item in result["deep_dive"] + result["quick_skim"]
        }
        self.assertEqual(selected_ids, {"good"})
        self.assertEqual(result["stats"]["minimum_shortfall"], 7)

    def test_load_recent_qualified_recommendations_for_zero_result_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            rec_dir = root / "20260719" / "recommend"
            rec_dir.mkdir(parents=True)
            payload = {
                "deep_dive": [
                    {
                        "id": "qualified",
                        "title": "Qualified",
                        "llm_score": 9.0,
                        "quality_gate_pass": True,
                        "matched_query_tag": "query:small-model-content-safety",
                    },
                    {
                        "id": "failed-gate",
                        "title": "Failed",
                        "llm_score": 9.8,
                        "quality_gate_pass": False,
                        "matched_query_tag": "query:small-model-content-safety",
                    },
                ],
                "quick_skim": [],
            }
            (rec_dir / "arxiv_papers_20260719.standard.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            items, source_date = self.mod.load_recent_qualified_recommendations(
                str(root),
                "20260720",
                "standard",
                active_tags=["small-model-content-safety"],
                max_days=5,
            )

        self.assertEqual(source_date, "20260719")
        self.assertEqual([item["id"] for item in items], ["qualified"])
        self.assertEqual(items[0]["selection_source"], "recent_replay")
        self.assertTrue(items[0]["is_recent_replay"])
        self.assertEqual(items[0]["replayed_from_date"], "20260719")

    def test_aggregate_replay_fills_across_days_and_honors_exclusions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            for day, paper_ids in {
                "20260718": ["older-1", "blocked"],
                "20260719": ["newer-1"],
            }.items():
                rec_dir = root / day / "recommend"
                rec_dir.mkdir(parents=True)
                payload = {
                    "deep_dive": [
                        {
                            "id": pid,
                            "llm_score": 8.0,
                            "quality_gate_pass": True,
                            "matched_query_tag": "query:small-model-content-safety",
                        }
                        for pid in paper_ids
                    ],
                    "quick_skim": [],
                }
                (rec_dir / f"arxiv_papers_{day}.standard.json").write_text(
                    json.dumps(payload, ensure_ascii=False),
                    encoding="utf-8",
                )

            items, source_dates = self.mod.load_recent_qualified_recommendations(
                str(root),
                "20260720",
                "standard",
                active_tags=["small-model-content-safety"],
                max_days=5,
                aggregate_days=True,
                max_items=8,
                excluded_ids={"BLOCKED"},
            )

        self.assertEqual({item["id"] for item in items}, {"newer-1", "older-1"})
        self.assertEqual(source_dates, "20260719,20260718")

    def test_build_carryover_out_marks_source(self):
        out = self.mod.build_carryover_out(
            [
                {
                    "id": "p-1",
                    "llm_score": 8.5,
                    "title": "P1",
                    "selection_source": "fresh_fetch",
                },
                {
                    "id": "p-2",
                    "llm_score": 7.9,
                    "title": "P2",
                    "selection_source": "fresh_fetch",
                },
            ],
            set(),
            5,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].get("selection_source"), "carryover_cache")
        self.assertEqual(out[0].get("paper_id"), "p-1")

    def test_sanitize_items_keeps_selection_source(self):
        with tempfile.TemporaryDirectory():
            items = [
                {
                    "id": "p-1",
                    "_source": "new",
                    "selection_source": "fresh_fetch",
                }
            ]
            out = self.mod.sanitize_items(items)
            self.assertEqual(len(out), 1)
            self.assertNotIn("_source", out[0])
            self.assertEqual(out[0].get("selection_source"), "fresh_fetch")

    def test_load_recent_carryover_keeps_tag_time_independent(self):
        payload = {
            "generated_at": "2026-03-28T00:00:00+00:00",
            "tag_states": {
                "GENE": {
                    "updated_date": "20260328",
                    "carryover_days": 5,
                    "items": [
                        {
                            "id": "gene-1",
                            "paper_id": "gene-1",
                            "llm_score": 9.1,
                            "matched_query_tag": "query:GENE",
                            "carry_days": 1,
                        }
                    ],
                },
                "AHD": {
                    "updated_date": "20260326",
                    "carryover_days": 5,
                    "items": [
                        {
                            "id": "ahd-1",
                            "paper_id": "ahd-1",
                            "llm_score": 9.2,
                            "matched_query_tag": "query:AHD",
                            "carry_days": 1,
                        }
                    ],
                },
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "carryover.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            items, delta = self.mod.load_recent_carryover(
                str(path),
                self.mod.parse_date_str("20260328"),
                5,
                active_tags=["GENE"],
            )

        self.assertEqual(delta, 0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "gene-1")
        self.assertEqual(items[0]["carry_days"], 1)

    def test_build_carryover_payload_updates_only_active_tag(self):
        existing = {
            "generated_at": "2026-03-27T00:00:00+00:00",
            "tag_states": {
                "AHD": {
                    "updated_date": "20260327",
                    "carryover_days": 5,
                    "items": [
                        {
                            "id": "ahd-1",
                            "paper_id": "ahd-1",
                            "llm_score": 9.2,
                            "matched_query_tag": "query:AHD",
                            "carry_days": 2,
                        }
                    ],
                }
            },
        }
        payload = self.mod.build_carryover_payload(
            existing,
            [
                {
                    "id": "gene-1",
                    "paper_id": "gene-1",
                    "llm_score": 9.3,
                    "matched_query_tag": "query:GENE",
                    "llm_tags": ["gene"],
                    "carry_days": 1,
                }
            ],
            active_tags=["GENE"],
            carryover_days=5,
            updated_date="20260328",
        )

        self.assertIn("AHD", payload["tag_states"])
        self.assertIn("GENE", payload["tag_states"])
        self.assertEqual(payload["tag_states"]["AHD"]["updated_date"], "20260327")
        self.assertEqual(payload["tag_states"]["GENE"]["updated_date"], "20260328")
        self.assertEqual(payload["tag_states"]["GENE"]["items"][0]["id"], "gene-1")

    def test_collect_seen_ids_isolated_by_active_tag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            recommend_dir = root / "20260327" / "recommend"
            recommend_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "deep_dive": [
                    {
                        "id": "paper-ahd",
                        "matched_query_tag": "query:AHD",
                    },
                    {
                        "id": "paper-gene",
                        "matched_query_tag": "query:GENE",
                    },
                ],
                "quick_skim": [],
            }
            (recommend_dir / "arxiv_papers_20260327.standard.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            seen_gene = self.mod.collect_seen_ids(str(root), "20260328", active_tags=["GENE"])
            seen_ahd = self.mod.collect_seen_ids(str(root), "20260328", active_tags=["AHD"])
            seen_all = self.mod.collect_seen_ids(str(root), "20260328")

        self.assertEqual(seen_gene, {"paper-gene"})
        self.assertEqual(seen_ahd, {"paper-ahd"})
        self.assertEqual(seen_all, {"paper-ahd", "paper-gene"})


class SelectPapersDeepPriorityModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[1]
        src_dir = root / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        cls.mod = _load_module("select_mod", src_dir / "5.select_papers.py")

    def test_process_mode_keeps_all_nine_plus_even_if_over_cap(self):
        candidates = [
            {"id": "p-1", "llm_score": 9.6},
            {"id": "p-2", "llm_score": 9.3},
            {"id": "p-3", "llm_score": 9.1},
            {"id": "p-4", "llm_score": 8.9},
            {"id": "p-5", "llm_score": 8.8},
        ]
        result = self.mod.process_mode(
            candidates=candidates,
            tag_count=1,
            mode="standard",
            cfg={"deep_base": 1, "deep_unlimited": False, "deep_strategy": "round_robin"},
            carryover_ratio=0.5,
        )
        self.assertEqual(result.get("stats", {}).get("deep_selected"), 3)
        deep_ids = [item.get("id") for item in result.get("deep_dive", [])]
        self.assertEqual(deep_ids, ["p-1", "p-2", "p-3"])

    def test_process_mode_nine_plus_full_then_fill_to_cap_with_regular(self):
        candidates = [
            {"id": "p-1", "llm_score": 9.8},
            {"id": "p-2", "llm_score": 8.9},
            {"id": "p-3", "llm_score": 8.7},
            {"id": "p-4", "llm_score": 8.6},
        ]
        result = self.mod.process_mode(
            candidates=candidates,
            tag_count=2,
            mode="standard",
            cfg={"deep_base": 1, "deep_unlimited": False, "deep_strategy": "score"},
            carryover_ratio=0.5,
        )
        self.assertEqual(result.get("stats", {}).get("deep_selected"), 3)
        deep_ids = {item.get("id") for item in result.get("deep_dive", [])}
        self.assertIn("p-1", deep_ids)
        self.assertTrue("p-2" in deep_ids or "p-3" in deep_ids)

    def test_process_mode_nine_plus_only_keeps_original_when_none(self):
        candidates = [
            {"id": "p-1", "llm_score": 8.9},
            {"id": "p-2", "llm_score": 8.6},
            {"id": "p-3", "llm_score": 8.4},
            {"id": "p-4", "llm_score": 7.9},
        ]
        result = self.mod.process_mode(
            candidates=candidates,
            tag_count=2,
            mode="standard",
            cfg={"deep_base": 3, "deep_unlimited": False, "deep_strategy": "score"},
            carryover_ratio=0.5,
        )
        self.assertEqual(result.get("stats", {}).get("deep_selected"), 3)
        deep_scores = [float(item.get("llm_score", 0)) for item in result.get("deep_dive", [])]
        self.assertEqual(deep_scores, sorted(deep_scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
