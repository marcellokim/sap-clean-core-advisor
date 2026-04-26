"""Tests for Joule readiness gap analysis generation."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from models.schemas import GapAnalysisOutput
from services.application.joule_readiness import generate_joule_gap_analysis
from services.domain.joule_readiness_engine import build_deterministic_gap_analysis


class JouleReadinessEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        generate_joule_gap_analysis.clear()

    def tearDown(self) -> None:
        generate_joule_gap_analysis.clear()

    @patch(
        "services.application.joule_readiness.GeminiLLMProvider.generate_structured_output",
        return_value=GapAnalysisOutput(
            identified_gaps=["SSO 설정 누락"],
            recommended_actions=["IAS 연동 구성", "권한 매트릭스 검증"],
            risk_level="Medium",
            executive_summary="핵심 인증 구성이 누락되어 활성화 전 보완이 필요합니다.",
        ),
    )
    @patch("services.application.joule_readiness.GeminiLLMProvider.__init__", return_value=None)
    def test_returns_structured_gap_analysis_from_provider(
        self,
        _mock_provider_init: object,
        mock_generate_structured_output: object,
    ) -> None:
        result = generate_joule_gap_analysis(
            checked_items=["BTP 서브어카운트 생성 완료"],
            unchecked_items=["IAS 신뢰 설정 미완료"],
        )

        self.assertIsInstance(result, GapAnalysisOutput)
        self.assertEqual(result.risk_level, "Medium")
        self.assertEqual(result.identified_gaps, ["SSO 설정 누락"])
        self.assertEqual(result.recommended_actions[0], "IAS 연동 구성")
        self.assertIn("핵심 인증", result.executive_summary)
        mock_generate_structured_output.assert_called_once()

    @patch(
        "services.application.joule_readiness.GeminiLLMProvider.generate_structured_output",
        side_effect=RuntimeError("provider boom"),
    )
    @patch("services.application.joule_readiness.GeminiLLMProvider.__init__", return_value=None)
    def test_returns_fallback_output_when_provider_raises(
        self,
        _mock_provider_init: object,
        _mock_generate_structured_output: object,
    ) -> None:
        result = generate_joule_gap_analysis(
            checked_items=["역할 정의 완료"],
            unchecked_items=["테넌트 연결 미완료"],
        )

        self.assertEqual(result.risk_level, "High")
        self.assertTrue(result.identified_gaps)
        self.assertTrue(result.recommended_actions)
        self.assertIn("상세 갭 분석을 수행하지 못했습니다", result.executive_summary)

    @patch("services.application.joule_readiness.GeminiLLMProvider.generate_structured_output")
    @patch("services.application.joule_readiness.GeminiLLMProvider.__init__", return_value=None)
    def test_llm_disabled_uses_deterministic_analysis_without_provider_call(
        self,
        mock_provider_init: object,
        mock_generate_structured_output: object,
    ) -> None:
        with patch("config.settings.settings.LLM_DISABLE", True):
            result = generate_joule_gap_analysis(
                checked_items=["BTP 서브어카운트 생성 완료"],
                unchecked_items=["IAS 신뢰 설정 미완료", "Destination 연결 테스트 미완료"],
            )

        self.assertIsInstance(result, GapAnalysisOutput)
        self.assertTrue(result.identified_gaps)
        self.assertIn(result.risk_level, {"High", "Medium", "Low"})
        mock_provider_init.assert_not_called()
        mock_generate_structured_output.assert_not_called()

    @patch(
        "services.application.joule_readiness.GLMLLMProvider.generate_structured_output",
        return_value=GapAnalysisOutput(
            identified_gaps=["GLM gap"],
            recommended_actions=["GLM action"],
            risk_level="Low",
            executive_summary="GLM structured output",
        ),
    )
    @patch("services.application.joule_readiness.GLMLLMProvider.__init__", return_value=None)
    def test_glm_provider_uses_structured_adapter(
        self,
        mock_provider_init: object,
        mock_generate_structured_output: object,
    ) -> None:
        with patch("config.settings.settings.LLM_PROVIDER", "glm"), patch("config.settings.settings.LLM_DISABLE", False):
            result = generate_joule_gap_analysis(
                checked_items=["BTP 서브어카운트 생성 완료"],
                unchecked_items=["IAS 신뢰 설정 미완료"],
            )

        self.assertIsInstance(result, GapAnalysisOutput)
        self.assertEqual(result.risk_level, "Low")
        self.assertEqual(result.identified_gaps, ["GLM gap"])
        self.assertEqual(result.recommended_actions, ["GLM action"])
        mock_provider_init.assert_called_once()
        mock_generate_structured_output.assert_called_once()

    @patch("services.application.joule_readiness.GeminiLLMProvider.generate_structured_output")
    @patch("services.application.joule_readiness.GeminiLLMProvider.__init__", return_value=None)
    @patch("services.application.joule_readiness.GLMLLMProvider.generate_structured_output")
    @patch("services.application.joule_readiness.GLMLLMProvider.__init__", return_value=None)
    def test_unsupported_provider_uses_deterministic_analysis_without_provider_call(
        self,
        mock_glm_init: object,
        mock_glm_generate_structured_output: object,
        mock_gemini_init: object,
        mock_gemini_generate_structured_output: object,
    ) -> None:
        with patch("config.settings.settings.LLM_PROVIDER", "unsupported"), patch("config.settings.settings.LLM_DISABLE", False):
            result = generate_joule_gap_analysis(
                checked_items=["BTP 서브어카운트 생성 완료"],
                unchecked_items=["IAS 신뢰 설정 미완료"],
            )

        self.assertIsInstance(result, GapAnalysisOutput)
        self.assertTrue(result.recommended_actions)
        mock_gemini_init.assert_not_called()
        mock_gemini_generate_structured_output.assert_not_called()
        mock_glm_init.assert_not_called()
        mock_glm_generate_structured_output.assert_not_called()

    @patch("services.application.joule_readiness.GeminiLLMProvider.__init__", return_value=None)
    def test_returns_fallback_when_provider_payload_breaks_schema(
        self,
        _mock_provider_init: object,
    ) -> None:
        invalid_payloads = [
            {
                "identified_gaps": ["권한 검토 필요"],
                "recommended_actions": ["권한 역할 재설계"],
                "risk_level": "Severe",
                "executive_summary": "리스크 수준 enum 위반",
            },
            {
                "identified_gaps": ["감사 로그 누락"],
                "recommended_actions": ["감사 정책 정의"],
                "risk_level": "Low",
            },
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                generate_joule_gap_analysis.clear()
                with patch(
                    "services.application.joule_readiness.GeminiLLMProvider.generate_structured_output",
                    return_value=payload,
                ):
                    result = generate_joule_gap_analysis(
                        checked_items=["보안 정책 점검 완료"],
                        unchecked_items=["감사 로그 설정 미완료"],
                    )

                self.assertEqual(result.risk_level, "High")
                self.assertTrue(result.identified_gaps)
                self.assertTrue(result.recommended_actions)
                self.assertTrue(result.executive_summary)

    def test_deterministic_gap_analysis_groups_incomplete_workstreams(self) -> None:
        result = build_deterministic_gap_analysis(
            checked_items=["BTP Global Account 준비 완료"],
            unchecked_items=[
                "SAP Cloud Identity Services (IAS/IPS) 테넌트 준비 완료",
                "Destination 설정과 엔드포인트 연결 테스트 정상 확인",
            ],
        )

        self.assertGreaterEqual(len(result.identified_gaps), 1)
        self.assertGreaterEqual(len(result.recommended_actions), 2)
        self.assertIn(result.risk_level, {"High", "Medium"})


if __name__ == "__main__":
    unittest.main()
