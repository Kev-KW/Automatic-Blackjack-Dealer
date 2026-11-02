
"""Display blackjack game in a centered terminal-style window."""

from contextlib import redirect_stdout
from io import TextIOBase
import queue
import threading
import traceback
import tkinter as tk
from tkinter import font as tkfont

import gameSetup
import screen


# ============================================================
# SETTINGS
# ============================================================

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700

BACKGROUND = "black"
TEXT_COLOR = "#00ff00"
ERROR_COLOR = "#ff0000"

FONT_SIZE = 18
FONT_FAMILY = "Consolas"

UPDATE_INTERVAL = 150
MAX_OUTPUT_LINES = 1000

# Layout proportions
TOP_RATIO = 0.55
BOTTOM_RATIO = 0.45

# Fixed-width area so text never shifts horizontally
TABLE_COLUMNS = 48


# ============================================================
# THREAD-SAFE OUTPUT
# ============================================================

class ScreenOutput(TextIOBase):

    def __init__(self):
        super().__init__()
        self._queue = queue.Queue()

    def write(self, text):
        if text:
            self._queue.put(text)
        return len(text)

    def flush(self):
        pass

    def drain(self):
        chunks = []

        while True:
            try:
                chunks.append(self._queue.get_nowait())
            except queue.Empty:
                break

        return "".join(chunks)


# ============================================================
# MAIN GUI
# ============================================================

