"""Agentic baseline: mini-SWE-agent on our SWE-bench Lite subset.

Providers: `gemini` (free tier; same endpoint and settings as the Agentless runs)
and `openai` (paid, e.g. gpt-6-luna). Same issues and the same local Docker
images as Agentless. Runs in its own venv (.venv-agent) because mini-swe-agent
needs a newer stack than the pinned Agentless one.

Exit codes: 0 done, 3 Gemini daily quota exhausted (rerun after it renews;
finished issues are kept), 2 API failing after retries or out of credits,
4 --budget reached.

    .venv-agent/bin/python pesquisa/scripts/agentic/run_agent.py --ids pesquisa/data/subset_47.txt \
        --output pesquisa/results/agent_luna --provider openai --model gpt-6-luna
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from collections import deque
from pathlib import Path

import litellm
import yaml
from minisweagent.agents.default import DefaultAgent
from minisweagent.config import builtin_config_dir
from minisweagent.environments import get_environment
from minisweagent.exceptions import FormatError
from minisweagent.models.litellm_model import LitellmModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extra_metrics import PRECOS  # noqa: E402  (US$ per 1M tokens, one table for both)

# env prefix holds <P>_API_KEY, <P>_RPM, <P>_TPM, <P>_REASONING_EFFORT (same names as Agentless)
PROVIDERS = {
    "gemini": {"prefix": "GEMINI", "api_base": "https://generativelanguage.googleapis.com/v1beta/openai/",
               "rpm": 15, "tpm": 200000, "effort": "none"},
    "openai": {"prefix": "OPENAI", "api_base": None, "rpm": 50, "tpm": 0, "effort": ""},
}


class DailyQuotaExceeded(Exception):
    pass


class ApiFailure(Exception):
    pass


class CreditsExhausted(ApiFailure):
    pass


class Limiter:
    """Sliding 60 s window over requests and input tokens, shared by all workers."""

    def __init__(self, rpm, tpm):
        self.rpm, self.tpm = rpm, tpm
        self.window = deque()  # [timestamp, tokens]
        self.lock = threading.Lock()

    def acquire(self, est_tokens):
        while True:
            with self.lock:
                now = time.time()
                while self.window and now - self.window[0][0] > 60:
                    self.window.popleft()
                used = sum(t for _, t in self.window)
                tokens_ok = self.tpm <= 0 or not self.window or used + est_tokens <= self.tpm
                if len(self.window) < self.rpm and tokens_ok:
                    slot = [now, est_tokens]
                    self.window.append(slot)
                    return slot
                wait = 60.5 - (now - self.window[0][0])
            time.sleep(max(wait, 0.5))


class RateLimitedModel(LitellmModel):
    abort_exceptions = LitellmModel.abort_exceptions + [DailyQuotaExceeded, CreditsExhausted]
    limiter: Limiter
    prices: tuple
    api_key: str  # passed per call, never in the config: the config is saved in every trajectory

    def _query(self, messages, **kwargs):
        slot = self.limiter.acquire(len(json.dumps(messages)) // 3)
        try:
            response = super()._query(messages, api_key=self.api_key, **kwargs)
        except litellm.exceptions.RateLimitError as e:
            detail = str(e) + str(getattr(e, "body", ""))  # litellm's message drops the details
            if "PerDay" in detail:
                raise DailyQuotaExceeded(str(e)) from e
            if "insufficient_quota" in detail:  # OpenAI: prepaid credits used up
                raise CreditsExhausted(str(e)) from e
            raise
        slot[1] = response.usage.prompt_tokens
        return response

    def query(self, messages, **kwargs):
        try:
            return super().query(messages, **kwargs)
        except (FormatError, DailyQuotaExceeded, ApiFailure):
            raise
        except Exception as e:
            raise ApiFailure(f"{type(e).__name__}: {e}") from e

    def _calculate_cost(self, response):
        u = response.usage
        return {"cost": u.prompt_tokens / 1e6 * self.prices[0] + u.completion_tokens / 1e6 * self.prices[1]}


def usage_of(messages):
    p = c = 0
    for m in messages:
        u = (m.get("extra") or {}).get("response", {}).get("usage") if isinstance(m.get("extra"), dict) else None
        if isinstance(u, dict):
            p += u.get("prompt_tokens") or 0
            c += u.get("completion_tokens") or 0
    return p, c


def image_for(iid):
    local = f"sweb.eval.x86_64.{iid}:latest"
    ok = subprocess.run(["docker", "image", "inspect", local], capture_output=True).returncode == 0
    return local if ok else f"docker.io/swebench/sweb.eval.x86_64.{iid.replace('__', '_1776_')}:latest".lower()


def autosubmit(env):
    """Current tracked-file diff, for runs that hit the step/cost limit without submitting."""
    out = env.execute({"command": "git -c core.fileMode=false diff"})
    return out["output"] if out.get("returncode") == 0 else ""


def run_instance(inst, out_dir, cfg, args, lock):
    iid = inst["instance_id"]
    idir = out_dir / iid
    shutil.rmtree(idir, ignore_errors=True)
    model = RateLimitedModel(**cfg["model"])
    env = get_environment({**cfg["environment"], "image": image_for(iid)})
    agent = DefaultAgent(model, env, **{**cfg["agent"], "output_path": idir / f"{iid}.traj.json"})
    extra = {}
    try:
        info = agent.run(inst["problem_statement"])
        status, patch = info.get("exit_status", ""), info.get("submission", "") or ""
        if not patch.strip() and args.autosubmit:
            patch = autosubmit(env)
            if patch.strip():
                status += "+autosubmit"
    except (DailyQuotaExceeded, ApiFailure):
        shutil.rmtree(idir, ignore_errors=True)  # retried from scratch on the next run
        raise
    except Exception as e:
        status, patch = type(e).__name__, ""
        extra = {"traceback": traceback.format_exc()}
    finally:
        env.cleanup()
    agent.save(idir / f"{iid}.traj.json", {"info": {"exit_status": status, "submission": patch, **extra}})
    p, c = usage_of(agent.messages)
    with lock:
        with open(out_dir / "agent_usage.jsonl", "a") as f:
            f.write(json.dumps({"instance_id": iid, "exit_status": status, "api_calls": agent.n_calls,
                                "cost": agent.cost, "patch_chars": len(patch),
                                "traj": {"usage": {"prompt_tokens": p, "completion_tokens": c}}}) + "\n")
        with open(out_dir / "all_preds.jsonl", "a") as f:
            f.write(json.dumps({"instance_id": iid, "model_name_or_path": f"mini-swe-agent_{args.model}",
                                "model_patch": patch}) + "\n")
    print(f"[{time.strftime('%d/%m %H:%M:%S')}] {iid}: {status}, {agent.n_calls} calls, "
          f"{p:,}/{c:,} tokens, US$ {agent.cost:.4f}, patch {len(patch)} chars", flush=True)
    return agent.cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--provider", choices=PROVIDERS, default="gemini")
    ap.add_argument("--model", default="gemini-3.1-flash-lite")
    ap.add_argument("--step-limit", type=int, default=50)
    ap.add_argument("--cost-limit", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0, help="ignored when a reasoning effort is set")
    ap.add_argument("--budget", type=float, default=0.0, help="stop once the run's total cost reaches this (US$, 0 = no cap)")
    ap.add_argument("--no-autosubmit", dest="autosubmit", action="store_false")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    ids = [l.strip() for l in open(args.ids) if l.strip()]
    rows = []
    if (out_dir / "agent_usage.jsonl").exists():
        rows = [json.loads(l) for l in open(out_dir / "agent_usage.jsonl") if l.strip()]
    done = {r["instance_id"] for r in rows}
    spent = [sum(r.get("cost", 0.0) for r in rows)]
    todo = [i for i in ids if i not in done]
    print(f"{len(done)} done, {len(todo)} to go, US$ {spent[0]:.3f} spent", flush=True)
    if not todo:
        return 0

    from datasets import load_dataset
    by_id = {x["instance_id"]: x for x in load_dataset("princeton-nlp/SWE-bench_Lite", split="test")}

    base = yaml.safe_load(open(builtin_config_dir / "benchmarks" / "swebench.yaml"))
    prov = PROVIDERS[args.provider]
    penv = lambda k, d: os.environ.get(f"{prov['prefix']}_{k}") or d
    RateLimitedModel.limiter = Limiter(int(penv("RPM", prov["rpm"])), int(penv("TPM", prov["tpm"])))
    RateLimitedModel.prices = PRECOS[args.model]
    RateLimitedModel.api_key = os.environ[f"{prov['prefix']}_API_KEY"]
    effort = penv("REASONING_EFFORT", prov["effort"])
    model_kwargs = {"extra_body": {"reasoning_effort": effort}} if effort else {}
    if prov["api_base"]:
        model_kwargs["api_base"] = prov["api_base"]
    # OpenAI reasoning models reject temperature; Gemini accepts it alongside reasoning_effort
    if args.provider == "gemini" or not effort:
        model_kwargs["temperature"] = args.temperature
    cfg = {
        "agent": {**base["agent"], "step_limit": args.step_limit, "cost_limit": args.cost_limit},
        "environment": {**base["environment"], "environment_class": "docker"},
        "model": {
            **{k: base["model"][k] for k in ("observation_template", "format_error_template")},
            "model_name": f"openai/{args.model}",
            "cost_tracking": "ignore_errors",
            "model_kwargs": model_kwargs,
        },
    }

    lock = threading.Lock()
    stop = threading.Event()
    code = [0]

    def worker(queue):
        while queue and not stop.is_set():
            with lock:
                if not queue:
                    return
                if args.budget and spent[0] >= args.budget:
                    print(f"budget of US$ {args.budget} reached; stopping", flush=True)
                    code[0] = 4
                    stop.set()
                    return
                inst = by_id[queue.pop(0)]
            try:
                spent[0] += run_instance(inst, out_dir, cfg, args, lock)
            except DailyQuotaExceeded:
                print("daily quota exhausted; stopping (rerun after it renews)", flush=True)
                code[0] = 3
                stop.set()
            except CreditsExhausted as e:
                print(f"out of API credits ({e}); stopping", flush=True)
                code[0] = code[0] or 2
                stop.set()
            except ApiFailure as e:
                print(f"API failing after retries ({e}); stopping", flush=True)
                code[0] = code[0] or 2
                stop.set()

    threads = [threading.Thread(target=worker, args=(todo,)) for _ in range(args.workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return code[0]


if __name__ == "__main__":
    sys.exit(main())
