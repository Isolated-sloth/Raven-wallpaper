import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import subprocess
import json
import atexit


CONFIG_PATH = os.path.expanduser("~/.raven_wallpaper.json")


APP_VERSION = "1.0.0"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

class RavenWallpaperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Raven Wallpaper")
        self.geometry("1000x650")
        self.minsize(800, 550)

        self.current_process = None
        self.video_list = []
        self.thumbnail_cache = {}
        self.selected_video = None
        self.current_folder = None
        self.selected_output = "* (All)"

        self.load_config()
        self.outputs = self.get_outputs()

        atexit.register(self.cleanup_thumbs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew")

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(main_frame, height=60, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(header, text="Raven Wallpaper", font=("Helvetica", 24, "bold")).pack(side="left", padx=20, pady=10)

        ctk.CTkButton(header, text="⚙ Settings", width=100, command=self.open_settings).pack(side="left", padx=10)

        ctk.CTkButton(header, text="Refresh", width=100, command=self.scan_folder).pack(side="left", padx=5)

        ctk.CTkButton(header, text="Stop Current", width=140, fg_color="darkred", hover_color="red", command=self.stop_wallpaper).pack(side="right", padx=20)

        # Version label in header
        ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION}",
            font=("Helvetica", 10),
            text_color="gray"
        ).pack(side="right", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(header, text=self.shorten_path(self.current_folder or "None selected"), wraplength=400)
        self.status_label.pack(side="left", padx=30)

        self.scroll_frame = ctk.CTkScrollableFrame(main_frame)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.scan_folder()

    def shorten_path(self, path):
        if not path:
            return "None selected"
        home = os.path.expanduser("~")
        path = path.replace(home, "~")
        if len(path) > 50:
            parts = path.split(os.sep)
            return os.sep.join(parts[:1] + ["..."] + parts[-2:])
        return path

    def get_outputs(self):
        try:
            result = subprocess.run(["wlr-randr"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.splitlines()
            outputs = ["* (All)"]
            for line in lines:
                if line.strip() and not line.startswith(" "):
                    name = line.split()[0]
                    outputs.append(name)
            return outputs
        except:
            return ["* (All)"]

    def open_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings")
        dialog.geometry("500x500")
        dialog.transient(self)
        dialog.attributes('-topmost', True)
        dialog.after(100, dialog.lift)
        dialog.after(150, dialog.focus_force)

        ctk.CTkLabel(dialog, text="Current Folder:", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))

        self.folder_display = ctk.CTkLabel(
            dialog,
            text=self.shorten_path(self.current_folder),
            wraplength=460,
            justify="left",
            anchor="w"
        )
        self.folder_display.pack(anchor="w", padx=20, pady=(0, 10), fill="x")

        ctk.CTkButton(dialog, text="Browse Folder", width=200, command=lambda: self.select_folder(dialog)).pack(pady=10)

        ctk.CTkLabel(dialog, text="Monitor / Output:", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))

        self.output_var = ctk.StringVar(value=self.selected_output)
        option_menu = ctk.CTkOptionMenu(
            dialog,
            values=self.outputs,
            variable=self.output_var,
            width=300
        )
        option_menu.pack(pady=5)

        self.output_var.trace("w", lambda *args: self.update_output())

        ctk.CTkButton(dialog, text="Close", width=120, command=dialog.destroy).pack(pady=30)

    def update_output(self):
        self.selected_output = self.output_var.get()
        self.save_config()

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    self.current_folder = data.get("folder")
                    self.selected_video = data.get("last_video")
                    self.selected_output = data.get("output", "* (All)")
            except:
                pass

    def save_config(self):
        data = {
            "folder": self.current_folder,
            "last_video": self.selected_video,
            "output": self.selected_output
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def select_folder(self, dialog=None):
        folder = filedialog.askdirectory(title="Choose Folder with Video Wallpapers")
        if folder:
            self.current_folder = folder
            self.status_label.configure(text=self.shorten_path(folder))
            if hasattr(self, 'folder_display'):
                self.folder_display.configure(text=self.shorten_path(folder))
            self.scan_folder()
            self.save_config()

    def scan_folder(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.current_folder or not os.path.isdir(self.current_folder):
            ctk.CTkLabel(self.scroll_frame, text="No folder selected.\nClick ⚙ Settings → Browse Folder", font=("Helvetica", 16)).pack(pady=60)
            return

        self.video_list = [os.path.join(self.current_folder, f) for f in sorted(os.listdir(self.current_folder)) if f.lower().endswith((".mp4", ".webm", ".mkv", ".mov", ".gif"))]

        if not self.video_list:
            ctk.CTkLabel(self.scroll_frame, text="No supported videos found.").pack(pady=40)
            return

        columns = 4
        for i, path in enumerate(self.video_list):
            card = ctk.CTkFrame(self.scroll_frame, corner_radius=12, border_width=1, width=240, height=290)
            card.grid(row=i // columns, column=i % columns, padx=12, pady=12, sticky="n")
            card.grid_propagate(False)

            # Thumbnail 
            thumb_frame = ctk.CTkFrame(
                card,
                fg_color="transparent",
                border_width=2,
                border_color="#00aaff",
                corner_radius=8,
                width=204,
                height=144
            )
            thumb_frame.pack(pady=(15, 5))
            thumb_frame.grid_propagate(False)

            thumb_label = ctk.CTkLabel(thumb_frame, text="", width=200, height=140, corner_radius=6)
            thumb_label.place(relx=0.5, rely=0.5, anchor="center")
            thumb = self.get_thumbnail(path)
            if thumb:
                thumb_label.configure(image=thumb)

            name = os.path.basename(path)
            short_name = (name[:30] + "...") if len(name) > 30 else name
            ctk.CTkLabel(card, text=short_name, wraplength=220).pack(pady=4)

            btn = ctk.CTkButton(card, text="Apply", width=120, command=lambda p=path: self.apply_wallpaper(p))
            btn.pack(pady=10)

            if path == self.selected_video:
                card.configure(border_color="#00aaff", border_width=3)

    def get_thumbnail(self, path):
        if path in self.thumbnail_cache:
            return self.thumbnail_cache[path]

        try:
            # Prefer bundled ffmpeg if present
            bundled_ffmpeg = os.path.join(os.path.dirname(__file__), "ffmpeg")
            ffmpeg_cmd = [bundled_ffmpeg] if os.path.isfile(bundled_ffmpeg) and os.access(bundled_ffmpeg, os.X_OK) else ["ffmpeg"]

            thumb_path = f"/tmp/raven_thumb_{os.path.basename(path)}.jpg"
            subprocess.run(
                ffmpeg_cmd + [
                    "-y", "-i", path, "-vframes", "1",
                    "-ss", "00:00:01", "-vf", "scale=200:140:force_original_aspect_ratio=decrease,pad=200:140:(ow-iw)/2:(oh-ih)/2,setsar=1",
                    thumb_path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8
            )

            img = Image.open(thumb_path) if os.path.exists(thumb_path) else Image.open(path)
            if getattr(img, "is_animated", False):
                img.seek(0)
            img = img.resize((200, 140), Image.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 140))
            self.thumbnail_cache[path] = photo
            return photo

        except Exception as e:
            print(f"Thumb error {path}: {e}")
            return None

    def cleanup_thumbs(self):
        for f in os.listdir("/tmp"):
            if f.startswith("raven_thumb_"):
                try:
                    os.remove(os.path.join("/tmp", f))
                except:
                    pass

    def apply_wallpaper(self, path):
        self.stop_wallpaper()
        self.selected_video = path
        self.save_config()
        self.scan_folder()

        output = self.selected_output.split()[0]

        cmd = [
            "mpvpaper", output,
            path,
            "-o", "--loop=inf --no-audio --no-osc --hwdec=auto --really-quiet"
        ]

        try:
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            messagebox.showinfo("Success", f"Applied to {output}:\n{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_wallpaper(self):
        if self.current_process:
            self.current_process.terminate()
            try:
                self.current_process.wait(3)
            except:
                self.current_process.kill()
            self.current_process = None
        subprocess.run(["pkill", "-f", "mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    app = RavenWallpaperApp()
    app.mainloop()