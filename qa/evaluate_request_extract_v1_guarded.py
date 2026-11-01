"""Run the frozen request-extractor evaluator with its fail-closed scorer."""

from qa import evaluate_request_extract_v1 as evaluation
from qa.request_extract_scoring import score_request_extract


evaluation._score = score_request_extract


if __name__ == "__main__":
    evaluation.main()
