import tkinter as tk
import json
import tkinter.filedialog as fd
import pystray
from PIL import Image
import threading
import sys
from datetime import datetime
import pyautogui
import os
from pynput import keyboard as pynput_keyboard


class DelayedToolTip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.after_id = None
        widget.bind('<Enter>', self.on_enter)
        widget.bind('<Leave>', self.on_leave)
    
    def on_enter(self, event=None):
        self.after_id = self.widget.after(self.delay, self.show_tip)
    
    def on_leave(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide_tip()
    
    def show_tip(self):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0",
                         relief=tk.SOLID, borderwidth=1, padx=5, pady=2)
        label.pack()
    
    def hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
    
    def update_text(self, new_text):
        self.text = new_text


class ScreenshotApp:
    def __init__(self):
        self.config = self.load_config()
        self.hotkey = self.config["Hotkey"]
        self.listener = None
        self.icon_path = "./icon.ico"
        self.running = True  # 添加运行标志
        
        self.create_tray_icon()
        self.create_window()
        self.win.after(100, self.start_hotkey_listener)
    
    def load_config(self) -> dict:
        try:
            with open("./config.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            config = {"Hotkey": "F10", "Destination": "..."}
            with open("./config.json", "w") as f:
                json.dump(config, f)
            return config
    
    def save_config(self):
        with open("./config.json", "w") as f:
            json.dump(self.config, f)
    
    def take_screenshot(self):
        save_path = self.config.get("Destination", "...")
        if save_path == "..." or not save_path:
            print("请先在设置中指定保存路径")
            return
        
        os.makedirs(save_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"screenshot_{timestamp}.png"
        full_path = os.path.join(save_path, filename)
        
        try:
            pyautogui.screenshot().save(full_path)
            print(f"截图已保存: {full_path}")
        except Exception as e:
            print(f"截图失败: {e}")
    
    def parse_hotkey(self, hotkey_str):
        """将热键字符串转换为 pynput 格式"""
        hotkey_lower = hotkey_str.lower()
        
        # 功能键映射
        special = {f'f{i}': f'<f{i}>' for i in range(1, 13)}
        special.update({
            'space': '<space>', 'enter': '<enter>', 'tab': '<tab>', 'esc': '<esc>',
            'up': '<up>', 'down': '<down>', 'left': '<left>', 'right': '<right>'
        })
        
        if hotkey_lower in special:
            return special[hotkey_lower]
        if len(hotkey_str) == 1 and (hotkey_str.isalpha() or hotkey_str.isdigit()):
            return hotkey_str.lower()
        
        print(f"不支持的热键: {self.hotkey}")
        return None
    
    def start_hotkey_listener(self):
        if self.listener:
            self.listener.stop()
        
        key = self.parse_hotkey(self.hotkey)
        if not key:
            return
        
        self.listener = pynput_keyboard.GlobalHotKeys({key: self.take_screenshot})
        threading.Thread(target=self.listener.run, daemon=True).start()
        print(f"热键 {self.hotkey} 已注册")
    
    def update_hotkey(self, new_hotkey):
        self.hotkey = new_hotkey
        self.config["Hotkey"] = new_hotkey
        self.save_config()
        self.start_hotkey_listener()
    
    def create_tray_icon(self):
        try:
            icon = Image.open(self.icon_path) if os.path.exists(self.icon_path) else Image.new('RGB', (64, 64), '#2E8B57')
        except:
            icon = Image.new('RGB', (64, 64), '#2E8B57')
        
        menu = pystray.Menu(
            pystray.MenuItem("Open window 打开窗口", self.show_window),
            pystray.MenuItem("Exit 退出", self.quit_app)
        )
        self.tray_icon = pystray.Icon("SFC", icon, "Silent Fullscreen Capturer", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_window(self):
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()
    
    def hide_window(self):
        self.win.withdraw()
    
    def quit_app(self):
        """退出程序 - 安全退出，不抛出异常"""
        self.running = False
        
        # 停止热键监听
        if self.listener:
            try:
                self.listener.stop()
            except:
                pass
        
        # 销毁窗口
        if self.win:
            try:
                self.win.quit()
                self.win.destroy()
            except:
                pass
        
        # 停止托盘图标
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        
        # 使用 after 延迟退出，避免在回调中直接调用 sys.exit
        def do_exit():
            sys.exit(0)
        
        if self.win:
            self.win.after(100, do_exit)
        else:
            do_exit()
    
    def update_folder_display(self):
        full = self.config["Destination"]
        display = full[:15] + "..." if len(full) > 18 else full
        self.folder_label.config(text=display if full != "..." else "...")
        self.folder_tooltip.update_text(full)
    
    def create_window(self):
        self.win = tk.Tk()
        self.win.geometry("350x200")
        self.win.resizable(False, False)
        self.win.title("SFC | 静默全屏截图")
        self.win.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # 设置图标
        if os.path.exists(self.icon_path):
            self.win.iconbitmap(self.icon_path)
        
        # 标题
        tk.Label(self.win, text="Silent Fullscreen Capturer", font=("Cascadia Code", 13)).place(anchor="n", x=175, y=15)
        tk.Label(self.win, text="静默全屏截图", font=("Cascadia Code", 18)).place(anchor="n", x=175, y=40)
        
        # 热键设置
        tk.Label(self.win, text="Hotkey 截图键:", font=("Cascadia Code", 10)).place(anchor="w", x=10, y=110)
        self.capture_key_label = tk.Label(self.win, text=self.config["Hotkey"], font=("Cascadia Code", 10))
        self.capture_key_label.place(anchor="e", x=340, y=110)
        DelayedToolTip(self.capture_key_label, "Click and press any key to change the hotkey\n点击后按任意键更改快捷键", 500)
        self.capture_key_label.bind("<Button-1>", lambda e: self.capture_key_label.focus_set())
        self.capture_key_label.bind("<KeyRelease>", self.input_hotkey)
        
        # 保存路径
        tk.Label(self.win, text="Destination 保存至:", font=("Cascadia Code", 10)).place(anchor="w", x=10, y=140)
        self.folder_label = tk.Label(self.win, text="", font=("Cascadia Code", 10), anchor="e")
        self.folder_label.place(anchor="e", x=340, y=140)
        self.folder_tooltip = DelayedToolTip(self.folder_label, self.config["Destination"], 300)
        
        tk.Button(self.win, text="Browse 浏览", font=("Cascadia Code", 10), relief="groove", 
                  command=self.open_folder).place(anchor="e", x=340, y=170)
        
        self.update_folder_display()
        self.win.withdraw()
    
    def input_hotkey(self, event):
        if event.keysym not in ["Escape", "Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R"]:
            self.capture_key_label.config(text=event.keysym)
            self.update_hotkey(event.keysym)
        self.win.focus_set()
    
    def open_folder(self):
        directory = fd.askdirectory()
        if directory:
            self.config["Destination"] = directory
            self.save_config()
            self.update_folder_display()
    
    def run(self):
        try:
            self.win.mainloop()
        finally:
            self.quit_app()


if __name__ == "__main__":
    app = ScreenshotApp()
    app.run()
