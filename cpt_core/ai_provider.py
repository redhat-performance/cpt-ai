"""
AI provider abstraction - ABC and OpenAI-compatible implementation.

Contains all prompt construction logic and API call mechanics.
Embeds the full regression detection methodology into prompts.
"""

import json
import logging
from abc import ABC, abstractmethod

import httpx

from .analysis import (
    BENCHMARK_THRESHOLDS, ROOT_CAUSE_PATTERNS,
    is_lower_better, get_benchmark_category,
)

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def analyze(self, run1_params, run1_data, run2_params, run2_data,
                      detail_level, geomean_info) -> str:
        """Produce a regression analysis report."""

    @abstractmethod
    async def ask(self, question, run1_params, run1_data, run2_params, run2_data,
                  geomean_info, chat_history=None) -> str:
        """Answer a follow-up question about the comparison."""


class OpenAICompatibleProvider(AIProvider):
    """Concrete AI provider using any OpenAI-compatible chat/completions endpoint."""

    def __init__(self, endpoint: str, api_key: str, model_name: str,
                 ssl_verify: bool = False):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model_name = model_name
        self.ssl_verify = ssl_verify

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(self, run1_params, run1_data, run2_params, run2_data,
                      detail_level, geomean_info) -> str:
        from .data_access import extract_metrics

        metrics1 = extract_metrics(run1_data)
        metrics2 = extract_metrics(run2_data)
        if not metrics1 or not metrics2:
            return "ERROR: Could not extract metrics from runs"

        system_prompt = self._build_analysis_system_prompt(detail_level, geomean_info)
        user_message = self._build_analysis_user_message(
            run1_params, run1_data, metrics1,
            run2_params, run2_data, metrics2,
            geomean_info,
        )

        max_tokens = {"basic": 500, "medium": 2000}.get(detail_level, 4000)
        return await self._chat(system_prompt, user_message, temperature=0.1,
                                max_tokens=max_tokens)

    async def ask(self, question, run1_params, run1_data, run2_params, run2_data,
                  geomean_info, chat_history=None) -> str:
        from .data_access import extract_metrics

        metrics1 = extract_metrics(run1_data)
        metrics2 = extract_metrics(run2_data)
        if not metrics1 or not metrics2:
            return "ERROR: Could not extract metrics from runs"

        geomean_context = self._build_geomean_context(geomean_info)
        methodology = self._build_methodology_context(geomean_info)

        system_prompt = (
            "You are an expert performance engineer analyzing benchmark results.\n"
            "Answer the user's question based on the two runs provided. "
            "Be specific, technical, and cite actual metric values when relevant.\n"
            "When asked about how the regression was calculated, explain the "
            "direction-aware geometric mean methodology.\n"
            f"{methodology}\n"
            f"{geomean_context}"
        )

        user_message = (
            f"Here are two benchmark runs:\n\n"
            f"RUN 1 (Baseline):\n"
            f"Cloud: {run1_params['cloud']}\n"
            f"OS: {run1_params['os_vendor']} {run1_params['os_version']}\n"
            f"Instance: {run1_params['instance']}\n"
            f"Benchmark: {run1_params['benchmark']}\n"
            f"Timestamp: {run1_data.get('metadata', {}).get('test_timestamp')}\n"
            f"Metrics: {json.dumps(metrics1, indent=2)}\n\n"
            f"RUN 2 (Comparison):\n"
            f"Cloud: {run2_params['cloud']}\n"
            f"OS: {run2_params['os_vendor']} {run2_params['os_version']}\n"
            f"Instance: {run2_params['instance']}\n"
            f"Benchmark: {run2_params['benchmark']}\n"
            f"Timestamp: {run2_data.get('metadata', {}).get('test_timestamp')}\n"
            f"Metrics: {json.dumps(metrics2, indent=2)}\n\n"
            f"USER QUESTION: {question}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})

        return await self._chat_messages(messages, temperature=0.3, max_tokens=2000)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _chat(self, system_prompt, user_message, temperature=0.3,
                    max_tokens=2000):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        return await self._chat_messages(messages, temperature, max_tokens)

    async def _chat_messages(self, messages, temperature=0.3, max_tokens=2000):
        async with httpx.AsyncClient(timeout=60.0, verify=self.ssl_verify) as client:
            try:
                response = await client.post(
                    f"{self.endpoint}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name or "default",
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                else:
                    return f"ERROR: {response.status_code}: {response.text[:200]}"
            except Exception as e:
                logger.error(f"AI API call failed: {e}")
                return f"ERROR: {e}"

    # ------------------------------------------------------------------
    # Methodology context
    # ------------------------------------------------------------------

    @staticmethod
    def _build_methodology_context(geomean_info):
        """Build the regression detection methodology context for prompts."""
        if not geomean_info:
            return ""

        benchmark = geomean_info.get('benchmark', '')
        threshold = geomean_info.get('threshold', 5.0)
        category = get_benchmark_category(benchmark)

        # Threshold table
        threshold_lines = []
        for cat in BENCHMARK_THRESHOLDS.values():
            benches = ', '.join(sorted(cat['benchmarks']))
            threshold_lines.append(
                f"  {cat['label']}: > {cat['threshold']}% | {benches}")

        return (
            "\nREGRESSION DETECTION METHODOLOGY:\n"
            "=================================\n\n"
            "METRIC DIRECTION:\n"
            "  Higher-is-better (throughput): Gflops, bw, iops, TPM, Bops, BOPs, "
            "GB_Sec, trans_sec, sched_eff, Copy, Scale, Add, Triad, Score\n"
            "  Lower-is-better (latency/time): clat, lat, slat, usec, Time, "
            "ME_LATENCY, Avg (pyperf), Run Time\n\n"
            "DIRECTION-AWARE GEOMEAN:\n"
            "  Higher-is-better: ratio_i = Run_B / Run_A\n"
            "  Lower-is-better:  ratio_i = Run_A / Run_B\n"
            "  geomean = (ratio_1 * ratio_2 * ... * ratio_n)^(1/n)\n"
            "  geomean > 1.0 = improvement, < 1.0 = regression, = 1.0 = no change\n"
            "  delta% = (geomean - 1) * 100  (positive=better, negative=worse)\n\n"
            "REGRESSION THRESHOLDS:\n"
            + "\n".join(threshold_lines) + "\n\n"
            f"THIS BENCHMARK: {benchmark} → category: {category}, "
            f"threshold: {threshold}%\n"
        )

    # ------------------------------------------------------------------
    # Geomean calculation context
    # ------------------------------------------------------------------

    @staticmethod
    def _build_geomean_context(geomean_info):
        """Build detailed geomean calculation context for AI prompts."""
        if not geomean_info:
            return ""

        detail_lines = []
        for d in geomean_info.get('details', []):
            direction = d.get('direction', 'higher-is-better')
            ratio = d.get('ratio', d['run2'] / d['run1'] if d['run1'] != 0 else 0)
            npct = d.get('normalized_pct', d.get('delta_pct', 0))
            detail_lines.append(
                f"    {d['metric']} @ {d['subtest']}: "
                f"Run_A={d['run1']:.6g}, Run_B={d['run2']:.6g}, "
                f"ratio={ratio:.6f}, normalized_delta={npct:+.2f}% "
                f"[{direction}]"
            )

        threshold = geomean_info.get('threshold', 5.0)
        severity = geomean_info.get('severity', 'NONE')
        root_causes = geomean_info.get('root_causes', [])

        root_cause_text = ""
        if root_causes:
            root_cause_text = (
                "\n  SUGGESTED ROOT CAUSES:\n"
                + "\n".join(f"    - {c}" for c in root_causes)
                + "\n"
            )

        regressions = geomean_info.get('regressions_count', 0)
        improvements = geomean_info.get('improvements_count', 0)
        neutral = geomean_info.get('neutral_count', 0)

        return (
            f"\nREGRESSION CALCULATION DETAILS:\n"
            f"  Method: Direction-aware geometric mean\n"
            f"  Higher-is-better: ratio = Run_B / Run_A\n"
            f"  Lower-is-better:  ratio = Run_A / Run_B\n"
            f"  Formula: geomean = exp(sum(log(ratio_i)) / N)\n"
            f"  delta% = (geomean - 1) * 100\n"
            f"  Matched metrics: {geomean_info['matched']}\n"
            f"  Threshold: {threshold}%\n"
            f"  Status: {geomean_info['status']} ({geomean_info['delta_pct']:+.2f}%)\n"
            f"  Severity: {severity}\n"
            f"  Breakdown: {regressions} regressed, {improvements} improved, "
            f"{neutral} neutral\n\n"
            f"  Per-metric ratios (direction-normalized):\n"
            + "\n".join(detail_lines) + "\n\n"
            f"  Geomean = {geomean_info.get('geomean_value', 0):.6f}\n"
            f"  Delta = ({geomean_info.get('geomean_value', 0):.6f} - 1) * 100 = "
            f"{geomean_info['delta_pct']:+.2f}%\n"
            f"{root_cause_text}\n"
            f"  Skip rules applied:\n"
            f"    - Non-performance keys skipped (status, count, error, total_*, etc.)\n"
            f"    - When _mean/_max/_min/_stddev variants exist, only _mean is used\n"
            f"    - Run_A = 0 skipped\n"
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_analysis_system_prompt(self, detail_level, geomean_info):
        methodology = self._build_methodology_context(geomean_info)

        geomean_context = ""
        if geomean_info:
            threshold = geomean_info.get('threshold', 5.0)
            severity = geomean_info.get('severity', 'NONE')
            geomean_context = (
                f"\nPRE-COMPUTED RESULTS (use these EXACTLY — do NOT recalculate):\n"
                f"  Status: {geomean_info['status']} ({geomean_info['delta_pct']:+.2f}%)\n"
                f"  Geomean: {geomean_info.get('geomean_value', 0):.6f}\n"
                f"  Matched metrics: {geomean_info['matched']} out of "
                f"{geomean_info['total_run1']} (Run1) / {geomean_info['total_run2']} (Run2)\n"
                f"  Threshold: {threshold}%\n"
                f"  Severity: {severity}\n"
                f"  Primary metric: {geomean_info['primary_metric']}\n"
                f"  Regressed: {geomean_info.get('regressions_count', 0)} | "
                f"Improved: {geomean_info.get('improvements_count', 0)} | "
                f"Neutral: {geomean_info.get('neutral_count', 0)}\n"
            )

        regression_rules = (
            "DIRECTION-AWARE STATUS RULES:\n"
            "- All metrics are normalized: negative delta% = regression, "
            "positive = improvement\n"
            f"- Threshold for this benchmark: {geomean_info.get('threshold', 5.0)}%\n"
            f'- "Regression" = performance degraded beyond threshold\n'
            f'- "Improvement" = performance improved beyond threshold\n'
            f'- "No regression" = within threshold (acceptable noise)\n'
            "- The Status is PRE-COMPUTED. Use it EXACTLY as provided.\n"
        )

        root_cause_hint = ""
        root_causes = geomean_info.get('root_causes', []) if geomean_info else []
        if root_causes:
            root_cause_hint = (
                "\nROOT CAUSE HINTS (consider these in your analysis):\n"
                + "\n".join(f"  - {c}" for c in root_causes) + "\n"
            )

        if detail_level == "basic":
            return (
                "You are a performance analyst. Compare two benchmark runs.\n\n"
                f"{regression_rules}\n{geomean_context}\n\n"
                "OUTPUT RULES:\n"
                "- Write exactly 1-2 sentences. No headers, no labels, no sections.\n"
                "- Start with the pre-computed status and delta, then summarize the key finding.\n"
                "- Mention the specific metric that moved the most.\n"
                "- Do NOT write 'Status:', 'Summary:', or any prefix labels.\n\n"
                "EXAMPLE OUTPUT (style only, not content):\n"
                "Regression -6.60%: Run2 shows lower Bops across all warehouse sizes on "
                "specjbb, with the largest drop at 64 warehouses (-10.43%). Likely caused "
                "by kernel version change.\n"
            )
        elif detail_level == "medium":
            return (
                "You are a performance analyst. Compare two benchmark runs.\n\n"
                f"{methodology}\n"
                f"{regression_rules}\n{geomean_context}\n"
                f"{root_cause_hint}\n"
                "OUTPUT RULES:\n"
                "- Write 5-10 lines total, organized into exactly two sections.\n"
                "- Use ONLY these two section headers (uppercase, no other formatting):\n"
                "  SUMMARY\n"
                "  ROOT CAUSE\n"
                "- Under SUMMARY: 3-5 lines covering the verdict, key metrics that moved, "
                "and their direction (higher/lower is better).\n"
                "- Under ROOT CAUSE: 2-3 lines suggesting why the change happened based on "
                "configuration differences (OS, instance, kernel, etc.).\n"
                "- Do NOT repeat Status/Severity/Geomean lines — those are already shown above.\n"
                "- Do NOT use markdown, bullets with *, or any decorative formatting.\n"
                "- Use plain dashes (-) for lists if needed.\n\n"
                "EXAMPLE OUTPUT (style only):\n"
                "SUMMARY\n"
                "The specjbb benchmark shows a minor regression of 6.60% in Bops. "
                "Performance degraded across most warehouse sizes, with the largest drops "
                "at 64 warehouses (-10.43%) and 56 warehouses (-10.12%). Bops is a "
                "higher-is-better throughput metric, so the decrease indicates slower "
                "Java business operations.\n\n"
                "ROOT CAUSE\n"
                "The regression is likely due to the kernel version change "
                "(el9_5 -> el9_6). Security mitigations or scheduler changes in the "
                "newer kernel may be impacting Java runtime performance.\n"
            )
        else:  # expert
            return (
                "You are an expert performance engineer. Provide a comprehensive "
                "regression analysis.\n\n"
                f"{methodology}\n"
                f"{regression_rules}\n{geomean_context}\n"
                f"{root_cause_hint}\n"
                "OUTPUT RULES:\n"
                "- Write a thorough analysis organized into exactly four sections.\n"
                "- Use ONLY these section headers (uppercase, no other formatting):\n"
                "  ANALYSIS\n"
                "  KEY DIFFERENCES\n"
                "  ROOT CAUSE TRIAGE\n"
                "  RECOMMENDATIONS\n"
                "- Under ANALYSIS: 5-8 lines covering the overall verdict, which metrics "
                "regressed/improved and by how much, direction context, and significance.\n"
                "- Under KEY DIFFERENCES: List configuration differences between runs "
                "(OS version, instance type, cloud, kernel, CPU, memory).\n"
                "- Under ROOT CAUSE TRIAGE: Based on which metrics regressed, suggest "
                "specific likely causes (e.g., CPU frequency, scheduler, mitigations).\n"
                "- Under RECOMMENDATIONS: 2-3 actionable next steps.\n"
                "- Do NOT repeat Status/Severity/Geomean/per-metric table — those are "
                "already shown above.\n"
                "- Do NOT use markdown, bullets with *, or decorative formatting.\n"
                "- Use plain dashes (-) for lists.\n\n"
                "EXAMPLE OUTPUT (style only):\n"
                "ANALYSIS\n"
                "The specjbb benchmark shows a 6.60% regression in Bops...\n\n"
                "KEY DIFFERENCES\n"
                "- Kernel: 5.14.0-503 (el9_5) -> 5.14.0-570 (el9_6)\n"
                "- Same instance, cloud, and CPU\n\n"
                "ROOT CAUSE TRIAGE\n"
                "- Kernel scheduler changes affecting Java thread scheduling\n"
                "- Possible new security mitigations in el9_6\n\n"
                "RECOMMENDATIONS\n"
                "1. Compare kernel changelogs between the two versions\n"
                "2. Test with tuned profile adjustments\n"
            )

    @staticmethod
    def _build_analysis_user_message(run1_params, run1_data, metrics1,
                                      run2_params, run2_data, metrics2,
                                      geomean_info):
        # Build per-metric detail lines with direction info
        detail_lines = []
        if geomean_info and geomean_info.get('details'):
            for d in geomean_info['details']:
                direction = d.get('direction', 'higher-is-better')
                npct = d.get('normalized_pct', d.get('delta_pct', 0))
                status_label = 'REGRESSION' if npct < -geomean_info.get('threshold', 5.0) \
                    else 'IMPROVEMENT' if npct > geomean_info.get('threshold', 5.0) \
                    else 'NEUTRAL'
                detail_lines.append(
                    f"  {d['metric']} @ {d['subtest']}: "
                    f"Run_A={d['run1']:.6g} Run_B={d['run2']:.6g} "
                    f"normalized_delta={npct:+.2f}% "
                    f"[{status_label}] [{direction}]"
                )

        subtest_summary = ""
        if detail_lines:
            subtest_summary = (
                f"\n\nALL METRICS ({len(detail_lines)} matched, direction-normalized):\n"
                + "\n".join(detail_lines)
                + f"\n\nGEOMEAN: {geomean_info.get('geomean_value', 0):.6f} "
                f"(delta: {geomean_info['delta_pct']:+.2f}%)"
                f"\nSTATUS: {geomean_info['status']}"
            )

        # Include report summary if available
        report = geomean_info.get('report_summary', '') if geomean_info else ''
        report_section = f"\n\nPRE-COMPUTED REPORT:\n{report}" if report else ""

        return (
            f"Compare these two benchmark runs:\n\n"
            f"RUN 1 (Baseline):\n"
            f"Cloud: {run1_params['cloud']}\n"
            f"OS: {run1_params['os_vendor']} {run1_params['os_version']}\n"
            f"Instance: {run1_params['instance']}\n"
            f"Benchmark: {run1_params['benchmark']}\n"
            f"Timestamp: {run1_data.get('metadata', {}).get('test_timestamp')}\n"
            f"Sample subtest metrics: {json.dumps(metrics1, indent=2)}\n\n"
            f"RUN 2 (Comparison):\n"
            f"Cloud: {run2_params['cloud']}\n"
            f"OS: {run2_params['os_vendor']} {run2_params['os_version']}\n"
            f"Instance: {run2_params['instance']}\n"
            f"Benchmark: {run2_params['benchmark']}\n"
            f"Timestamp: {run2_data.get('metadata', {}).get('test_timestamp')}\n"
            f"Sample subtest metrics: {json.dumps(metrics2, indent=2)}\n"
            f"{subtest_summary}"
            f"{report_section}\n\n"
            f"Analyze using the regression detection methodology. "
            f"Use pre-computed geomean and status EXACTLY as provided."
        )
