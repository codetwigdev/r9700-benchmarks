#!/bin/bash
# Runs on a separate client machine. Sends HTTP benchmark traffic only, using the vllm bench client
# inside the running vLLM container in CT 113. Does not restart or reconfigure anything.
set -u
# Set SERVER (vLLM host address), LLM_HOST (ssh alias of the docker host) and VLLM_CONTAINER first.
OUT=./results
C=${VLLM_CONTAINER:?set to the vLLM container name}
TOK=/models/Qwen3.8-27B-MXFP4-mtpfp8
COMMON="--base-url http://127.0.0.1:8080 --model Qwen3.8 --tokenizer $TOK --dataset-name random --random-range-ratio 0 --seed 42 --ignore-eos --num-warmups 1 --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,90,99 --save-result --save-detailed --result-dir /tmp/amdbench"

wait_idle() {
  for i in $(seq 1 60); do
    r=$(curl -s -m5 http://$SERVER:8080/metrics | awk '/^vllm:num_requests_(running|waiting)\{/{s+=$2} END{print s+0}')
    [ "$r" = "0" ] && return 0
    echo "$(date -Is) background load: $r requests running/waiting, waiting 30s" | tee -a $OUT/background-load.log
    sleep 30
  done
}

run() {  # name backend endpoint in out conc nprompts [extra args...]
  name=$1 be=$2 ep=$3 in=$4 outl=$5 conc=$6 np=$7; shift 7
  wait_idle
  echo "$(date -Is) start $name" | tee -a $OUT/run.log
  curl -s http://$SERVER:8080/metrics > $OUT/raw/$name.metrics-before.txt
  cmd="vllm bench serve --backend $be --endpoint $ep $COMMON --random-input-len $in --random-output-len $outl --max-concurrency $conc --num-prompts $np --result-filename $name.json $*"
  echo "docker exec $C $cmd" >> $OUT/commands.txt
  echo "mkdir -p /tmp/amdbench && $cmd" | ssh $LLM_HOST "docker exec -i $C bash -s" > $OUT/raw/$name.log 2>&1
  ssh $LLM_HOST "docker exec $C cat /tmp/amdbench/$name.json" > $OUT/raw/$name.json
  curl -s http://$SERVER:8080/metrics > $OUT/raw/$name.metrics-after.txt
  echo "$(date -Is) end $name" | tee -a $OUT/run.log
}

# GPU logger
( while true; do echo "=== $(date -Is)"; ssh $LLM_HOST "docker exec $C rocm-smi -d 0 1 --showpower --showtemp --showuse --showsclk --showmclk --csv" 2>/dev/null; sleep 5; done ) > $OUT/raw/gpu-log.csv &
GL=$!
trap "kill $GL" EXIT

run r1k-c1 openai /v1/completions 1024 512 1 8
run r1k-c4 openai /v1/completions 1024 512 4 16
run r1k-c8 openai /v1/completions 1024 512 8 32
run r8k-c1 openai /v1/completions 8192 512 1 8
run r8k-c4 openai /v1/completions 8192 512 4 16
run r8k-c8 openai /v1/completions 8192 512 8 32
run r32k-c1 openai /v1/completions 32768 256 1 8
# Chat endpoint (chat template applied): thinking on (template default) vs off
run chat1k-think-c1 openai-chat /v1/chat/completions 1024 512 1 8
run chat1k-nothink-c1 openai-chat /v1/chat/completions 1024 512 1 8 --extra-body "'{\"chat_template_kwargs\":{\"enable_thinking\":false}}'"
echo done | tee -a $OUT/run.log
