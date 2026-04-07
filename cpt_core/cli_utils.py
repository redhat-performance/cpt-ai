"""
Shared CLI utilities for regression analyzer output formatting.

Used by both regression_analyzer.py (OpenSearch mode) and
csv_regression_analyzer.py (CSV mode).
"""


def fmt_val(v):
    """Format a numeric value for the metrics table."""
    if v == int(v):
        return f"{int(v):,}"
    elif abs(v) >= 100:
        return f"{v:,.2f}"
    else:
        return f"{v:.4f}"


def severity_bar(severity):
    """Return a visual severity bar."""
    bars = {
        'CRITICAL': '████████████████████  CRITICAL (>20%)',
        'MAJOR':    '█████████████         MAJOR (10-20%)',
        'MINOR':    '██████                MINOR (5-10%)',
    }
    return bars.get(severity, '')


def box_line(text, width=82):
    """Format a line inside a box: |  text...  |"""
    return "|  " + text.ljust(width - 4) + "|"


def box_empty(width=82):
    """Empty box line."""
    return "|" + " " * (width - 1) + "|"


def print_result(result, detail_level, logger=None):
    """Print boxed comparison summary, metrics table, and AI analysis."""
    run1_params = result.run1['params']
    run2_params = result.run2['params']
    geomean = result.geomean
    bench_name = run1_params.get('benchmark', 'BENCHMARK')
    W = 82

    if logger:
        logger.info(
            f"GEOMEAN: delta={geomean['delta_pct']:+.2f}%, "
            f"geomean={geomean.get('geomean_value', 0):.6f}, "
            f"matched={geomean['matched']}/{geomean['total_run1']}/{geomean['total_run2']}, "
            f"status={geomean['status']}, severity={geomean.get('severity', 'NONE')}, "
            f"threshold={geomean.get('threshold', 5.0)}%, "
            f"regressed={geomean.get('regressions_count', 0)}, "
            f"improved={geomean.get('improvements_count', 0)}, "
            f"metric={geomean['primary_metric']}"
        )

    status = geomean['status']
    delta = geomean['delta_pct']
    severity = geomean.get('severity', 'NONE')
    threshold = geomean.get('threshold', 5.0)
    category = geomean.get('category', '')
    geomean_val = geomean.get('geomean_value', 0)
    regressed_n = geomean.get('regressions_count', 0)
    improved_n = geomean.get('improvements_count', 0)
    neutral_n = geomean.get('neutral_count', 0)
    details = geomean.get('details', [])

    r1_os = f"{run1_params.get('os_vendor', '')} {run1_params.get('os_version', '')}".strip()
    r2_os = f"{run2_params.get('os_vendor', '')} {run2_params.get('os_version', '')}".strip()
    if len(r1_os) > 26:
        r1_os = r1_os[:23] + "..."
    if len(r2_os) > 26:
        r2_os = r2_os[:23] + "..."

    print()

    # Title
    title = f"CPT AI  -  {bench_name.upper()} REGRESSION ANALYSIS  ({detail_level.upper()})"
    print("+" + "=" * (W - 1) + "+")
    print(box_line(title, W))
    print("+" + "=" * (W - 1) + "+")

    # Run Comparison
    print(box_empty(W))
    print(box_line(f"{'':14s} {'Run 1 (Baseline)':<28s} {'Run 2 (Comparison)':<28s}", W))
    for label, v1, v2 in [
        ("Cloud",     run1_params.get('cloud', ''),     run2_params.get('cloud', '')),
        ("OS",        r1_os,                            r2_os),
        ("Instance",  run1_params.get('instance', ''),  run2_params.get('instance', '')),
        ("Benchmark", run1_params.get('benchmark', ''), run2_params.get('benchmark', '')),
    ]:
        print(box_line(f"{label + ':':<14s} {v1:<28s} {v2:<28s}", W))
    print(box_empty(W))

    # Verdict
    print("+" + "-" * (W - 1) + "+")
    print(box_empty(W))
    print(box_line(f"Status:    {status}  {delta:+.2f}%", W))
    if status == 'Regression':
        print(box_line(f"Severity:  {severity_bar(severity)}", W))
    print(box_line(f"Geomean:   {geomean_val:.6f}     Threshold: {threshold}% ({category})", W))
    print(box_line(f"Metrics:   {regressed_n} regressed  |  {improved_n} improved  |  {neutral_n} neutral", W))
    print(box_empty(W))

    # Per-Metric Table
    if details:
        print("+" + "-" * (W - 1) + "+")
        print(box_empty(W))
        if len(details) > 20:
            print(box_line(f"PER-METRIC BREAKDOWN (top 20 of {len(details)})", W))
        else:
            print(box_line("PER-METRIC BREAKDOWN", W))
        print(box_empty(W))

        hdr = f"{'Metric':<8s} {'Subtest':<18s} {'Run A':<14s} {'Run B':<14s} {'Delta':<10s} {'':6s}"
        print(box_line(hdr, W))
        print(box_line("-" * 73, W))

        sorted_details = sorted(details, key=lambda d: d.get('normalized_pct', 0))
        show_details = sorted_details[:20] if len(sorted_details) > 20 else sorted_details

        for d in show_details:
            npct = d.get('normalized_pct', 0)
            lower = d.get('lower_is_better', False)
            arrow = "v" if lower else "^"

            if npct < -threshold:
                verdict = f"REGR {arrow}"
            elif npct > threshold:
                verdict = f"IMPR {arrow}"
            else:
                verdict = f"  ok {arrow}"

            subtest = d['subtest']
            if len(subtest) > 18:
                subtest = subtest[:15] + "..."

            metric = d['metric']
            if len(metric) > 8:
                metric = metric[:8]

            line = (f"{metric:<8s} {subtest:<18s} "
                    f"{fmt_val(d['run1']):<14s} {fmt_val(d['run2']):<14s} "
                    f"{npct:+.2f}%{'':4s}{verdict}")
            print(box_line(line, W))

        print(box_empty(W))
        print(box_line("^ = higher-is-better    v = lower-is-better", W))
        print(box_empty(W))

    # AI Analysis
    print("+" + "=" * (W - 1) + "+")
    print()
    for line in result.analysis.splitlines():
        print(f"  {line}")
    print()
    print("+" + "=" * (W - 1) + "+")


async def qa_loop(analyzer, result):
    """Interactive Q&A loop."""
    print("\n" + "=" * 80)
    print("INTERACTIVE Q&A MODE")
    print("=" * 80)
    print("\nYou can now ask questions about the regression analysis.")
    print("\nType 'quit' or 'exit' to end the session.")
    print("=" * 80)

    chat_history = []
    while True:
        user_question = input("\nYour question: ").strip()

        if user_question.lower() in ['quit', 'exit', 'q']:
            print("\nExiting Q&A mode...")
            break

        if not user_question:
            print("Please enter a question.")
            continue

        print("\nAsking AI...")
        answer = await analyzer.ask(user_question, result, chat_history)

        chat_history.append({'role': 'user', 'content': user_question})
        chat_history.append({'role': 'assistant', 'content': answer})

        print("\n" + "-" * 80)
        print("AI Response:")
        print("-" * 80)
        print(answer)
        print("-" * 80)
