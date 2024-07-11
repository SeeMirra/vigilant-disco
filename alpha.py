from __future__ import annotations
import os
import logging
import io
import sys
import argparse

from game import Game
from textual import work, events
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, Log, MarkdownViewer, RichLog, Button, Static
from textual.logging import TextualHandler
import queue
from textual.message import Message
from textwrap import wrap
from events import BufferUpdated, GenerateUpdated, GenerateCleared, Stopped, SaveState
import os.path
from rich_pixels import Pixels
from rich.console import Console
from rich.panel import Panel
from PIL import Image
import glob


logging.basicConfig(
    level="DEBUG",
    handlers=[TextualHandler()],
)


class Untitled1(App):
    CSS_PATH = "alpha.tcss"

    game: Game
    buffer: str
    generte: str
    line_limit = 4096

    def __init__(self, args):
        self.args = args
        super().__init__()

    def compose(self) -> ComposeResult:
        self.dark = True
        self.executor = None
        self.listener = None
        self.queue_to_game = queue.Queue()
        self.queue_from_game = queue.Queue()

        # with VerticalScroll(id="buffer-container"):
        yield RichLog(id="buffer_panel", auto_scroll=True, wrap=True, markup=True)
        yield RichLog(id="generation_panel", auto_scroll=True, wrap=True, markup=True)
        yield Input(placeholder="Your command")
        #yield RichLog(id="image_panel")

        self.console = Console()
        self.console_panel = Static(id="image_panel")
        #self.console.status("Illustration")
        yield self.console_panel
        #yield Console()
        #yield Static("Standard Buttons", classes="header"),
        #yield Button("Default"),
        #yield Button("Primary!", variant="primary"),
        #yield Button.success("Success!"),
        #yield Button.warning("Warning!"),
        #yield Button.error("Error!"),

    def on_mount(self) -> None:
        self.buffer = "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\t\t\t\t[b u]Welcome to [sanitized]![/]\n\n"
        self.buffer += (
            "[i]This is in an unfinished state and under development. "
        )

        self.generate = ""
        self.query_one(Input).focus()
        self.executor = self.run_worker(self.execute, thread=True)
        self.listener = self.run_worker(self.listen, thread=True)

        panel = self.query_one("#generation_panel", RichLog).clear()
        panel.display = False
        panel.border_title = "LLM"

        self.update_console("[bold red]Welcome to Untitled1![/bold red]")

        #with Image.open("/home/workstation/work/ml/img/ComfyUI/output/ComfyUI_temp_njvqq_00001_.png") as image:
        pixels = Pixels.from_image_path("/home/workstation/work/ml/img/ComfyUI/output/titlescreen.png", (140, 140))
        self.update_console(pixels)
         #self.console.print(pixels)

        #pixels = Pixels.from_image_path("/home/workstation/work/ml/img/ComfyUI/output/bulbasaur.png")
        #self.console.print(pixels)

        

    def update_console(self, content: str) -> None:
        console_panel_content = Panel(content, title="", border_style="none")
        self.console_panel.update(console_panel_content)


    def on_unmount(self) -> None:
        self.queue_to_game.put("<<<stop>>>", block=False)
        self.queue_from_game.put("<<<stop>>>", block=False)

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        self.query_one("Input", Input).clear()
        if message.value == "dark":
            self.dark = True
        elif message.value == "light":
            self.dark = False
        else:
            self.queue_to_game.put(message.value, block=True)

    async def on_buffer_updated(self, message: BufferUpdated) -> None:
        self.buffer += message.message

        lines = self.buffer.split("\n")
        if len(lines) > self.line_limit:
            lines = lines[len(lines) - self.line_limit :]
            self.buffer = "\n".join(lines)

        panel = self.query_one("#buffer_panel", RichLog)
        panel.clear()
        panel.write(self.buffer + "\n", scroll_end=True)

    async def on_generate_updated(self, message: GenerateUpdated) -> None:
        panel = self.query_one("#generation_panel", RichLog).clear()
        panel.display = True

        # wtf this gets wiped when we do panel.display = True, ytho
        buf = self.query_one("#buffer_panel", RichLog).clear()
        buf.write(self.buffer + "\n", scroll_end=True)

        self.generate += message.message

        panel = self.query_one("#generation_panel", RichLog)
        panel.clear()
        panel.write(self.generate + "\n", scroll_end=True)

    async def on_generate_cleared(self, message: GenerateCleared) -> None:
        panel = self.query_one("#generation_panel", RichLog).clear()
        panel.display = False
        panel.clear()
        self.generate = ""
        with open("/home/workstation/work/ml/img/ComfyUI/ComfyUI-to-Python-Extension/currentImage.txt", "w") as text_file:
            list_of_files = glob.glob('/home/workstation/work/ml/img/ComfyUI/output/*')
            latest_file = max(list_of_files, key=os.path.getctime)
            print(f"{latest_file}", file=text_file)
            pixels = Pixels.from_image_path(latest_file, (140, 140))
            self.update_console(pixels)

    def listen(self):
        while True:
            event = self.queue_from_game.get(block=True)
            if event == "<<<stop>>>":
                print("Listener stopping...")
                break
            else:
                self.post_message(event)

    def execute(self):
        if os.path.exists("save/game_loop.json"):
            game = Game(
                self.queue_from_game,
                args=self.args,
                from_save="save",
            )
        else:
            game = Game(self.queue_from_game, args=self.args)

        while True:
            line = self.queue_to_game.get(block=True)
            if line == "<<<stop>>>":
                print("Executor stopping...")
                break
            else:
                game.execute(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Untitled1",
    )
    parser.add_argument("-m", "--model", type=str)
    parser.add_argument("-ngl", "--gpu-layers", type=int)
    parser.add_argument("-c", "--n_ctx", type=int)
    parser.add_argument("-b", "--n_batch", type=int)
    parser.add_argument("-t", "--threads", type=int)
    parser.add_argument("--mlock", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if not os.path.isfile(args.model):
        print("Pass model path as the first parameter")

    app = Untitled1(args)
    app.run()