def run():

    root = tk.Tk()
    root.title("Automatic Blackjack Dealer")

    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    root.minsize(700, 450)
    root.configure(bg=BACKGROUND)

    game_font = tkfont.Font(
        family=FONT_FAMILY,
        size=FONT_SIZE
    )

    line_height = game_font.metrics("linespace")

    # ========================================================
    # FRAMES
    # ========================================================

    # Explicit relative positioning prevents the footer
    # from shrinking the upper table area.

    top_frame = tk.Frame(
        root,
        bg=BACKGROUND
    )

    top_frame.place(
        relx=0,
        rely=0,
        relwidth=1,
        relheight=TOP_RATIO
    )

    bottom_frame = tk.Frame(
        root,
        bg=BACKGROUND
    )

    bottom_frame.place(
        relx=0,
        rely=TOP_RATIO,
        relwidth=1,
        relheight=BOTTOM_RATIO
    )

    # ========================================================
    # FIXED-POSITION GAME TABLE
    # ========================================================

    # This label maintains a constant character width.
    # It is centered as one complete block, not line-by-line.
    #
    # Changing card values or adding STAND/BUST does not
    # change where the table begins.

    table_label = tk.Label(
        top_frame,
        text="",
        font=game_font,
        bg=BACKGROUND,
        fg=TEXT_COLOR,
        justify=tk.LEFT,
        anchor="w",
        width=TABLE_COLUMNS,
        borderwidth=0,
        padx=0,
        pady=0
    )

    table_label.place(
        relx=0.5,
        rely=0.5,
        anchor="center"
    )

    # ========================================================
    # SETUP DISPLAY
    # ========================================================

    setup_label = tk.Label(
        top_frame,
        text="",
        font=game_font,
        bg=BACKGROUND,
        fg=TEXT_COLOR,
        justify=tk.CENTER,
        anchor="center"
    )

    # ========================================================
    # FOOTER
    # ========================================================

    # One Text widget, no scrollbar.
    # Same font size as the blackjack table.

    footer = tk.Text(
        bottom_frame,
        bg=BACKGROUND,
        fg=TEXT_COLOR,
        font=game_font,
        borderwidth=0,
        highlightthickness=0,
        padx=10,
        pady=5,
        wrap=tk.NONE,
        state=tk.DISABLED,
        takefocus=False,
        cursor="arrow"
    )

    footer.place(
        relx=0,
        rely=0,
        relwidth=1,
        relheight=1
    )

    footer.tag_configure(
        "normal",
        justify=tk.CENTER,
        foreground=TEXT_COLOR
    )

    footer.tag_configure(
        "ignored",
        justify=tk.CENTER,
        foreground=ERROR_COLOR
    )

    # ========================================================
    # STATE
    # ========================================================

    output = ScreenOutput()

    game_output = ""

    last_mode = None
    last_player_count = None

    last_table = None
    last_footer = None
    last_footer_height = None

    running = True

    # ========================================================
    # PARSE GAME OUTPUT
    # ========================================================

    def parse_game_output():

        lines = game_output.splitlines()

        dealer_index = None

        for i in range(len(lines) - 1, -1, -1):

            if lines[i].startswith("DEALER:"):
                dealer_index = i
                break

        if dealer_index is None:
            return [], lines

        table_end = dealer_index + 1

        while table_end < len(lines):

            if not lines[table_end].startswith("PLAYER "):
                break

            table_end += 1

        table_lines = lines[dealer_index:table_end]
        footer_lines = lines[table_end:]

        while footer_lines and not footer_lines[0].strip():
            footer_lines.pop(0)

        while footer_lines and not footer_lines[-1].strip():
            footer_lines.pop()

        # Do not strip or pad table rows.
        # Original spacing is preserved exactly.

        return table_lines, footer_lines

    # ========================================================
    # UPDATE GAME TABLE
    # ========================================================

    def update_table(table_lines):
        nonlocal last_table

        content = "\n".join(table_lines)

        if content == last_table:
            return

        # Determine longest row in characters.
        longest_line = max(
            (len(line) for line in table_lines),
            default=TABLE_COLUMNS
        )

        # Expand table width only when necessary.
        required_columns = max(
            TABLE_COLUMNS,
            longest_line + 2
        )

        table_label.configure(
            width=required_columns,
            text=content
        )

        last_table = content

    # ========================================================
    # UPDATE FOOTER
    # ========================================================

    def update_footer(footer_lines, force=False):

        nonlocal last_footer
        nonlocal last_footer_height

        content = "\n".join(footer_lines)

        current_height = footer.winfo_height()

        if (
            not force
            and content == last_footer
            and current_height == last_footer_height
        ):
            return

        visible_rows = max(
            1,
            (current_height - 10) // line_height
        )

        # Center vertically when the content fits.
        if len(footer_lines) < visible_rows:

            padding = max(
                0,
                (visible_rows - len(footer_lines)) // 2
            )

        else:
            padding = 0

        footer.configure(state=tk.NORMAL)
        footer.delete("1.0", tk.END)

        if footer_lines and padding:
            footer.insert(
                tk.END,
                "\n" * padding
            )

        for i, line in enumerate(footer_lines):

            tag = (
                "ignored"
                if line.startswith("Ignoring action")
                else "normal"
            )

            footer.insert(
                tk.END,
                line,
                tag
            )

            if i < len(footer_lines) - 1:
                footer.insert(tk.END, "\n")

        footer.configure(state=tk.DISABLED)

        if len(footer_lines) > visible_rows:
            footer.see(tk.END)
        else:
            footer.yview_moveto(0)

        last_footer = content
        last_footer_height = current_height

    # ========================================================
    # RENDER LOOP
    # ========================================================

    def render():

        nonlocal game_output
        nonlocal last_mode
        nonlocal last_player_count
        nonlocal last_table
        nonlocal last_footer

        if not running:
            return

        mode, player_count, screen_output = screen.drain()
        captured = output.drain()

        clear_marker = "\x00CLEAR_GAME"

        clear_requested = (
            clear_marker in screen_output
            if screen_output is not None
            else False
        )

        mode_changed = mode != last_mode

        player_changed = (
            player_count != last_player_count
        )

        if mode_changed or clear_requested:

            game_output = ""
            last_table = None
            last_footer = None

        if captured:

            game_output += captured

            lines = game_output.splitlines(
                keepends=True
            )

            if len(lines) > MAX_OUTPUT_LINES:

                game_output = "".join(
                    lines[-MAX_OUTPUT_LINES:]
                )

        data_changed = (
            bool(captured)
            or mode_changed
            or player_changed
            or clear_requested
        )

        footer_size_changed = (
            footer.winfo_height() != last_footer_height
        )

        # ====================================================
        # SETUP
        # ====================================================

        if mode == "setup":

            if mode_changed:

                table_label.place_forget()

                setup_label.place(
                    relx=0.5,
                    rely=0.5,
                    anchor="center"
                )

            if data_changed:

                setup_label.configure(
                    text=(
                        "SELECT NUMBER PLAYERS\n\n"
                        f"{player_count}"
                    )
                )

                update_footer([], force=True)

        # ====================================================
        # GAME
        # ====================================================

        else:

            if mode_changed:

                setup_label.place_forget()

                table_label.place(
                    relx=0.5,
                    rely=0.5,
                    anchor="center"
                )

            if data_changed or footer_size_changed:

                table_lines, footer_lines = (
                    parse_game_output()
                )

                if data_changed:
                    update_table(table_lines)

                update_footer(footer_lines)

        last_mode = mode
        last_player_count = player_count

        root.after(
            UPDATE_INTERVAL,
            render
        )

    # ========================================================
    # GAME THREAD
    # ========================================================

    def run_game():

        with redirect_stdout(output):

            try:
                gameSetup.main()

            except Exception:
                traceback.print_exc()

    # ========================================================
    # WINDOW CLOSE
    # ========================================================

    def on_close():

        nonlocal running

        running = False
        root.destroy()

    root.protocol(
        "WM_DELETE_WINDOW",
        on_close
    )

    # ========================================================
    # START
    # ========================================================

    worker = threading.Thread(
        target=run_game,
        daemon=True
    )

    worker.start()

    root.after(
        UPDATE_INTERVAL,
        render
    )

    root.mainloop()


if __name__ == "__main__":
    run()
