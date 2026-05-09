import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from src.config import Config
from src.client import TShellClient

console = Console()

async def setup_credentials(config: Config):
    console.print("\n[bold cyan]T-Shell Authentication Setup[/bold cyan]\n")

    api_id = Prompt.ask("[yellow]Enter your Telegram API ID[/yellow]")
    api_hash = Prompt.ask("[yellow]Enter your Telegram API Hash[/yellow]")
    phone = Prompt.ask("[yellow]Enter your phone number (with country code)[/yellow]")

    config.save_credentials(api_id, api_hash, phone)
    console.print("[green]Credentials saved successfully![/green]\n")

async def display_dashboard(client: TShellClient):
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]T-Shell Dashboard[/bold cyan]",
        border_style="cyan"
    ))

    dialogs = await client.get_dialogs(limit=10)

    table = Table(show_header=True, header_style="bold magenta", border_style="blue")
    table.add_column("#", justify="center", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Type", justify="center")
    table.add_column("Last Message", style="dim")

    for idx, dialog in enumerate(dialogs, 1):
        entity = dialog.entity
        name = getattr(entity, 'first_name', None) or getattr(entity, 'title', 'Unknown')
        entity_type = type(entity).__name__
        last_msg = dialog.message.text[:50] + "..." if dialog.message and dialog.message.text else "No messages"

        table.add_row(str(idx), str(name), entity_type, last_msg)

    console.print(table)
    console.print(f"\n[dim]Showing {len(dialogs)} recent conversations[/dim]")

async def main():
    config = Config()

    if not config.has_credentials():
        setup = Confirm.ask("[yellow]No credentials found. Would you like to set them up now?[/yellow]")
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
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())