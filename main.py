import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

from src.config import Config
from src.client import TShellClient

console = Console()

async def setup_credentials(config: Config):
    console.print("\n")
    with Panel(
        Text("T-Shell Authentication Setup", style="bold cyan"),
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    ) as panel:
        console.print(panel)

    api_id = Prompt.ask("  [yellow]API ID[/yellow]")
    api_hash = Prompt.ask("  [yellow]API Hash[/yellow]")
    phone = Prompt.ask("  [yellow]Phone (with country code)[/yellow]")

    config.save_credentials(api_id, api_hash, phone)
    console.print("\n  [green]✓[/green] Credentials saved!\n")

def get_entity_icon(entity) -> str:
    from telethon.tl.types import User, Channel, Chat
    if isinstance(entity, User):
        return "[blue]👤[/blue]"
    elif isinstance(entity, Channel):
        return "[magenta]📢[/magenta]"
    elif isinstance(entity, Chat):
        return "[green]👥[/green]"
    return "💬"

def format_message(message) -> str:
    if not message or not message.text:
        return "[dim]No messages[/dim]"
    text = message.text.strip()
    if len(text) > 60:
        return text[:57] + "..."
    return text

async def display_dashboard(client: TShellClient):
    console.clear()
    
    me = await client.get_me()
    
    header = Panel(
        f"  [cyan]Logged in as[/cyan] [bold white]{me.first_name}[/bold white] [dim]@{me.username or 'no username'}[/dim]\n"
        f"  [dim]ID:[/dim] [cyan]{me.id}[/cyan]",
        title="[bold cyan]T-Shell[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    )
    console.print(header)
    console.print()

    dialogs = await client.get_dialogs(limit=10)

    table = Table(
        box=box.DOUBLE,
        border_style="cyan",
        header_style="bold cyan",
        row_styles=["", "dim"],
        show_lines=True
    )
    table.add_column("  #", justify="right", style="cyan", width=4)
    table.add_column("Type", justify="center", width=5)
    table.add_column("Name", style="bold white", min_width=30, max_width=40)
    table.add_column("Last Message", style="dim", max_width=50)

    for idx, dialog in enumerate(dialogs, 1):
        entity = dialog.entity
        name = getattr(entity, 'first_name', None) or getattr(entity, 'title', 'Unknown')
        icon = get_entity_icon(entity)
        msg = format_message(dialog.message)
        
        table.add_row(
            f"[cyan]{idx}[/cyan]",
            icon,
            str(name),
            msg
        )

    console.print(table)
    console.print()
    
    footer = Panel(
        "[dim]Press [yellow]Enter[/yellow] to refresh · [yellow]Ctrl+C[/yellow] to quit[/dim]",
        border_style="dim",
        box=box.SIMPLE,
        padding=(0, 1)
    )
    console.print(footer, justify="center")

async def main():
    config = Config()

    if not config.has_credentials():
        setup = Confirm.ask("[yellow]No credentials found. Set up now?[/yellow]")
        if setup:
            await setup_credentials(config)
        else:
            console.print("[red]Cannot proceed without credentials.[/red]")
            sys.exit(1)

    client = TShellClient(config)

    try:
        await client.start()
        await display_dashboard(client)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())