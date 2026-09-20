"""三方案对比评估脚本。

方案 A：一次性提示词打分（不要求证据）
方案 B：带证据检索（要求引用原文）
方案 C：循证评阅（本产品：证据状态 + 档位校验 + 矛盾检测 + 待复核 + 重试）

评估指标：准确性（档位命中率）、覆盖率、错误放行（ground truth 为最低档却给了高分）、成本（token）、耗时。

运行：PYTHONPATH= uv run --project backend python backend/scripts/evaluate.py
"""
import time

from app.services.ai_client import get_llm
from app.services.grading.json_utils import extract_json
from app.services.grading.prompts import SYSTEM_PROMPT, build_user_prompt

BANDS = ["优秀", "良好", "及格", "不及格"]
BAND_SCORE = {"优秀": 40, "良好": 30, "及格": 20, "不及格": 0}

ITEMS = [
    {"name": "算法实现正确性", "bands": BANDS},
    {"name": "复杂度分析", "bands": BANDS},
]

# 模拟报告 + 教师 ground truth
REPORTS = [
    {
        "name": "完整正确报告",
        "text": (
            "# 排序算法实验报告\n\n"
            "## 算法实现\n"
            "本实验实现了快速排序算法，核心是分治：选取基准，将数组划分为小于和大于基准的两部分，递归排序。\n\n"
            "```python\ndef quicksort(arr):\n"
            "    if len(arr) <= 1:\n        return arr\n"
            "    pivot = arr[len(arr)//2]\n"
            "    left = [x for x in arr if x < pivot]\n"
            "    right = [x for x in arr if x > pivot]\n"
            "    return quicksort(left) + [pivot] + quicksort(right)\n```\n\n"
            "## 复杂度分析\n"
            "快速排序平均时间复杂度为 O(n log n)，最坏 O(n²)；空间复杂度 O(log n)。\n\n"
            "## 实验结果\n"
            "| 数据规模 | 运行时间(ms) |\n| --- | --- |\n| 1000 | 1.2 |\n| 10000 | 15.3 |\n| 100000 | 198.7 |\n"
        ),
        "ground_truth": {"算法实现正确性": "优秀", "复杂度分析": "优秀"},
    },
    {
        "name": "缺复杂度分析",
        "text": (
            "# 排序算法实验报告\n\n"
            "## 算法实现\n"
            "本实验实现了冒泡排序算法。\n\n"
            "```python\ndef bubble_sort(arr):\n"
            "    n = len(arr)\n"
            "    for i in range(n):\n"
            "        for j in range(0, n-i-1):\n"
            "            if arr[j] > arr[j+1]:\n"
            "                arr[j], arr[j+1] = arr[j+1], arr[j]\n"
            "    return arr\n```\n"
        ),
        "ground_truth": {"算法实现正确性": "良好", "复杂度分析": "不及格"},
    },
]


def _find_band(text: str) -> str | None:
    for b in BANDS:
        if b in text:
            return b
    return None


def grade_baseline(llm, report: str, item: dict) -> dict:
    prompt = (
        f"你是实验报告评阅助教。评分项：{item['name']}。可选档位：{'/'.join(item['bands'])}。\n"
        f"报告：\n{report}\n\n"
        f"请给该评分项打分，只输出档位名（{'/'.join(item['bands'])}之一）。"
    )
    r = llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=2000)
    return {
        "band": _find_band(r.content),
        "usage": r.usage.get("total_tokens", 0),
        "elapsed": r.elapsed_seconds,
    }


def grade_evidence(llm, report: str, item: dict) -> dict:
    prompt = (
        f"你是实验报告评阅助教。评分项：{item['name']}。可选档位：{'/'.join(item['bands'])}。\n"
        f"报告：\n{report}\n\n"
        "请给该评分项打分，并逐字引用原文证据。只输出 JSON："
        '{"band": "档位名", "quotes": ["原文片段"]}'
    )
    r = llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=2000)
    parsed = extract_json(r.content)
    band = parsed.get("band") if parsed else None
    if band not in item["bands"]:
        band = None
    return {
        "band": band,
        "usage": r.usage.get("total_tokens", 0),
        "elapsed": r.elapsed_seconds,
    }


