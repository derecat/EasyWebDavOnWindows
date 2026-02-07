from wsgidav import __version__ as wsgidav_version
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.fs_dav_provider import FilesystemProvider
from cheroot import wsgi
import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import sys

# 重定向控制台输出到GUI文本框的类
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        # 确保在主线程更新GUI
        self.text_widget.after(0, lambda: self.text_widget.insert(tk.END, string))
        self.text_widget.after(0, lambda: self.text_widget.see(tk.END))  # 自动滚动到底部

    def flush(self):
        pass  # 兼容flush方法，避免报错

class WebDAVGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"WebDAV 服务管理器 (wsgidav {wsgidav_version})")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        # 服务状态
        self.server = None
        self.server_thread = None
        self.is_running = False

        # 创建GUI布局
        self.create_widgets()

        # 重定向stdout和stderr到文本框
        self.redirector = RedirectText(self.log_text)
        sys.stdout = self.redirector
        sys.stderr = self.redirector
        
        # ========== 新增代码：打印绪山朝日地址到日志区 ==========
        print("绪山朝日：https://www.xiaoheihe.cn/app/user/profile/84805332")
        print("-" * 60 + "\n")
        # ======================================================

    def create_widgets(self):
        # 1. 配置区域
        config_frame = ttk.LabelFrame(self.root, text="服务配置")
        config_frame.pack(padx=10, pady=10, fill=tk.X)

        # 共享目录
        ttk.Label(config_frame, text="共享目录:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.folder_var = tk.StringVar(value=r"D:\Users\Administrator\Desktop\music")
        folder_entry = ttk.Entry(config_frame, textvariable=self.folder_var, width=50)
        folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(config_frame, text="浏览", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)

        # 端口
        ttk.Label(config_frame, text="端口:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar(value="8080")
        port_entry = ttk.Entry(config_frame, textvariable=self.port_var, width=20)
        port_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # 用户名
        ttk.Label(config_frame, text="用户名:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.user_var = tk.StringVar(value="admin")
        user_entry = ttk.Entry(config_frame, textvariable=self.user_var, width=20)
        user_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # 密码
        ttk.Label(config_frame, text="密码:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.pass_var = tk.StringVar(value="123456")
        pass_entry = ttk.Entry(config_frame, textvariable=self.pass_var, show="*", width=20)
        pass_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        # 2. 控制按钮区域
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(padx=10, pady=5, fill=tk.X)

        self.start_btn = ttk.Button(btn_frame, text="启动服务", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="停止服务", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(btn_frame, text="清空日志", command=self.clear_log)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 3. 日志区域
        log_frame = ttk.LabelFrame(self.root, text="运行日志")
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    def browse_folder(self):
        """选择共享目录"""
        folder = filedialog.askdirectory(title="选择共享目录")
        if folder:
            self.folder_var.set(folder)

    def validate_config(self):
        """验证配置是否合法"""
        # 检查端口是否为数字
        try:
            port = int(self.port_var.get())
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "端口必须是1-65535之间的数字！")
            return False

        # 检查用户名和密码是否为空
        if not self.user_var.get().strip():
            messagebox.showerror("错误", "用户名不能为空！")
            return False
        if not self.pass_var.get().strip():
            messagebox.showerror("错误", "密码不能为空！")
            return False

        # 检查共享目录（不存在则创建）
        share_folder = self.folder_var.get()
        if not os.path.exists(share_folder):
            try:
                os.makedirs(share_folder)
                print(f"已自动创建共享文件夹：{share_folder}")
            except Exception as e:
                messagebox.showerror("错误", f"创建共享目录失败：{str(e)}")
                return False

        return True

    def start_server(self):
        """启动WebDAV服务（在子线程中运行）"""
        if not self.validate_config():
            return

        if self.is_running:
            messagebox.showinfo("提示", "服务已在运行中！")
            return

        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 在子线程中启动服务，避免阻塞GUI
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def _run_server(self):
        """实际启动服务的函数（子线程）"""
        try:
            self.is_running = True

            # 获取配置
            share_folder = self.folder_var.get()
            port = int(self.port_var.get())
            username = self.user_var.get().strip()
            password = self.pass_var.get().strip()

            # 创建文件系统提供者
            provider = FilesystemProvider(share_folder)

            # 配置项（修复后的版本）
            config = {
            "host": "0.0.0.0",
            "port": port,
            "verbose": 1,
            "provider_mapping": {"/": provider},
            "simple_dc": {
                "user_mapping": {
                    "*": {  # * 表示所有 realm
                        username: {"password": password},
                    }
                }
            },
            "http_authenticator": {
                "domain_controller": None,
                "accept_basic": True,
                "accept_digest": False,
                "default_realm": "WebDAV",
                "default_to_anonymous": False,
            },
            "dir_browser": False  # 新增这一行：禁用目录浏览插件，避免依赖htdocs
        }

            # 创建并启动服务
            app = WsgiDAVApp(config)
            self.server = wsgi.Server(bind_addr=(config["host"], config["port"]), wsgi_app=app)

            # 打印启动信息
            print("=" * 60)
            print(f"✅ WebDAV 服务启动成功（需密码认证）")
            print(f"🔗 访问地址: http://{config['host']}:{config['port']}")
            print(f"📁 共享目录: {share_folder}")
            print(f"👤 用户名: {username} | 密码: {password}")
            print(f"📦 wsgidav 版本: {wsgidav_version}")
            print("=" * 60)

            # 启动服务（阻塞直到停止）
            self.server.start()

        except Exception as e:
            print(f"\n❌ 服务启动失败：{str(e)}")
            self.is_running = False
            # 恢复按钮状态
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def stop_server(self):
        """停止WebDAV服务"""
        if not self.is_running:
            messagebox.showinfo("提示", "服务未运行！")
            return

        try:
            if self.server:
                self.server.stop()
                self.is_running = False
                print("\n⚠️  WebDAV 服务已手动停止")
            
            # 恢复按钮状态
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("错误", f"停止服务失败：{str(e)}")
            print(f"\n❌ 停止服务失败：{str(e)}")

    def clear_log(self):
        """清空日志文本框"""
        self.log_text.delete(1.0, tk.END)
        # 清空后重新打印地址
        print("可以给电一电我吗？https://www.xiaoheihe.cn/app/user/profile/84805332")
        print("-" * 60 + "\n")

    def on_closing(self):
        """窗口关闭时的处理"""
        if self.is_running:
            if messagebox.askyesno("提示", "服务仍在运行中，是否停止并退出？"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WebDAVGUI(root)
    # 窗口关闭时的回调
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

    # 恢复stdout和stderr
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
