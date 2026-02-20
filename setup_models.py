# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false
"""
Interactive CLI to configure OpenAI models and connection settings.
Run: python setup_models.py
"""

from __future__ import annotations

import getpass
from collections.abc import Iterable
from pathlib import Path

from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text


ENV_PATH = Path(".env")

MANAGED_KEYS = {
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "AI_MODEL",
    "REASONING_MODEL",
    "REASONING_PROVIDER",
}


def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def write_env(updates: dict[str, str]) -> None:
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    updated_keys: set[str] = set()
    output_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            comment_content = stripped[1:].strip()
            if "=" in comment_content:
                comment_key = comment_content.split("=", 1)[0].strip()
                if comment_key in updates:
                    value = updates[comment_key]
                    ending = "\n" if line.endswith("\n") else ""
                    if value == "":
                        output_lines.append(f"# {comment_key}={ending}")
                    else:
                        output_lines.append(f"{comment_key}={value}{ending}")
                    updated_keys.add(comment_key)
                    continue
            output_lines.append(line)
            continue
        if not stripped or "=" not in line:
            output_lines.append(line)
            continue

        key, _ = line.split("=", 1)
        key = key.strip()
        if key not in updates:
            output_lines.append(line)
            continue

        value = updates[key]
        ending = "\n" if line.endswith("\n") else ""
        if value == "":
            output_lines.append(f"# {key}={ending}")
        else:
            output_lines.append(f"{key}={value}{ending}")
        updated_keys.add(key)

    for key, value in updates.items():
        if key in updated_keys:
            continue
        if value == "":
            output_lines.append(f"# {key}=\n")
        else:
            output_lines.append(f"{key}={value}\n")

    _ = ENV_PATH.write_text("".join(output_lines), encoding="utf-8")


def mask(secret: str) -> str:
    if not secret:
        return "(not set)"
    if len(secret) <= 12:
        start = secret[:4]
        end = secret[-4:] if len(secret) >= 4 else ""
        return f"{start}****{end}"
    return f"{secret[:8]}...{secret[-4:]}"


def show_current_config(console: Console, env: dict[str, str]) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    api_key = env.get("OPENAI_API_KEY", "")
    base_url = env.get("OPENAI_BASE_URL", "")
    hint_model = env.get("AI_MODEL", "gpt-4o-mini")
    reasoning_model = env.get("REASONING_MODEL", "") or hint_model

    base_display = base_url or "(default -- api.openai.com)"

    table.add_row("API Key", mask(api_key))
    table.add_row("Base URL", base_display)
    table.add_row("Hint Model", hint_model)
    table.add_row("Reasoning Model", reasoning_model)

    console.print(table)


def _safe_prompt(text: str, default: str) -> str:
    try:
        return Prompt.ask(text, default=default)
    except EOFError:
        return default


def _safe_confirm(text: str, default: bool) -> bool:
    try:
        return Confirm.ask(text, default=default)
    except EOFError:
        return default


def prompt_connection(console: Console, env: dict[str, str]) -> tuple[str, str]:
    show_current_config(console, env)
    if not _safe_confirm("Edit connection settings?", default=False):
        return env.get("OPENAI_API_KEY", ""), env.get("OPENAI_BASE_URL", "")

    current_key = env.get("OPENAI_API_KEY", "")
    if current_key:
        masked = mask(current_key)
        entered = _safe_prompt("API Key", default=masked)
        api_key = current_key if entered == masked or entered.strip() == "" else entered.strip()
    else:
        try:
            api_key = getpass.getpass("API Key: ").strip()
        except EOFError:
            api_key = ""

    current_base = env.get("OPENAI_BASE_URL", "")
    base_default = current_base or "(default)"
    base_input = _safe_prompt("Base URL", default=base_default).strip()
    base_url = "" if base_input == "(default)" else base_input

    return api_key, base_url


def _relevance_score(model_id: str) -> int:
    name = model_id.lower()
    priorities = [
        ("gpt-4o-mini", 1000),
        ("gpt-4o", 950),
        ("gpt-4.1-", 900),
        ("gpt-3.5-turbo", 850),
        ("o1-", 820),
        ("o3-mini", 810),
        ("o4-mini", 800),
        ("claude", 760),
        ("gemini", 740),
        ("llama", 720),
        ("mistral", 700),
        ("deepseek", 680),
        ("qwen", 660),
    ]
    for token, score in priorities:
        if token.endswith("-") and name.startswith(token):
            return score
        if token in name:
            return score
    return 0


def _is_hidden_model(model_id: str) -> bool:
    name = model_id.lower()
    hidden_tokens = [
        "embed",
        "embedding",
        "tts",
        "whisper",
        "dall-e",
        "davinci",
        "babbage",
        "moderation",
    ]
    return any(token in name for token in hidden_tokens)


def _sort_models(models: Iterable[str]) -> list[str]:
    unique = list(dict.fromkeys(models))
    return sorted(unique, key=lambda m: (-_relevance_score(m), m))