def grade_review(llm, report: str, item: dict) -> dict:
    """方案 C：复用循证评阅的完整流程（prompt + 档位校验 + 待复核 + 重试）。"""
    bands_dict = [{"level": b, "score": BAND_SCORE[b], "description": ""} for b in item["bands"]]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(item["name"], "", bands_dict, report)},
    ]
    r = llm.chat(messages, temperature=0.0, max_tokens=2000)
    parsed = extract_json(r.content)
    usage = r.usage.get("total_tokens", 0)
    elapsed = r.elapsed_seconds

    if parsed is None:
        messages.append(
            {"role": "user", "content": "你上一次没有输出合法 JSON。请重新输出，只输出一个合法 JSON 对象。"}
        )
        r2 = llm.chat(messages, temperature=0.0, max_tokens=2000)
        parsed = extract_json(r2.content)
        usage += r2.usage.get("total_tokens", 0)
        elapsed += r2.elapsed_seconds

    if parsed is None:
        return {"band": None, "evidence_state": "uncertain", "needs_review": True, "usage": usage, "elapsed": elapsed}

    band = parsed.get("suggested_band")
    state = parsed.get("evidence_state")
    if band not in item["bands"]:
        band = None
    needs_review = state == "uncertain" or band is None
    return {
        "band": band,
        "evidence_state": state,
        "needs_review": needs_review,
        "usage": usage,
        "elapsed": elapsed,
    }


SCHEMES = {
    "A 一次性打分": grade_baseline,
    "B 带证据": grade_evidence,
    "C 循证评阅": grade_review,
}


def main() -> None:
    llm = get_llm()
    if llm is None:
        print("LLM 未配置，请检查 .env")
        return

    results = {name: {"hits": 0, "total": 0, "covered": 0, "false_pass": 0, "tokens": 0, "elapsed": 0.0} for name in SCHEMES}

    print(f"模型：{llm.model}\n")
    print("=" * 72)

    for rpt in REPORTS:
        print(f"\n【报告】{rpt['name']}")
        for item in ITEMS:
            gt = rpt["ground_truth"][item["name"]]
            row = f"  {item['name']:<10} ground_truth={gt:<4} |"
            for scheme, fn in SCHEMES.items():
                out = fn(llm, rpt["text"], item)
                band = out["band"]
                res = results[scheme]
                res["tokens"] += out["usage"]
                res["elapsed"] += out["elapsed"]
                res["total"] += 1
                if band is not None:
                    res["covered"] += 1
                    if band == gt:
                        res["hits"] += 1
                    # 错误放行：ground truth 是最低档，却给了高两档以上
                    if gt == "不及格" and band in ("优秀", "良好"):
                        res["false_pass"] += 1
                label = band if band else ("待复核" if out.get("needs_review") else "—")
                mark = "✓" if band == gt else ("⚠" if band is not None else "·")
                row += f" {scheme[:1]}={label}{mark} |"
            print(row)

    print("\n" + "=" * 72)
    print("\n【汇总对比】")
    print(f"{'方案':<14}{'准确性':<10}{'覆盖率':<10}{'错误放行':<10}{'token':<10}{'耗时(s)':<10}")
    for scheme, res in results.items():
        acc = f"{res['hits']}/{res['total']} ({res['hits']/res['total']*100:.0f}%)" if res["total"] else "-"
        cov = f"{res['covered']}/{res['total']}"
        print(
            f"{scheme:<14}{acc:<10}{cov:<10}{res['false_pass']:<10}"
            f"{res['tokens']:<10}{res['elapsed']:.1f}"
        )


if __name__ == "__main__":
    main()
