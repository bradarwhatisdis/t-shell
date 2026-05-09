import asyncio
import sys
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.live import Live

from src.config import Config
from src.client import TShellClient

console = Console()

NORD_COLORS = {
    "bg": "#2E3440",
    "bg_light": "#3B4252",
    "accent": "#88C0D0",
    "accent_bright": "#81A1C1",
    "text": "#ECEFF4",
    "text_dim": "#D8DEE9",
    "user": "#88C0D0",
    "channel": "#B48EAD",
    "bot": "#A3BE8C",
    "success": "#A3BE8C",
    "warning": "#EBCB8B",
    "error": "#BF616A",
}

class TShellUI:
    def __init__(self):
        self.layout = Layout()
        self.selected_chat = None
        self.me = None
        self.dialogs = []

    def create_layout(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )
        layout["main"].split_row(
            Layout(name="sidebar", ratio=1),
            Layout(name="chat_view", ratio=2),
        )
        return layout

    def render_header(self) -> Panel:
        username = f"@{self.me.username}" if self.me.username else "no username"
        user_display = f"[{NORD_COLORS['accent_bright']}]{self.me.first_name}[/{NORD_COLORS['accent_bright']}] [dim]({username})[/dim]"

        content = Text.assemble(
            f"  [bold {NORD_COLORS['accent']}]t-shell[/bold {NORD_COLORS['accent']}]",
            "  │  ",
            user_display,
            "  │  ",
            f"[dim]ID: {self.me.id}[/dim]",
        )

        return Panel(
            content,
            border_style=NORD_COLORS['accent'],
            box=box.ROUNDED,
            padding=(0, 1),
            height=3,
        )

    def render_sidebar(self, console_width: int) -> Panel:
        chat_lines = []

        for idx, dialog in enumerate(self.dialogs):
            entity = dialog.entity
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', 'Unknown')

            is_user = hasattr(entity, 'first_name') and not getattr(entity, 'is_bot', False)
            is_channel = hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast')
            is_bot = getattr(entity, 'is_bot', False)

            if is_user:
                color = NORD_COLORS['user']
                icon = "👤"
            elif is_channel:
                color = NORD_COLORS['channel']
                icon = "📢" if getattr(entity, 'broadcast', False) else "👥"
            elif is_bot:
                color = NORD_COLORS['bot']
                icon = "🤖"
            else:
                color = NORD_COLORS['text_dim']
                icon = "💬"

            max_name = 35
            display_name = str(name)[:max_name] + ("..." if len(str(name)) > max_name else "")

            selector = "[bold green]>[/bold green] " if self.selected_chat == idx else "   "
            line = f"{selector}[{color}]{icon} {display_name}[/{color}]"

            if dialog.message and dialog.message.text:
                msg = dialog.message.text[:40].replace('\n', ' ')
                line += f"\n[dim]    {msg}[/dim]"

            chat_lines.append(line)

        if not chat_lines:
            chat_lines = [f"[dim]No chats found[/dim]"]

        content = Text("\n".join(chat_lines))
        return Panel(
            content,
            title=f"[bold {NORD_COLORS['accent']}]Chats[/bold {NORD_COLORS['accent']}]",
            border_style=NORD_COLORS['accent'],
            box=box.ROUNDED,
            padding=(0, 1),
        )

    def render_chat_view(self) -> Panel:
        if self.selected_chat is not None and self.selected_chat < len(self.dialogs):
            dialog = self.dialogs[self.selected_chat]
            entity = dialog.entity
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', 'Unknown')

            content = Text.from_markup(
                f"[bold {NORD_COLORS['accent']}]Selected:[/bold {NORD_COLORS['accent']}] {name}\n\n"
                f"[dim]Conversation will appear here...[/dim]"
            )
        else:
            content = Text.from_markup(
                f"[bold {NORD_COLORS['accent_bright']}]Welcome to t-shell![/bold {NORD_COLORS['accent_bright']}]\n\n"
                f"[{NORD_COLORS['text_dim']}]Select a chat from the sidebar to start messaging.[/{NORD_COLORS['text_dim']}]\n\n"
                f"[dim]System Info:[/dim]\n"
                f"  [{NORD_COLORS['success']}]●[/] Connected\n"
                f"  [{NORD_COLORS['warning']}]●[/] DC: Main\n"
                f"  [{NORD_COLORS['accent']}]●[/] Ping: ~50ms\n"
                f"  [{NORD_COLORS['text_dim']}]●[/] Version: 0.1.0"
            )

        return Panel(
            content,
            title=f"[bold {NORD_COLORS['accent']}]Chat View[/bold {NORD_COLORS['accent']}]",
            border_style=NORD_COLORS['accent'],
            box=box.ROUNDED,
            padding=(1, 2),
        )

    def render_footer(self) -> Panel:
        content = Text.assemble(
            f"  [{NORD_COLORS['warning']}][R][/] Refresh  ",
            f"  [{NORD_COLORS['warning']}][↑/↓][/] Navigate  ",
            f"  [{NORD_COLORS['warning']}][Enter][/] Select  ",
            f"  [{NORD_COLORS['error']}][Q][/] Quit",
        )

        return Panel(
            content,
            border_style=NORD_COLORS['bg_light'],
            box=box.ROUNDED,
            padding=(0, 1),
            height=3,
        )

    def render(self, console_width: int):
        self.layout = self.create_layout()
        self.layout["header"].update(self.render_header())
        self.layout["sidebar"].update(self.render_sidebar(console_width))
        self.layout["chat_view"].update(self.render_chat_view())
        self.layout["footer"].update(self.render_footer())
        return self.layout


async def setup_credentials(config: Config):
    console.print("\n")
    with Panel(
        Text("T-Shell Authentication Setup", style=f"bold {NORD_COLORS['accent']}"),
        border_style=NORD_COLORS['accent'],
        box=box.ROUNDED,
        padding=(1, 2)
    ) as panel:
        console.print(panel)

    api_id = Prompt.ask(f"  [{NORD_COLORS['warning']}]API ID[/{NORD_COLORS['warning']}]")
    api_hash = Prompt.ask(f"  [{NORD_COLORS['warning']}]API Hash[/{NORD_COLORS['warning']}]")
    phone = Prompt.ask(f"  [{NORD_COLORS['warning']}]Phone (with country code)[/{NORD_COLORS['warning']}]")

    config.save_credentials(api_id, api_hash, phone)
    console.print(f"\n  [{NORD_COLORS['success']}]✓[/] Credentials saved!\n")


async def main():
    config = Config()

    if not config.has_credentials():
        setup = Confirm.ask(f"[{NORD_COLORS['warning']}]No credentials found. Set up now?[/{NORD_COLORS['warning']}]")
        if setup:
            await setup_credentials(config)
        else:
            console.print(f"[{NORD_COLORS['error']}]Cannot proceed without credentials.[/{NORD_COLORS['error']}]")
            sys.exit(1)

    client = TShellClient(config)
    ui = TShellUI()

    try:
        await client.start()
        ui.me = await client.get_me()
        ui.dialogs = await client.get_dialogs(limit=50)

        console.clear()

        with Live(ui.render(console.width), console=console, refresh_per_second=4, screen=True, transient=False) as live:
            while True:
                await asyncio.sleep(30)
                ui.dialogs = await client.get_dialogs(limit=50)
                live.update(ui.render(console.width))

    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as e:
        console.print(f"\n[{NORD_COLORS['error']}]Error:[/] {e}")
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())