def fetch_models(console: Console, api_key: str, base_url: str) -> list[str]:
    try:
        with console.status("[bold]Fetching models from API...", spinner="dots"):
            client = OpenAI(api_key=api_key, base_url=base_url or None)
            response = client.models.list()
            model_ids = [model.id for model in response.data]
        models = _sort_models(model_ids)
        console.print(f"[bold green]OK Found {len(models)} models[/bold green]")
        return models
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]! Unable to fetch models: {exc}[/yellow]")
        return []


def pick_model(
    console: Console,
    models: list[str],
    purpose: str,
    description: str,
    current: str,
) -> str:
    if not models:
        console.print("[yellow]No models available from API.[/yellow]")
        fallback = _safe_prompt(f"Select model for {purpose}", default=current or "").strip()
        return fallback or current

    show_all = False
    filter_text = ""
    page = 0
    page_size = 20

    while True:
        filtered = models
        if filter_text:
            filtered = [m for m in filtered if filter_text.lower() in m.lower()]

        hidden_count = 0
        if not show_all:
            hidden_count = sum(1 for m in filtered if _is_hidden_model(m))
            visible = [m for m in filtered if not _is_hidden_model(m)]
        else:
            visible = list(filtered)

        if not visible:
            console.print("[yellow]No models match that filter.[/yellow]")
            filter_text = ""
            continue

        total_pages = max(1, (len(visible) + page_size - 1) // page_size)
        page = max(0, min(page, total_pages - 1))
        start = page * page_size
        page_models = visible[start : start + page_size]

        console.print()
        console.print(f"Select a model for {purpose} -- {description}")

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", justify="right", width=3)
        table.add_column("Model")
        table.add_column("")

        for idx, model_id in enumerate(page_models, start=1):
            marker = ""
            model_text: Text | str = model_id
            if model_id == current:
                model_text = Text(model_id, style="bold green")
                marker = Text("<- current", style="bold green")
            table.add_row(str(idx), model_text, marker)

        console.print(table)
        console.print(f"Page {page + 1}/{total_pages}  |  {hidden_count} non-chat models hidden")
        console.print("\\[n]ext  \\[p]rev  \\[f]ilter  \\[a]ll")

        selection = _safe_prompt("Select # or type model name", default=current or "").strip()

        if selection == "" and current:
            return current
        if selection.lower() == "n":
            page = (page + 1) % total_pages
            continue
        if selection.lower() == "p":
            page = (page - 1) % total_pages
            continue
        if selection.lower() == "a":
            show_all = not show_all
            page = 0
            continue
        if selection.lower() == "f":
            filter_text = _safe_prompt("Filter", default=filter_text).strip()
            page = 0
            continue

        if selection.isdigit():
            index = int(selection) - 1
            if 0 <= index < len(page_models):
                return page_models[index]
            console.print("[yellow]Invalid selection number.[/yellow]")
            continue

        return selection or current


def show_summary(
    console: Console,
    api_key: str,
    base_url: str,
    hint_model: str,
    reasoning_model: str,
) -> None:
    base_display = base_url or "(default)"
    summary = Table.grid(padding=(0, 2))
    summary.add_column(justify="right", style="bold")
    summary.add_column()
    summary.add_row("API Key:", mask(api_key))
    summary.add_row("Base URL:", base_display)
    summary.add_row("Hint Model:", Text(hint_model, style="bold cyan"))
    summary.add_row("Reasoning Model:", Text(reasoning_model, style="bold cyan"))

    console.print(Panel(summary, title="Summary"))


def main() -> None:
    console = Console()
    title = Text("NeuronLab -- AI Model Setup", justify="center")
    console.print(Panel(title))
    console.print()

    env = read_env()

    console.print("[1/3] OpenAI Connection")
    console.print()
    api_key, base_url = prompt_connection(console, env)
    write_env({"OPENAI_API_KEY": api_key, "OPENAI_BASE_URL": base_url})

    console.print()
    console.print("[2/3] Fetch Models")
    console.print()
    models = fetch_models(console, api_key, base_url)

    console.print()
    console.print("[3/3] Assign Models")

    hint_current = env.get("AI_MODEL", "gpt-4o-mini")
    reasoning_current = env.get("REASONING_MODEL", "") or hint_current

    hint_model = pick_model(
        console,
        models,
        "hints",
        "fast, cheap, used for code debugging hints",
        hint_current,
    )
    reasoning_model = pick_model(
        console,
        models,
        "reasoning",
        "higher quality model for chain-of-thought reasoning",
        reasoning_current,
    )

    console.print()
    show_summary(console, api_key, base_url, hint_model, reasoning_model)

    if _safe_confirm("Save to .env?", default=True):
        write_env(
            {
                "OPENAI_API_KEY": api_key,
                "OPENAI_BASE_URL": base_url,
                "AI_MODEL": hint_model,
                "REASONING_MODEL": reasoning_model,
                "REASONING_PROVIDER": "openai",
            }
        )
        console.print("[bold green]Done! .env updated! Restart the server to apply changes.[/bold green]")
    else:
        console.print("[yellow]Aborted. No changes saved.[/yellow]")


if __name__ == "__main__":
    main()
