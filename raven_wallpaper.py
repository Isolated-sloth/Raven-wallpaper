import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import subprocess
import json
import atexit


CONFIG_PATH = os.path.expanduser("~/.raven_wallpaper.json")


APP_VERSION = "1.0.1"


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")  


POP_ORANGE = "#F6A33B"
POP_CYAN = "#48B9C7"
POP_DARK = "#2A2829"
POP_DARKER = "#1E1D1E"
POP_LIGHT = "#E6E6E6"

class RavenWallpaperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Raven Wallpaper")
        self.geometry("1000x650")
        self.minsize(800, 550)
        self.configure(fg_color=POP_DARKER)

        self.current_process = None
        self.video_list = []
        self.thumbnail_cache = {}
        self.selected_video = None
        self.current_folder = None
        self.selected_output = "* (All)"
        self.muted = True  # Default to muted

        self.load_config()
        self.outputs = self.get_outputs()

        atexit.register(self.cleanup_thumbs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        
        main_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=POP_DARK)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)


        header = ctk.CTkFrame(main_frame, height=60, corner_radius=0, fg_color=POP_DARKER)
        header.grid(row=0, column=0, sticky="ew")

        # Window control dots (Mac/Linux style)
        dot_frame = ctk.CTkFrame(header, fg_color="transparent")
        dot_frame.pack(side="left", padx=15, pady=20)
        
        ctk.CTkButton(dot_frame, text="", width=12, height=12, corner_radius=6, 
                      fg_color="#ff5f57", hover_color="#ff3b30", 
                      command=self.destroy).pack(side="left", padx=2)
        ctk.CTkButton(dot_frame, text="", width=12, height=12, corner_radius=6, 
                      fg_color="#ffbd2e", hover_color="#ffaa00", 
                      command=self.iconify).pack(side="left", padx=2)
        ctk.CTkButton(dot_frame, text="", width=12, height=12, corner_radius=6, 
                      fg_color="#28ca42", hover_color="#15b330", 
                      command=self.maximize).pack(side="left", padx=2)

        # App title
        ctk.CTkLabel(header, text="Raven Wallpaper", font=("Ubuntu", 20, "bold"), 
                     text_color=POP_LIGHT).pack(side="left", padx=20)

        # Center toolbar buttons
        toolbar_frame = ctk.CTkFrame(header, fg_color="transparent")
        toolbar_frame.pack(side="left", padx=20)

        ctk.CTkButton(toolbar_frame, text="⚙ Settings", width=120, 
                      fg_color=POP_CYAN, hover_color="#3aa3b1",
                      text_color="black", command=self.open_settings).pack(side="left", padx=5)

        ctk.CTkButton(toolbar_frame, text="Refresh", width=100, 
                      fg_color=POP_DARK, hover_color="#3a3839",
                      border_width=1, border_color=POP_CYAN,
                      command=self.scan_folder).pack(side="left", padx=5)

        # Right side status
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=20)

        self.status_label = ctk.CTkLabel(status_frame, text=self.shorten_path(self.current_folder or "None selected"), 
                                         wraplength=400, font=("Ubuntu", 12), text_color="gray")
        self.status_label.pack(side="right", padx=10)

        ctk.CTkButton(status_frame, text="Stop Current", width=140, 
                      fg_color="#d63031", hover_color="#b71c1c",
                      command=self.stop_wallpaper).pack(side="right", padx=10)

        # Version label
        ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION}",
            font=("Ubuntu", 10),
            text_color="gray"
        ).pack(side="right", padx=10)

        # Scrollable video grid
        self.scroll_frame = ctk.CTkScrollableFrame(main_frame, fg_color=POP_DARK)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.scan_folder()

    def maximize(self):
        if self.state() == "normal":
            self.state("zoomed")
        else:
            self.state("normal")

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
        dialog.geometry("500x550")
        dialog.transient(self)
        dialog.attributes('-topmost', True)
        dialog.configure(fg_color=POP_DARK)
        dialog.after(100, dialog.lift)
        dialog.after(150, dialog.focus_force)



        # Folder section
        ctk.CTkLabel(dialog, text="Current Folder:", font=("Ubuntu", 14, "bold"), 
                     text_color=POP_LIGHT).pack(anchor="w", padx=20, pady=(20, 5))

        self.folder_display = ctk.CTkLabel(
            dialog,
            text=self.shorten_path(self.current_folder),
            wraplength=460,
            justify="left",
            anchor="w",
            text_color="gray"
        )
        self.folder_display.pack(anchor="w", padx=20, pady=(0, 10), fill="x")

        ctk.CTkButton(dialog, text="Browse Folder", width=200, 
                      fg_color=POP_CYAN, hover_color="#3aa3b1",
                      text_color="black", command=lambda: self.select_folder(dialog)).pack(pady=10)

        # Monitor section
        ctk.CTkLabel(dialog, text="Monitor / Output:", font=("Ubuntu", 14, "bold"), 
                     text_color=POP_LIGHT).pack(anchor="w", padx=20, pady=(20, 5))

        self.output_var = ctk.StringVar(value=self.selected_output)
        option_menu = ctk.CTkOptionMenu(
            dialog,
            values=self.outputs,
            variable=self.output_var,
            width=300,
            fg_color=POP_DARKER,
            button_color=POP_CYAN,
            button_hover_color="#3aa3b1"
        )
        option_menu.pack(pady=5)

        self.output_var.trace("w", lambda *args: self.update_output())

                # Mute section
        ctk.CTkLabel(dialog, text="Audio:", font=("Ubuntu", 14, "bold"), 
                     text_color=POP_LIGHT).pack(anchor="w", padx=20, pady=(20, 5))
        self.mute_var = ctk.BooleanVar(value=self.muted)
        mute_frame = ctk.CTkFrame(dialog, fg_color=POP_DARKER, corner_radius=8)
        mute_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(mute_frame, text="Mute Wallpaper Audio", font=("Ubuntu", 12), 
                     text_color="gray").pack(side="left", padx=15, pady=10)
        self.mute_switch = ctk.CTkSwitch(
            mute_frame,
            text="",
            variable=self.mute_var,
            width=50,
            height=30,
            button_color=POP_ORANGE,
            button_hover_color="#e67e22",
            fg_color=POP_DARKER,
            border_color=POP_CYAN,
            border_width=2,
            command=self.update_mute
        )
        self.mute_switch.pack(side="right", padx=15, pady=10)
        # Mute status indicator
        self.mute_status_label = ctk.CTkLabel(
            mute_frame,
            text="🔇 Muted" if self.muted else "🔊 Sound On",
            font=("Ubuntu", 11),
            text_color=POP_ORANGE if self.muted else POP_CYAN
        )
        self.mute_status_label.pack(side="right", padx=10, pady=10)
        # Cache section
        ctk.CTkLabel(dialog, text="Cache:", font=("Ubuntu", 14, "bold"), 
                     text_color=POP_LIGHT).pack(anchor="w", padx=20, pady=(20, 5))
        self.cache_label = ctk.CTkLabel(
            dialog,
            text=f"{len(self.thumbnail_cache)} thumbnails cached",
            font=("Ubuntu", 11),
            text_color="gray"
        )
        self.cache_label.pack(anchor="w", padx=20, pady=(0, 5))
        ctk.CTkButton(
            dialog,
            text="Clear Cache",
            width=200,
            fg_color=POP_CYAN,
            hover_color="#3aa3b1",
            text_color="black",
            command=self.clear_cache
        ).pack(pady=5)
        # Close button
        ctk.CTkButton(dialog, text="Close", width=120, 
                      fg_color=POP_DARK, hover_color="#3a3839",
                      border_width=1, border_color=POP_CYAN,
                      command=dialog.destroy).pack(pady=30)

    def update_output(self):
        self.selected_output = self.output_var.get()
        self.save_config()

    def update_mute(self):
        self.muted = self.mute_var.get()
        self.mute_status_label.configure(
            text="🔇 Muted" if self.muted else "🔊 Sound On",
            text_color=POP_ORANGE if self.muted else POP_CYAN
        )
        self.save_config()
        
    def clear_cache(self):
        """Clear all cached thumbnails and refresh the video list"""
        # Clear the thumbnail cache dictionary
        self.thumbnail_cache.clear()
        
        # Remove temp files
        self.cleanup_thumbs()
        
        # Update the cache label
        if hasattr(self, 'cache_label'):
            self.cache_label.configure(text="0 thumbnails cached")
        
        # Refresh the video grid to regenerate thumbnails
        self.scan_folder()
        
        messagebox.showinfo("Cache Cleared", "All thumbnails have been cleared and the video list has been refreshed.")


    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    self.current_folder = data.get("folder")
                    self.selected_video = data.get("last_video")
                    self.selected_output = data.get("output", "* (All)")
                    self.muted = data.get("muted", True)
            except:
                pass

    def save_config(self):
        data = {
            "folder": self.current_folder,
            "last_video": self.selected_video,
            "output": self.selected_output,
            "muted": self.muted
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
            empty_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            empty_frame.pack(pady=60)
            
            ctk.CTkLabel(empty_frame, text="📁", font=("Ubuntu", 40)).pack(pady=10)
            ctk.CTkLabel(empty_frame, text="No folder selected", font=("Ubuntu", 16, "bold"), 
                         text_color=POP_LIGHT).pack(pady=5)
            ctk.CTkLabel(empty_frame, text="Click ⚙ Settings → Browse Folder to get started", 
                         font=("Ubuntu", 12), text_color="gray").pack(pady=5)
            return

        self.video_list = [os.path.join(self.current_folder, f) for f in sorted(os.listdir(self.current_folder)) if f.lower().endswith((".mp4", ".webm", ".mkv", ".mov", ".gif"))]

        if not self.video_list:
            empty_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            empty_frame.pack(pady=60)
            
            ctk.CTkLabel(empty_frame, text="🎥", font=("Ubuntu", 40)).pack(pady=10)
            ctk.CTkLabel(empty_frame, text="No supported videos found", font=("Ubuntu", 16, "bold"), 
                         text_color=POP_LIGHT).pack(pady=5)
            return

        columns = 4
        for i, path in enumerate(self.video_list):
            is_selected = path == self.selected_video
            
            card = ctk.CTkFrame(self.scroll_frame, corner_radius=16, border_width=2, 
                                width=240, height=290,
                                fg_color=POP_DARKER,
                                border_color=POP_CYAN if is_selected else POP_DARK)
            card.grid(row=i // columns, column=i % columns, padx=12, pady=12, sticky="n")
            card.grid_propagate(False)

            # Badge for selected video
            if is_selected:
                badge_frame = ctk.CTkFrame(card, fg_color=POP_CYAN, corner_radius=12)
                badge_frame.place(relx=0.85, rely=0.05, anchor="ne")
                
                # Audio status badge
                audio_badge = "🔇" if self.muted else "🔊"
                ctk.CTkLabel(badge_frame, text=f"Active {audio_badge}", font=("Ubuntu", 9, "bold"), 
                             text_color="black").pack(padx=8, pady=2)

            # Thumbnail frame
            thumb_frame = ctk.CTkFrame(
                card,
                fg_color="#1a1a1a",
                border_width=2,
                border_color=POP_CYAN if is_selected else "#333333",
                corner_radius=12,
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
            ctk.CTkLabel(card, text=short_name, wraplength=220, 
                         font=("Ubuntu", 12), text_color=POP_LIGHT).pack(pady=4)

            btn = ctk.CTkButton(card, text="Apply", width=120, 
                                fg_color=POP_ORANGE, hover_color="#e67e22",
                                text_color="black", command=lambda p=path: self.apply_wallpaper(p))
            btn.pack(pady=10)

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

        # Build mpvpaper command with or without audio based on mute state
        if self.muted:
            cmd = [
                "mpvpaper", output,
                path,
                "-o", "--loop=inf --no-audio --no-osc --hwdec=auto --really-quiet"
            ]
        else:
            cmd = [
                "mpvpaper", output,
                path,
                "-o", "--loop=inf --no-osc --hwdec=auto --really-quiet"
            ]

        try:
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio_status = "🔇 Muted" if self.muted else "🔊 With Sound"
            messagebox.showinfo("Success", f"Applied to {output}:\n{os.path.basename(path)}\n{audio_status}")
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
