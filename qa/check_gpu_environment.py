"""Verify the project interpreter and real CUDA operations on the target GPU."""

import importlib.metadata
import json
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "metrics" / "environment_gpu_check.json"
report = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "interpreter": sys.executable,
    "platform": platform.platform(),
    "kind": "CUDA environment verification; no dataset or Mini GPT training",
    "status": "failed",
}

try:
    import torch
    import torch.nn.functional as F

    report.update(
        torch=torch.__version__,
        cuda_runtime=torch.version.cuda,
        cuda_available=torch.cuda.is_available(),
        cudnn=torch.backends.cudnn.version(),
    )
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise RuntimeError("Interpreter is not using this project's .venv")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the project environment")
    properties = torch.cuda.get_device_properties(0)
    report.update(
        gpu=properties.name,
        compute_capability=list(torch.cuda.get_device_capability(0)),
        vram_bytes=properties.total_memory,
        compiled_architectures=torch.cuda.get_arch_list(),
        bf16_supported=torch.cuda.is_bf16_supported(),
    )
    if "RTX 5070" not in properties.name:
        raise RuntimeError(f"Target GPU is not RTX 5070: {properties.name}")
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    a_cpu = torch.randn(256, 256)
    b_cpu = torch.randn(256, 256)
    result = a_cpu.cuda() @ b_cpu.cuda()
    reference = a_cpu @ b_cpu
    torch.testing.assert_close(result.cpu(), reference, rtol=1e-3, atol=1e-3)
    report["fp32_matmul"] = "passed: CUDA result matches CPU reference"
    import numpy as np
    array = a_cpu.numpy()
    np.testing.assert_array_equal(torch.from_numpy(array).numpy(), array)
    report["numpy_interop"] = "passed: torch Tensor and NumPy array conversion"

    dtype = torch.bfloat16 if report["bf16_supported"] else torch.float16
    q, k, v = [torch.randn(2, 4, 64, 32, device="cuda", dtype=dtype, requires_grad=True) for _ in range(3)]
    attention = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    loss = attention.float().square().mean()
    loss.backward()
    if not all(t.grad is not None and torch.isfinite(t.grad).all().item() for t in (q, k, v)):
        raise RuntimeError("Non-finite or absent attention gradients")
    report["causal_attention_forward_backward"] = f"passed: {dtype}, finite gradients"

    layer = torch.nn.Linear(32, 16, device="cuda")
    optimizer = torch.optim.AdamW(layer.parameters(), lr=1e-3)
    weight_before = layer.weight.detach().clone()
    with torch.autocast(device_type="cuda", dtype=dtype):
        optimizer_loss = layer(torch.randn(4, 32, device="cuda")).float().square().mean()
    optimizer_loss.backward()
    optimizer.step()
    if torch.equal(weight_before, layer.weight) or not torch.isfinite(layer.weight).all().item():
        raise RuntimeError("Optimizer did not produce a finite parameter update")
    torch.cuda.synchronize()
    report["mixed_precision_adamw"] = "passed: finite parameter update"
    report["peak_allocated_bytes"] = torch.cuda.max_memory_allocated(0)
    report["nvidia_smi"] = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,compute_cap", "--format=csv,noheader"],
        text=True,
    ).strip()
    report["packages"] = {}
    for name in ("torch", "numpy", "datasets", "tokenizers", "tqdm", "matplotlib", "pandas", "ipykernel", "jsonschema", "safetensors"):
        try:
            report["packages"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            report["packages"][name] = None
    report["status"] = "passed"
except Exception:
    report["error"] = traceback.format_exc()
finally:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)

raise SystemExit(0 if report["status"] == "passed" else 1)
