#!/usr/bin/env python3
"""Batchowy benchmark modeli GGUF uruchamianych przez llama.cpp.

Dla każdego modelu skrypt uruchamia osobny proces llama-server, czeka na
załadowanie modelu, wysyła pytania równolegle do API zgodnego z OpenAI,
zapisuje odpowiedzi do JSONL, a następnie zatrzymuje serwer i zwalnia GPU.

Pierwsze uruchomienie może obejmować pobieranie plików GGUF. Aby porównywać
sam czas ładowania modeli, warto wykonać właściwy benchmark po rozgrzaniu cache.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


# Klucze są identyczne z model_id używanymi w run_models_vllm.py, dzięki czemu
# wyniki obu backendów można łatwo ze sobą zestawić.
DEFAULT_GGUF_MODELS = {
    "CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412": (
        "mradermacher/Llama-PLLuM-8B-instruct-GGUF"
    ),
    "meta-llama/Llama-3.1-8B-Instruct": (
        "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
    ),
    "speakleash/Bielik-11B-v2.3-Instruct": (
        "speakleash/Bielik-11B-v2.3-Instruct-GGUF"
    ),
    "mistralai/Mistral-7B-Instruct-v0.2": (
        "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
    ),
}

MODELS_WITHOUT_SYSTEM_ROLE = {
    "mistralai/Mistral-7B-Instruct-v0.2",
}

SYSTEM_PROMPT = (
    "Odpowiedz na pytanie krótko i konkretnie. "
    "Podaj wyłącznie odpowiedź, bez uzasadnienia."
)


def default_server_path() -> Path:
    executable = shutil.which("llama-server")
    return Path(executable) if executable else Path("llama-server")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Uruchom modele GGUF przez llama.cpp na pytaniach z JSONL."
    )
    parser.add_argument("--input", type=Path, default=Path("pytania.jsonl"))
    parser.add_argument(
        "--output", type=Path, default=Path("odpowiedzi_llamacpp.jsonl")
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_GGUF_MODELS),
        help=(
            "Identyfikatory modeli bazowych. Dla czterech modeli domyślnych "
            "skrypt automatycznie wybiera odpowiadające repozytoria GGUF."
        ),
    )
    parser.add_argument(
        "--quantization",
        default="Q4_K_M",
        help="Kwantyzacja wybierana z repozytorium GGUF (domyślnie: Q4_K_M).",
    )
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=1024,
        help="Maksymalny kontekst pojedynczego równoległego żądania.",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=16,
        help="Liczba slotów llama-server i równoległych żądań HTTP.",
    )
    parser.add_argument(
        "--gpu-layers",
        default="999",
        help="Wartość przekazywana do -ngl (np. 999, all albo 0).",
    )
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--threads-batch", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--ubatch-size", type=int, default=512)
    parser.add_argument(
        "--cache-prompt",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Włącz ponowne używanie wspólnych fragmentów promptów. Domyślnie "
            "wyłączone, aby każde pytanie było przetwarzane niezależnie."
        ),
    )
    parser.add_argument(
        "--llama-server",
        type=Path,
        default=default_server_path(),
        help="Ścieżka do pliku wykonywalnego llama-server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port serwera; 0 wybiera automatycznie wolny port.",
    )
    parser.add_argument("--load-timeout", type=float, default=3600.0)
    parser.add_argument("--request-timeout", type=float, default=600.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.max_new_tokens < 1:
        raise ValueError("--max-new-tokens musi być większe od zera.")
    if args.max_model_len < args.max_new_tokens:
        raise ValueError("--max-model-len nie może być mniejsze niż --max-new-tokens.")
    if args.parallel < 1:
        raise ValueError("--parallel musi być większe od zera.")
    if args.batch_size < 1 or args.ubatch_size < 1:
        raise ValueError("--batch-size i --ubatch-size muszą być większe od zera.")
    if args.temperature < 0:
        raise ValueError("--temperature nie może być ujemne.")
    if not 0 < args.top_p <= 1:
        raise ValueError("--top-p musi być w zakresie (0, 1].")
    if args.max_questions is not None and args.max_questions < 1:
        raise ValueError("--max-questions musi być większe od zera.")
    if not 0 <= args.port <= 65535:
        raise ValueError("--port musi być w zakresie 0-65535.")
    if args.load_timeout <= 0 or args.request_timeout <= 0:
        raise ValueError("Timeouty muszą być większe od zera.")

    unknown_models = [
        model_id for model_id in args.models if model_id not in DEFAULT_GGUF_MODELS
    ]
    if unknown_models:
        models = "\n  - ".join(unknown_models)
        raise ValueError(
            "Brak mapowania repozytorium GGUF dla modeli:\n"
            f"  - {models}\n"
            "Dodaj je do DEFAULT_GGUF_MODELS w skrypcie."
        )

    executable = shutil.which(str(args.llama_server))
    if executable is None and not (
        args.llama_server.is_file() and os.access(args.llama_server, os.X_OK)
    ):
        raise FileNotFoundError(
            f"Nie znaleziono llama-server: {args.llama_server}. "
            "Podaj poprawną ścieżkę przez --llama-server."
        )


def read_questions(path: Path, limit: int | None) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                item = {
                    "id": str(record["id"]),
                    "question": str(record["question_pl"]),
                }
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(
                    f"Niepoprawny rekord w {path}, linia {line_number}: {exc}"
                ) from exc
            questions.append(item)
            if limit is not None and len(questions) >= limit:
                break

    if not questions:
        raise ValueError(f"Plik {path} nie zawiera pytań.")
    return questions


def read_completed(path: Path) -> set[tuple[str, str]]:
    completed: set[tuple[str, str]] = set()
    if not path.exists():
        return completed

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                parameters = record["model_parameters"]
                if parameters.get("backend") != "llama.cpp":
                    continue
                completed.add((str(parameters["model_id"]), str(record["id"])))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return completed


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


def build_server_command(
    args: argparse.Namespace, model_id: str, gguf_repo: str, port: int
) -> list[str]:
    # llama-server dzieli całkowity kontekst pomiędzy sloty.
    total_context = args.max_model_len * args.parallel
    command = [
        str(args.llama_server),
        "-hf",
        f"{gguf_repo}:{args.quantization}",
        "-ngl",
        str(args.gpu_layers),
        "-c",
        str(total_context),
        "-np",
        str(args.parallel),
        "-b",
        str(args.batch_size),
        "-ub",
        str(args.ubatch_size),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--alias",
        model_id,
        "--cont-batching",
        "--jinja",
        "--log-colors",
        "off",
    ]
    if args.threads is not None:
        command.extend(["--threads", str(args.threads)])
    if args.threads_batch is not None:
        command.extend(["--threads-batch", str(args.threads_batch)])
    return command


def wait_until_ready(
    process: subprocess.Popen[Any], base_url: str, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    last_error = "brak odpowiedzi serwera"

    while time.monotonic() < deadline:
        returncode = process.poll()
        if returncode is not None:
            raise RuntimeError(
                f"llama-server zakończył się podczas ładowania (kod {returncode})."
            )

        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2) as response:
                payload = json.loads(response.read())
                if response.status == 200 and payload.get("status") == "ok":
                    return
        except urllib.error.HTTPError as exc:
            # Kod 503 oznacza, że serwer działa, ale model nadal się ładuje.
            last_error = f"HTTP {exc.code}"
            exc.close()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)

        time.sleep(0.25)

    raise TimeoutError(
        f"llama-server nie załadował modelu w {timeout:.0f} s ({last_error})."
    )


def stop_server(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def messages_for_model(model_id: str, question: str) -> list[dict[str, str]]:
    if model_id in MODELS_WITHOUT_SYSTEM_ROLE:
        return [
            {
                "role": "user",
                "content": f"{SYSTEM_PROMPT}\n\nPytanie: {question}",
            }
        ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]


def request_completion(
    base_url: str,
    model_id: str,
    item: dict[str, str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    payload = {
        "model": model_id,
        "messages": messages_for_model(model_id, item["question"]),
        "max_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": 0,
        "min_p": 0.0,
        "seed": args.seed,
        "cache_prompt": args.cache_prompt,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    request_started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=args.request_timeout) as response:
            response_body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc
    latency_seconds = time.perf_counter() - request_started

    try:
        content = response_body["choices"][0]["message"].get("content") or ""
        usage = response_body["usage"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Niepoprawna odpowiedź llama-server: {response_body}") from exc

    return {
        "id": item["id"],
        "response": str(content).strip(),
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "output_tokens": int(usage.get("completion_tokens", 0)),
        "latency_seconds": latency_seconds,
        "server_timings": response_body.get("timings", {}),
    }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def generate_answers(
    base_url: str,
    model_id: str,
    gguf_repo: str,
    pending: list[dict[str, str]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    from tqdm import tqdm

    args.output.parent.mkdir(parents=True, exist_ok=True)
    latencies: list[float] = []
    prompt_tokens = 0
    output_tokens = 0
    errors: list[str] = []
    answers_generated = 0
    generation_started = time.perf_counter()

    with (
        args.output.open("a", encoding="utf-8", buffering=1) as output_file,
        ThreadPoolExecutor(max_workers=args.parallel) as executor,
        tqdm(total=len(pending), desc=model_id, unit="pyt.") as progress,
    ):
        futures = {
            executor.submit(request_completion, base_url, model_id, item, args): item
            for item in pending
        }
        for future in as_completed(futures):
            item = futures[future]
            try:
                answer = future.result()
            except Exception as exc:
                errors.append(f"pytanie {item['id']}: {exc}")
                progress.update(1)
                continue

            result = {
                "id": answer["id"],
                "response": answer["response"],
                "model_parameters": {
                    "model_id": model_id,
                    "backend": "llama.cpp",
                    "gguf_repo": gguf_repo,
                    "quantization": args.quantization,
                    "max_new_tokens": args.max_new_tokens,
                    "temperature": args.temperature,
                    "top_p": args.top_p,
                    "seed": args.seed,
                    "max_model_len": args.max_model_len,
                    "parallel": args.parallel,
                    "gpu_layers": str(args.gpu_layers),
                    "batch_size": args.batch_size,
                    "ubatch_size": args.ubatch_size,
                    "cache_prompt": args.cache_prompt,
                    "system_prompt": SYSTEM_PROMPT,
                },
            }
            output_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            output_file.flush()

            latencies.append(answer["latency_seconds"])
            prompt_tokens += answer["prompt_tokens"]
            output_tokens += answer["output_tokens"]
            answers_generated += 1
            progress.update(1)

    generation_seconds = time.perf_counter() - generation_started
    if errors:
        examples = "; ".join(errors[:3])
        remaining = len(errors) - 3
        suffix = f"; oraz {remaining} kolejnych" if remaining > 0 else ""
        raise RuntimeError(
            f"Nie udało się wygenerować {len(errors)} odpowiedzi: {examples}{suffix}"
        )

    return {
        "generation_seconds": generation_seconds,
        "answers_generated": answers_generated,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "average_latency_seconds": sum(latencies) / len(latencies),
        "p50_latency_seconds": percentile(latencies, 0.50),
        "p95_latency_seconds": percentile(latencies, 0.95),
    }


def run_model(
    args: argparse.Namespace,
    model_id: str,
    questions: list[dict[str, str]],
    completed: set[tuple[str, str]],
) -> dict[str, Any]:
    model_started = time.perf_counter()
    gguf_repo = DEFAULT_GGUF_MODELS[model_id]
    pending = [item for item in questions if (model_id, item["id"]) not in completed]
    if not pending:
        print(f"[{model_id}] Wszystkie pytania są już zapisane.")
        return {
            "model_id": model_id,
            "gguf_repo": gguf_repo,
            "status": "skipped",
            "process_seconds": time.perf_counter() - model_started,
        }

    port = args.port or find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    command = build_server_command(args, model_id, gguf_repo, port)
    print(f"[{model_id}] Pozostało pytań: {len(pending)}")
    print(f"[{model_id}] Repozytorium GGUF: {gguf_repo}:{args.quantization}")

    load_started = time.perf_counter()
    process = subprocess.Popen(command)
    try:
        wait_until_ready(process, base_url, args.load_timeout)
        load_seconds = time.perf_counter() - load_started
        print(f"[{model_id}] Model załadowany. Rozpoczynam generowanie.")
        generation_stats = generate_answers(
            base_url, model_id, gguf_repo, pending, args
        )
    finally:
        stop_server(process)

    return {
        "model_id": model_id,
        "gguf_repo": gguf_repo,
        "status": "completed",
        "load_seconds": load_seconds,
        "process_seconds": time.perf_counter() - model_started,
        **generation_stats,
    }


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)} min {remaining_seconds:.1f} s"
    hours, remaining_minutes = divmod(int(minutes), 60)
    return f"{hours} h {remaining_minutes} min {remaining_seconds:.0f} s"


def print_benchmark_stats(
    model_stats: list[dict[str, Any]], benchmark_seconds: float
) -> None:
    print("\n=== Statystyki benchmarku llama.cpp ===")
    for stats in model_stats:
        print(f"\n{stats['model_id']}")
        if stats["status"] == "failed":
            print(f"  Status: błąd — {stats['error']}")
            print(f"  Czas do błędu: {format_duration(stats['process_seconds'])}")
            continue
        if stats["status"] == "skipped":
            print("  Status: pominięty — wszystkie odpowiedzi były już zapisane")
            continue

        generation_seconds = stats["generation_seconds"]
        answers_per_second = stats["answers_generated"] / generation_seconds
        tokens_per_second = stats["output_tokens"] / generation_seconds
        print(f"  Repozytorium: {stats['gguf_repo']}")
        print(f"  Wygenerowane odpowiedzi: {stats['answers_generated']}")
        print(f"  Ładowanie modelu: {format_duration(stats['load_seconds'])}")
        print(
            "  Generowanie wszystkich odpowiedzi: "
            f"{format_duration(generation_seconds)}"
        )
        print(
            "  Latencja żądania (średnia / p50 / p95): "
            f"{format_duration(stats['average_latency_seconds'])} / "
            f"{format_duration(stats['p50_latency_seconds'])} / "
            f"{format_duration(stats['p95_latency_seconds'])}"
        )
        print(f"  Przepustowość: {answers_per_second:.2f} odp./s")
        print(f"  Tokeny wejściowe: {stats['prompt_tokens']}")
        print(
            f"  Tokeny wyjściowe: {stats['output_tokens']} "
            f"({tokens_per_second:.2f} tokenów/s)"
        )
        print(f"  Cały proces modelu: {format_duration(stats['process_seconds'])}")

    completed = [stats for stats in model_stats if stats["status"] == "completed"]
    skipped = [stats for stats in model_stats if stats["status"] == "skipped"]
    print("\nPodsumowanie")
    print(f"  Modele z nowymi odpowiedziami: {len(completed)}")
    print(f"  Modele pominięte przy wznowieniu: {len(skipped)}")
    print(
        "  Wygenerowane odpowiedzi łącznie: "
        f"{sum(stats['answers_generated'] for stats in completed)}"
    )
    print(
        "  Suma czasów ładowania: "
        f"{format_duration(sum(stats['load_seconds'] for stats in completed))}"
    )
    print(
        "  Suma czasów generowania: "
        f"{format_duration(sum(stats['generation_seconds'] for stats in completed))}"
    )
    print(f"  Całkowity czas benchmarku: {format_duration(benchmark_seconds)}")


def main() -> int:
    args = parse_args()
    validate_args(args)
    benchmark_started = time.perf_counter()

    if args.overwrite and args.output.exists():
        args.output.unlink()

    questions = read_questions(args.input, args.max_questions)
    completed_answers = read_completed(args.output)
    model_stats: list[dict[str, Any]] = []

    for model_id in args.models:
        print(f"\n=== Uruchamianie modelu: {model_id} ===")
        model_started = time.perf_counter()
        try:
            stats = run_model(args, model_id, questions, completed_answers)
        except Exception as exc:
            stats = {
                "model_id": model_id,
                "status": "failed",
                "error": str(exc),
                "process_seconds": time.perf_counter() - model_started,
            }
            model_stats.append(stats)
            print_benchmark_stats(
                model_stats, time.perf_counter() - benchmark_started
            )
            print(
                f"Benchmark zatrzymany na modelu {model_id}. "
                "Ponowne uruchomienie wznowi pracę.",
                file=sys.stderr,
            )
            return 1
        model_stats.append(stats)

    print("\nWszystkie modele zakończone.")
    print_benchmark_stats(model_stats, time.perf_counter() - benchmark_started)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nPrzerwano. Ponowne uruchomienie wznowi pracę.")
        raise SystemExit(130)
