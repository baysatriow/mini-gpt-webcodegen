"""Mean loss and perplexity over supervised tokens, with already-aligned labels."""
import math

from src.training.engine import loss_sum


def token_metrics(logits, labels):
    total, count = loss_sum(logits, labels)
    loss = float(total.detach()) / count
    return {"loss": loss, "perplexity": math.exp(loss) if loss < 700 else None, "valid_tokens": count}
