import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tools.stats.upload_stats_lib import (
    upload_to_s3,
)
from tools.stats.upload_test_stats import (
    get_invoking_file_times,
    get_pytest_parallel_times,
    parse_xml_report,
    summarize_test_cases,
)


def get_tests_for_circleci(
    workflow_run_id: int, workflow_run_attempt: int
) -> Tuple[List[Dict[str, Any]], Dict[Any, Any]]:
    # Parse the reports and transform them to JSON
    test_cases = []
    for xml_report in Path(".").glob("**/test/test_reports/**/*.xml"):
        test_cases.extend(
            parse_xml_report(
                "testcase",
                xml_report,
                workflow_run_id,
                workflow_run_attempt,
            )
        )

    pytest_parallel_times = get_pytest_parallel_times()

    return test_cases, pytest_parallel_times


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload test stats to Rockset for circleci"
    )
    parser.add_argument(
        "--circle-workflow-id",
        required=True,
        help="id of the workflow, see https://circleci.com/docs/variables#built-in-environment-variables",
    )
    parser.add_argument(
        "--head-branch",
        required=True,
        help="Head branch of the workflow",
    )
    args = parser.parse_args()
    test_cases, pytest_parallel_times = get_tests_for_circleci(
        args.circle_workflow_id, 1  # im not sure how to get attempt number for circleci
    )

    # Flush stdout so that any errors in rockset upload show up last in the logs.
    sys.stdout.flush()

    # For PRs, only upload a summary of test_runs. This helps lower the
    # volume of writes we do to Rockset.
    test_case_summary = summarize_test_cases(test_cases)
    invoking_file_times = get_invoking_file_times(
        test_case_summary, pytest_parallel_times
    )

    upload_to_s3(
        args.circle_workflow_id,
        1,
        "test_run_summary",
        test_case_summary,
    )

    upload_to_s3(
        args.circle_workflow_id,
        1,
        "invoking_file_times",
        invoking_file_times,
    )

    if args.head_branch == "master":
        # For master jobs, upload everytihng.
        upload_to_s3(args.circle_workflow_id, 1, "test_run", test_cases)
