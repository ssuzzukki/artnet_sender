import socket
import threading
import time
import tkinter as tk
from tkinter import ttk


# =========================
# Art-Net Sender
# =========================

class ArtNetSender:
    PORT = 6454

    def __init__(self):
        self.target_ip = "127.0.0.1"

        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        self.universes = {}
        self.lock = threading.Lock()

        self.running = True

        self.thread = threading.Thread(
            target=self._send_loop,
            daemon=True
        )

        self.thread.start()

    def set_ip(self, ip):
        self.target_ip = ip

    def set_value(self, universe, channel, value):
        if not (0 <= universe <= 32767):
            return

        if not (1 <= channel <= 512):
            return

        value = max(0, min(255, value))

        with self.lock:
            if universe not in self.universes:
                self.universes[universe] = bytearray(512)

            self.universes[universe][channel - 1] = value

    def make_packet(self, universe, dmx):

        packet = bytearray()

        packet.extend(b"Art-Net\x00")

        # ArtDMX opcode
        packet.extend((0x00, 0x50))

        # Protocol version 14
        packet.extend((0x00, 0x0E))

        # Sequence
        packet.append(0)

        # Physical
        packet.append(0)

        # Universe (little endian)
        packet.extend((
            universe & 0xFF,
            (universe >> 8) & 0xFF
        ))

        # Length = 512
        packet.extend((0x02, 0x00))

        packet.extend(dmx)

        return packet

    def _send_loop(self):

        while self.running:

            with self.lock:
                universes_copy = {
                    k: bytes(v)
                    for k, v in self.universes.items()
                }

            for universe, dmx in universes_copy.items():

                packet = self.make_packet(
                    universe,
                    dmx
                )

                try:
                    self.sock.sendto(
                        packet,
                        (self.target_ip, self.PORT)
                    )
                except Exception:
                    pass

            # 40Hz
            time.sleep(0.025)

    def stop(self):
        self.running = False


# =========================
# Fader Widget
# =========================

class Fader:

    def __init__(self, parent, sender):

        self.sender = sender

        self.frame = ttk.LabelFrame(
            parent,
            text="Fader"
        )

        self.frame.pack(
            side="left",
            padx=5,
            pady=5
        )

        self.universe_var = tk.StringVar(value="0")
        self.channel_var = tk.StringVar(value="1")
        self.value_var = tk.StringVar(value="0")

        ttk.Label(
            self.frame,
            text="Universe"
        ).pack()

        self.universe_entry = ttk.Entry(
            self.frame,
            width=6,
            textvariable=self.universe_var
        )
        self.universe_entry.pack()

        ttk.Label(
            self.frame,
            text="Channel"
        ).pack()

        self.channel_entry = ttk.Entry(
            self.frame,
            width=6,
            textvariable=self.channel_var
        )
        self.channel_entry.pack()

        self.scale = tk.Scale(
            self.frame,
            from_=255,
            to=0,
            orient="vertical",
            length=250,
            command=self.scale_changed
        )

        self.scale.pack(
            pady=8
        )

        self.value_entry = ttk.Entry(
            self.frame,
            width=6,
            justify="center",
            textvariable=self.value_var
        )

        self.value_entry.pack()

        self.value_entry.bind(
            "<Return>",
            self.entry_changed
        )

        self.value_entry.bind(
            "<FocusOut>",
            self.entry_changed
        )

        ttk.Button(
            self.frame,
            text="×",
            command=self.remove,
            width=4
        ).pack(
            pady=5
        )

    def send_current_value(self, value):

        try:
            universe = int(
                self.universe_var.get()
            )

            channel = int(
                self.channel_var.get()
            )

        except ValueError:
            return

        self.sender.set_value(
            universe,
            channel,
            value
        )

    def scale_changed(self, value):

        value = int(float(value))

        self.value_var.set(
            str(value)
        )

        self.send_current_value(value)

    def entry_changed(self, _):

        try:
            value = int(
                self.value_var.get()
            )
        except ValueError:
            return

        value = max(
            0,
            min(255, value)
        )

        self.value_var.set(
            str(value)
        )

        self.scale.set(value)

        self.send_current_value(value)

    def remove(self):
        self.frame.destroy()


# =========================
# Main App
# =========================

class App:

    def __init__(self, root):

        self.root = root
        self.root.title("Simple ArtNet Sender")

        self.sender = ArtNetSender()

        self.build_ui()

    def build_ui(self):

        top = ttk.Frame(self.root)
        top.pack(
            fill="x",
            padx=8,
            pady=8
        )

        ttk.Label(
            top,
            text="Target IP"
        ).pack(side="left")

        self.ip_var = tk.StringVar(
            value="127.0.0.1"
        )

        ttk.Entry(
            top,
            width=20,
            textvariable=self.ip_var
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            top,
            text="Apply",
            command=self.apply_ip
        ).pack(side="left")

        ttk.Button(
            top,
            text="+ Add Fader",
            command=self.add_fader
        ).pack(
            side="left",
            padx=20
        )

        # Scroll Area

        self.canvas = tk.Canvas(
            self.root
        )

        scrollbar = ttk.Scrollbar(
            self.root,
            orient="horizontal",
            command=self.canvas.xview
        )

        self.canvas.configure(
            xscrollcommand=scrollbar.set
        )

        scrollbar.pack(
            side="bottom",
            fill="x"
        )

        self.canvas.pack(
            side="top",
            fill="both",
            expand=True
        )

        self.fader_frame = ttk.Frame(
            self.canvas
        )

        self.window_id = self.canvas.create_window(
            (0, 0),
            window=self.fader_frame,
            anchor="nw"
        )

        self.fader_frame.bind(
            "<Configure>",
            self.update_scrollregion
        )

    def update_scrollregion(self, _):

        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def apply_ip(self):

        ip = self.ip_var.get().strip()

        self.sender.set_ip(ip)

    def add_fader(self):

        Fader(
            self.fader_frame,
            self.sender
        )

        self.update_scrollregion(None)

    def stop(self):
        self.sender.stop()


# =========================
# Start
# =========================

def main():

    root = tk.Tk()

    root.geometry("900x500")

    app = App(root)

    try:
        root.mainloop()

    finally:
        app.stop()


if __name__ == "__main__":
    main()