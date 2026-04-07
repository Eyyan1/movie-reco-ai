from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.eval.prompt_benchmark import (
    DEFAULT_BENCHMARK_PATH,
    evaluate_prompt,
    load_benchmark_prompts,
    summarize_results,
)
from app.services.tmdb_service import TMDBService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run family-based recommendation benchmark prompts.")
    parser.add_argument(
        "--benchmark-file",
        type=Path,
        default=DEFAULT_BENCHMARK_PATH,
        help="Path to benchmark_prompts.json",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=None,
        help="Optional path to write a JSON report.",
    )
    args = parser.parse_args()

    prompts = load_benchmark_prompts(args.benchmark_file)
    service = TMDBService()
    results = [evaluate_prompt(service, benchmark) for benchmark in prompts]
    summary = summarize_results(results)

    print(f"Total prompts: {summary['total_prompts']}")
    print(f"Succeeded: {summary['succeeded']}")
    print(f"Failed: {summary['failed']}")
    print("")
    print(f"Overall average score: {summary['overall_average']:.3f}")
    print("")
    print("Average by family:")
    for family, score in summary["averages_by_family"].items():
        print(f"  {family}: {score:.3f}")

    print("")
    print("Worst prompts:")
    for item in summary["worst_prompts"]:
        if item["failed"]:
            print(
                f"  {item['prompt']} -> FAILED | {item['failure_reason']}"
            )
            continue
        print(f"  {item['prompt']} -> {item['metrics']['overall_score']:.3f} | {', '.join(item['failure_reasons']) or 'no major failures recorded'}")

    print("")
    print("Best prompts:")
    for item in summary["best_prompts"]:
        if item["failed"]:
            print(f"  {item['prompt']} -> FAILED | {item['failure_reason']}")
            continue
        print(f"  {item['prompt']} -> {item['metrics']['overall_score']:.3f}")

    print("")
    print("Top failure reasons:")
    for reason, count in summary["top_failure_reasons"]:
        print(f"  {reason}: {count}")

    if args.report_file is not None:
        args.report_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("")
        print(f"Wrote report to {args.report_file}")


if __name__ == "__main__":
    main()
