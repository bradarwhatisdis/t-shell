import asyncio
import sys
import readchar
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.live import Live
from datetime import datetime

from src.config import Config
from src.client import TShellClient

console = Console()

NORD = {
    "accent": "#88C0D0",
    "accent_bright": "#81A1C1",
    "text": "#ECEFF4",
    "text_dim": "#D8DEE9",
    "gray": "#4C566A",
    "user": "#88C0D0",
    "channel": "#B48EAD",
    "bot": "#A3BE8C",
    "success": "#A3BE8C",
    "warning": "#EBCB8B",
    "error": "#BF616A",
    "bg": "#2E3440",
}


def markup(text: str) -> Text:
    return Text.from_markup(text)


def format_time(dt):
    if not dt:
        return ""
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    now = datetime.now()
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    elif (now - dt).days == 1:
        return "Yesterday"
    else:
        return dt.strftime("%d %b")


class TShellUI:
    def __init__(self):
        self.layout = Layout()
        self.selected_chat = 0
        self.scroll_offset = 0
        self.visible_count = 20
        self.me = None
        self.dialogs = []
        self.messages = []
        self.loading = False

    def create_layout(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        layout["main"].split_row(
            Layout(name="sidebar", ratio=1),
            Layout(name="chat_view", ratio=3),
        )
        return layout

    def render_header(self) -> Panel:
        username = f"@{self.me.username}" if self.me.username else "no username"
        user_line = f"Logged in as [bold #ECEFF4]{self.me.first_name}[/] [#D8DEE9]({username})[/]  |  [#4C566A]ID:[/] [#88C0D0]{self.me.id}[/]"
        
        content = Text.from_markup(f"  [#88C0D0 bold]t-shell[/]  │  {user_line}")
        
        return Panel(
            content,
            border_style="#81A1C1",
            box=box.ROUNDED,
            padding=(0, 1),
            height=3,
        )

    def render_sidebar(self) -> Panel:
        lines = []
        
        visible_dialogs = self.dialogs[self.scroll_offset:self.scroll_offset + self.visible_count]
        
        for idx, dialog in enumerate(visible_dialogs):
            real_idx = idx + self.scroll_offset
            entity = dialog.entity
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', 'Unknown')

            is_user = hasattr(entity, 'first_name') and not getattr(entity, 'is_bot', False)
            is_channel = hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast')
            is_bot = getattr(entity, 'is_bot', False)

            if is_user:
                color = "#88C0D0"
                icon = "👤"
            elif is_channel:
                color = "#B48EAD"
                icon = "📢" if getattr(entity, 'broadcast', False) else "👥"
            elif is_bot:
                color = "#A3BE8C"
                icon = "🤖"
            else:
                color = "#ECEFF4"
                icon = "💬"

            max_name = 28
            if len(str(name)) > max_name:
                display_name = str(name)[:max_name-3] + "..."
            else:
                display_name = str(name)

            is_selected = real_idx == self.selected_chat
            prefix = "[#A3BE8B bold]▶ [/]" if is_selected else "  "
            
            name_text = Text.from_markup(f"{prefix}[{color} bold]{icon} {display_name}[/]")

            if dialog.message and dialog.message.text:
                msg_text = dialog.message.text.replace('\n', ' ')[:40]
                if len(dialog.message.text) > 40:
                    msg_text += "..."
                msg_line = Text.from_markup(f"   [#4C566A]{msg_text}[/]")
                lines.append(Group(name_text, msg_line))
            else:
                lines.append(name_text)

        if not lines:
            lines = [Text.from_markup("[#4C566A]No chats found[/]")]

        content = Group(*lines)
        
        info_text = Text.from_markup(f"[#4C566A]{self.selected_chat + 1}/{len(self.dialogs)} chats[/]")
        
        return Panel(
            Group(content, "", info_text),
            title=markup("[bold #88C0D0]Chats[/]"),
            border_style="#88C0D0",
            box=box.ROUNDED,
            padding=(0, 1),
        )

    def render_chat_view(self) -> Panel:
        if self.loading:
            content = markup(f"[bold #81A1C1]Loading messages...[/]")
        elif self.dialogs and self.selected_chat < len(self.dialogs):
            dialog = self.dialogs[self.selected_chat]
            entity = dialog.entity
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', 'Unknown')
            
            entity_type = "User" if hasattr(entity, 'first_name') else "Chat"
            if hasattr(entity, 'broadcast'):
                entity_type = "Channel" if entity.broadcast else "Group"
            if getattr(entity, 'is_bot', False):
                entity_type = "Bot"

            header = markup(
                f"[bold #88C0D0]{name}[/]\n"
                f"[#4C566A]Type:[/] [#ECEFF4]{entity_type}[/]  "
                f"[#4C566A]ID:[/] [#81A1C1]{entity.id}[/]"
            )

            if self.messages:
                msg_lines = []
                for msg in reversed(self.messages):
                    time_str = format_time(msg.date)
                    msg_text = msg.text or "[media]"
                    
                    if msg.from_id:
                        sender_id = msg.from_id.user_id if hasattr(msg.from_id, 'user_id') else str(msg.from_id)
                        sender = f"User#{sender_id}"
                    elif hasattr(msg, 'sender') and msg.sender:
                        sender = getattr(msg.sender, 'first_name', None) or getattr(msg.sender, 'title', 'Unknown')
                    else:
                        sender = "Unknown"
                    
                    msg_short = msg_text[:80] + "..." if len(msg_text) > 80 else msg_text
                    msg_short = msg_short.replace('\n', ' ')
                    
                    msg_lines.append(f"[#EBCB8B]{time_str}[/] [#81A1C1]{sender}[/]: [#ECEFF4]{msg_short}[/]")
                
                messages_text = Text.from_markup("\n".join(msg_lines))
                content = Group(header, "", messages_text)
            else:
                content = Group(header, "", markup(f"[#4C566A]No messages[/]"))
        else:
            content = markup(
                f"[bold #81A1C1]Welcome to t-shell![/]\n\n"
                f"[#D8DEE9]Select a chat from the sidebar.[/]\n\n"
                f"[#4C566A]─────────────────────────[/]\n"
                f"[#A3BE8C]●[/] [#ECEFF4]Connected[/]\n"
                f"[#EBCB8B]●[/] [#ECEFF4]DC: Main[/]\n"
                f"[#88C0D0]●[/] [#ECEFF4]Ping: ~50ms[/]\n"
                f"[#4C566A]─────────────────────────[/]\n\n"
                f"[#4C566A]Version:[/] [#81A1C1]0.1.0[/]"
            )

        return Panel(
            content,
            title=markup("[bold #88C0D0]Chat View[/]"),
            border_style="#88C0D0",
            box=box.ROUNDED,
            padding=(1, 2),
        )

    def render_footer(self) -> Panel:
        refresh = markup("[#2E3440 on #EBCB8B bold] R [/]")
        up = markup("[#2E3440 on #EBCB8B bold] ↑↓ [/]")
        enter = markup("[#2E3440 on #A3BE8C bold] Enter [/]")
        quit_btn = markup("[#2E3440 on #BF616A bold] Q [/]")

        content = Text.assemble(
            f"  {refresh} Refresh  ",
            f"  {up} Navigate  ",
            f"  {enter} Select  ",
            f"  {quit_btn} Quit",
        )

        return Panel(
            content,
            border_style="#4C566A",
            box=box.ROUNDED,
            padding=(0, 1),
            height=3,
        )

    def render(self) -> Layout:
        self.layout = self.create_layout()
        self.layout["header"].update(self.render_header())
        self.layout["sidebar"].update(self.render_sidebar())
        self.layout["chat_view"].update(self.render_chat_view())
        self.layout["footer"].update(self.render_footer())
        return self.layout

    def navigate(self, direction: int):
        new_index = self.selected_chat + direction
        if 0 <= new_index < len(self.dialogs):
            self.selected_chat = new_index
            self.messages = []
            if self.selected_chat >= self.scroll_offset + self.visible_count:
                self.scroll_offset = self.selected_chat - self.visible_count + 1
            elif self.selected_chat < self.scroll_offset:
                self.scroll_offset = self.selected_chat


async def setup_credentials():
    console.print("\n")
    console.print(Panel(
        markup("[bold #88C0D0]T-Shell Authentication Setup[/]"),
        border_style="#81A1C1",
        box=box.ROUNDED,
        padding=(1, 2),
    ))

    api_id = Prompt.ask(markup("  [#EBCB8B]API ID[/]"))
    api_hash = Prompt.ask(markup("  [#EBCB8B]API Hash[/]"))
    phone = Prompt.ask(markup("  [#EBCB8B]Phone (with country code)[/]"))

    config = Config()
    config.save_credentials(api_id, api_hash, phone)
    console.print(markup(f"\n  [#A3BE8C]✓[/] [#A3BE8C]Credentials saved![/]\n"))


async def main():
    config = Config()

    if not config.has_credentials():
        setup = Confirm.ask(markup("[#EBCB8B]No credentials found. Set up now?[/]"))
        if setup:
            await setup_credentials()
        else:
            console.print(markup("[#BF616A]Cannot proceed without credentials.[/]"))
            sys.exit(1)

    client = TShellClient(config)
    ui = TShellUI()

    try:
        await client.start()
        ui.me = await client.get_me()
        ui.dialogs = await client.get_dialogs(limit=100)
        
        if ui.dialogs:
            ui.loading = True
            ui.messages = await client.get_messages(ui.dialogs[0].entity, limit=50)
            ui.loading = False
        
        console.clear()

        with Live(
            ui.render(),
            console=console,
            refresh_per_second=4,
            screen=True,
            transient=False
        ) as live:
            while True:
                key = readchar.readkey()
                
                if key == readchar.key.UP:
                    ui.navigate(-1)
                    ui.loading = True
                    live.update(ui.render())
                    entity = ui.dialogs[ui.selected_chat].entity
                    ui.messages = await client.get_messages(entity, limit=50)
                    ui.loading = False
                    live.update(ui.render())
                elif key == readchar.key.DOWN:
                    ui.navigate(1)
                    ui.loading = True
                    live.update(ui.render())
                    entity = ui.dialogs[ui.selected_chat].entity
                    ui.messages = await client.get_messages(entity, limit=50)
                    ui.loading = False
                    live.update(ui.render())
                elif key.lower() == 'r':
                    ui.dialogs = await client.get_dialogs(limit=100)
                    live.update(ui.render())
                elif key.lower() == 'q' or key == readchar.key.CTRL_C:
                    break

    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as e:
        console.print(markup(f"\n[#BF616A]Error:[/] {e}"))
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())