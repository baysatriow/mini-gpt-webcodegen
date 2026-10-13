import unittest

import torch
import torch.nn.functional as F

from src.models.minigpt import MiniGPT


def tiny_config():
    return {"vocab_size": 32, "block_size": 16, "n_layer": 2, "n_head": 2,
            "n_embd": 16, "dropout": 0.0, "tie_embeddings": True}


class MiniGPTTests(unittest.TestCase):
    def test_shape_and_future_tokens_cannot_change_prefix_logits(self):
        torch.manual_seed(42)
        model = MiniGPT(tiny_config()).eval()
        original = torch.tensor([[1, 2, 3, 4, 5, 6]])
        changed = torch.tensor([[1, 2, 3, 20, 21, 22]])
        with torch.no_grad():
            first, second = model(original), model(changed)
        self.assertEqual(tuple(first.shape), (1, 6, 32))
        torch.testing.assert_close(first[:, :3], second[:, :3], rtol=0, atol=1e-6)
        self.assertFalse(torch.equal(first[:, 3:], second[:, 3:]))

    def test_backward_is_finite_and_tied_weights_share_parameters(self):
        model = MiniGPT(tiny_config())
        logits = model(torch.tensor([[1, 2, 3, 4]]))
        loss = F.cross_entropy(logits.reshape(-1, 32), torch.tensor([2, 3, 4, 5]))
        loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))
        self.assertIs(model.lm_head.weight, model.token_embedding.weight)

    def test_invalid_heads_and_context_overflow_are_rejected(self):
        with self.assertRaises(ValueError):
            MiniGPT({**tiny_config(), "n_head": 3})
        model = MiniGPT(tiny_config())
        with self.assertRaises(ValueError):
            model(torch.ones((1, 17), dtype=torch.long))
        with self.assertRaises(ValueError):
            model(torch.ones((1, 0), dtype=torch.long))

    @unittest.skipUnless(torch.cuda.is_available(), "CUDA unavailable")
    def test_cuda_bf16_forward_backward_is_finite(self):
        model = MiniGPT(tiny_config()).cuda()
        inputs = torch.randint(0, 32, (2, 16), device="cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(inputs)
            loss = F.cross_entropy(logits.float().reshape(-1, 32), inputs.reshape(-1))
        loss.backward()
        torch.cuda.synchronize()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters()))


if __name__ == "__main__":
    unittest.main()
