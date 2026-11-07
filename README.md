# Radeon AI PRO R9700 benchmarks

LLM inference benchmarks on a home server with 2x AMD Radeon AI PRO R9700 (32 GB each).

| Date | Write-up | Data |
| --- | --- | --- |
| 2026-11-07 | [vLLM, Qwen3.8-27B MXFP4, TP2, DFlash speculative decoding](r9700-vllm-2026-11-07.md) | [r9700-vllm-2026-11-07/](r9700-vllm-2026-11-07/) |

## 2026-11-07 data folder

- `raw/<run>.json`: `vllm bench serve --save-result --save-detailed` output, per-request TTFT/ITL included.
- `raw/<run>.log`: full client output.
- `raw/gpu-log-pass*.csv`: rocm-smi samples (power, temperature, use) every 5 s. `raw/run-times-pass*.log`: start/end time of each run.
- `raw/cachehit-first-pass/`: the first 8k/32k runs. They reused a seed plus a warmup request, so 7-32 % of the
  prompt tokens hit the prefix cache. **Not valid results**, kept only for reference. The clean re-runs (unique seed,
  no warmup, 0 cache hits) are the ones in `raw/` and in the write-up.
- `env/launch-config.json`: image, full vLLM launch arguments and environment of the server container.
  `env/gpu-static.txt`: amd-smi/rocm-smi output (serials removed). `env/host-info.txt`: host summary.
- `commands.txt`: the exact `vllm bench serve` commands. The lines after `# pass 2` replaced the first 8k/32k runs.
- `scripts/`: the run scripts and `summarize.py`, which rebuilds the results table from `raw/`.
