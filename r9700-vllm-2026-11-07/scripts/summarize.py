import json, glob, os, re, csv, io, datetime as dt
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo folder above scripts/
order=["r1k-c1","r1k-c4","r1k-c8","r8k-c1","r8k-c4","r8k-c8","r32k-c1","chat1k-think-c1","chat1k-nothink-c1","r8k-c1-cachehit","r8k-c4-cachehit","r8k-c8-cachehit","r32k-c1-cachehit"]
# GPU log -> per-run power/temp
samples=[]
cur=None
for line in open(f"{D}/raw/gpu-log-pass1.csv").read().splitlines()+open(f"{D}/raw/gpu-log-pass2.csv").read().splitlines():
    line=line.strip()
    if line.startswith("=== "): cur=dt.datetime.fromisoformat(line[4:]); continue
    if line.startswith("card") and cur:
        f=line.split(",")
        samples.append((cur,f[0],float(f[2]),float(f[4]),float(f[5])))  # junction, power, use
runs={}
for l in open(f"{D}/raw/run-times-pass1.log").read().splitlines()+open(f"{D}/raw/run-times-pass2.log").read().splitlines():
    m=re.match(r"(\S+) (start|end) (\S+)",l)
    if m:
        k=m[3]
        if k in runs and "end" in runs[k] and m[2]=="start": runs[k+"-cachehit"]=runs.pop(k)
        runs.setdefault(k,{})[m[2]]=dt.datetime.fromisoformat(m[1])
rows=[]
for n in order:
    p=f"{D}/raw/{n}.json" if "cachehit" not in n else f"{D}/raw/cachehit-first-pass/{n}.json"
    if not os.path.exists(p) or os.path.getsize(p)==0: continue
    j=json.load(open(p))
    c=j["max_concurrency"]
    w=runs.get(n,{})
    ss=[s for s in samples if w and w["start"]<=s[0]<=w["end"] and s[4]>=50]
    pw=max([s[3] for s in ss],default=float('nan')); tj=max([s[2] for s in ss],default=float('nan'))
    pavg=sum(s[3] for s in ss)/len(ss) if ss else float('nan')
    acc=j.get("spec_decode_acceptance_rate"); al=j.get("spec_decode_acceptance_length")
    rows.append(dict(name=n,conc=c,np=j["completed"],inp=j["total_input_tokens"]//j["completed"],out=j["total_output_tokens"]//j["completed"],
      otps=j["output_throughput"],ttps=j["total_token_throughput"],perreq=1000/j["mean_tpot_ms"] if j["mean_tpot_ms"] else 0,
      perreq_e2e=(j["total_output_tokens"]/j["completed"])/(j["mean_e2el_ms"]/1000),
      ttft50=j["median_ttft_ms"],ttft99=j["p99_ttft_ms"],tpot=j["median_tpot_ms"],tpotm=j["mean_tpot_ms"],itl=j["median_itl_ms"],itl99=j["p99_itl_ms"],
      rps=j["request_throughput"],acc=acc,al=al,pavg=pavg,pmax=pw,tj=tj,dur=j["duration"]))
def f(x,d=1): 
    return "n/a" if x is None or x!=x else f"{x:.{d}f}"
print("| Run | Conc | Prompts | In/Out tok | Output tok/s (total) | Total tok/s | Per-req tok/s (1/TPOT) | Per-req tok/s (out/E2E) | TTFT median ms | TTFT p99 ms | TPOT median ms | ITL median ms | ITL p99 ms | Req/s | Spec accept % | Accept len | GPU W avg/max (per card) | Junction max °C |")
print("|"+"---|"*18)
for r in rows:
    print(f"| {r['name']} | {r['conc']} | {r['np']} | {r['inp']}/{r['out']} | {f(r['otps'])} | {f(r['ttps'])} | {f(r['perreq'])} | {f(r['perreq_e2e'])} | {f(r['ttft50'],0)} | {f(r['ttft99'],0)} | {f(r['tpot'],2)} | {f(r['itl'],1)} | {f(r['itl99'],1)} | {f(r['rps'],3)} | {f(r['acc'])} | {f(r['al'],2)} | {f(r['pavg'],0)}/{f(r['pmax'],0)} | {f(r['tj'],0)} |")
