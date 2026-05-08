"""Tkinter desktop app for beginner macOS users."""

from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional, TypeVar

from .gui_controller import GuiValidationError, PhotoDateRescueGuiController
from .gui_models import DependencyStatus, GuiRepairSummary, GuiScanSummary

T = TypeVar("T")


class PhotoDateRescueApp:
    def __init__(self, root: tk.Tk, controller: Optional[PhotoDateRescueGuiController] = None) -> None:
        self.root = root
        self.controller = controller or PhotoDateRescueGuiController()
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.status_var = tk.StringVar(value="请选择安卓照片 / 视频导出文件夹和安全输出文件夹。")
        self.dependency_var = tk.StringVar(value="正在检查依赖...")
        self.source_button: Optional[ttk.Button] = None
        self.output_button: Optional[ttk.Button] = None
        self.scan_button: Optional[ttk.Button] = None
        self.repair_button: Optional[ttk.Button] = None
        self.open_button: Optional[ttk.Button] = None
        self._busy = False
        self._scan_completed = False
        self._output_ready = False
        self._build_ui()
        self._show_dependency_status()

    def _build_ui(self) -> None:
        self.root.title("PhotoDateRescue")
        self.root.geometry("780x560")
        self.root.minsize(700, 500)

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text="PhotoDateRescue", font=("Helvetica", 24, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            main,
            text="安卓换 iPhone 后，照片时间线乱了？这个工具会生成安全副本，不修改原文件。",
            wraplength=720,
        )
        subtitle.pack(anchor="w", pady=(6, 18))

        safety = ttk.Label(
            main,
            text="安全原则：先扫描，再修复；不自动导入 Apple Photos；不删除任何原始照片或视频。",
            foreground="#444444",
            wraplength=720,
        )
        safety.pack(anchor="w", pady=(0, 16))

        folder_frame = ttk.LabelFrame(main, text="1. 选择文件夹", padding=14)
        folder_frame.pack(fill="x", pady=(0, 14))
        folder_frame.columnconfigure(1, weight=1)

        ttk.Label(folder_frame, text="安卓导出文件夹").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(folder_frame, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", pady=6)
        self.source_button = ttk.Button(folder_frame, text="选择...", command=self.choose_source)
        self.source_button.grid(row=0, column=2, padx=(10, 0), pady=6)

        ttk.Label(folder_frame, text="安全输出文件夹").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(folder_frame, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", pady=6)
        self.output_button = ttk.Button(folder_frame, text="选择...", command=self.choose_output)
        self.output_button.grid(row=1, column=2, padx=(10, 0), pady=6)

        dependency_frame = ttk.LabelFrame(main, text="2. 环境状态", padding=14)
        dependency_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(dependency_frame, textvariable=self.dependency_var, wraplength=720, justify="left").pack(anchor="w")

        action_frame = ttk.LabelFrame(main, text="3. 扫描与修复", padding=14)
        action_frame.pack(fill="x", pady=(0, 14))

        self.scan_button = ttk.Button(action_frame, text="开始扫描", command=self.scan)
        self.scan_button.pack(side="left")
        self.repair_button = ttk.Button(action_frame, text="生成修复后的安全副本", command=self.repair, state="disabled")
        self.repair_button.pack(side="left", padx=(10, 0))
        self.open_button = ttk.Button(action_frame, text="打开输出文件夹", command=self.open_output, state="disabled")
        self.open_button.pack(side="left", padx=(10, 0))

        status_frame = ttk.LabelFrame(main, text="处理结果", padding=14)
        status_frame.pack(fill="both", expand=True)
        ttk.Label(status_frame, textvariable=self.status_var, wraplength=720, justify="left").pack(anchor="nw")

    def _show_dependency_status(self) -> None:
        statuses = self.controller.check_dependencies()
        lines = [self._format_dependency(status) for status in statuses]
        self.dependency_var.set("\n".join(lines))

    def _format_dependency(self, status: DependencyStatus) -> str:
        if status.available:
            return "{0}: 已找到{1}".format(status.name, "（{0}）".format(status.path) if status.path else "")
        prefix = "{0}: 缺少".format(status.name)
        if status.required:
            prefix += "（必需）"
        return "{0}。{1}".format(prefix, status.hint)

    def choose_source(self) -> None:
        if self._busy:
            return
        path = filedialog.askdirectory(title="选择安卓照片 / 视频导出文件夹")
        if path:
            self.source_var.set(path)
            self._suggest_output_from_source(path)

    def choose_output(self) -> None:
        if self._busy:
            return
        path = filedialog.askdirectory(title="选择安全输出文件夹")
        if path:
            self.output_var.set(path)

    def _suggest_output_from_source(self, source_path: str) -> None:
        if self.output_var.get().strip():
            return
        try:
            suggested = self.controller.suggest_output_folder(source_path)
        except GuiValidationError:
            return
        self.output_var.set(str(suggested))

    def scan(self) -> None:
        if self._busy:
            return
        self._run_background(
            busy_message="正在扫描，请稍等。大图库可能需要几分钟，窗口没有卡死。",
            worker=lambda: self.controller.scan(Path(self.source_var.get()), Path(self.output_var.get())),
            on_success=self._handle_scan_success,
            failure_title="扫描失败",
        )

    def _handle_scan_success(self, summary: GuiScanSummary) -> None:
        self._scan_completed = True
        self._output_ready = True
        self.status_var.set(self._format_scan_summary(summary))

    def _format_scan_summary(self, summary: GuiScanSummary) -> str:
        return (
            "扫描完成。\n"
            "共发现 {0} 个文件：照片 {1}，视频 {2}。\n"
            "可修复 {3}，正常 {4}，高风险 {5}，不支持 {6}，错误 {7}。\n"
            "报告位置：{8}\n\n"
            "下一步：请先看摘要。如果结果合理，再点击“生成修复后的安全副本”。"
        ).format(
            summary.total_files,
            summary.photo_files,
            summary.video_files,
            summary.repairable_files,
            summary.ok_files,
            summary.high_risk_files,
            summary.unsupported_files,
            summary.error_files,
            summary.report_dir,
        )

    def repair(self) -> None:
        if self._busy:
            return
        if not messagebox.askyesno("确认生成副本", "现在会生成修复后的安全副本，不会修改原始文件。继续吗？"):
            return
        self._run_background(
            busy_message="正在生成修复后的安全副本，请稍等。原始文件不会被修改。",
            worker=lambda: self.controller.repair(Path(self.source_var.get()), Path(self.output_var.get())),
            on_success=self._handle_repair_success,
            failure_title="生成失败",
        )

    def _handle_repair_success(self, summary: GuiRepairSummary) -> None:
        self._output_ready = True
        self.status_var.set(self._format_repair_summary(summary))

    def _format_repair_summary(self, summary: GuiRepairSummary) -> str:
        return (
            "生成完成。\n"
            "复制 {0}，修复 {1}，失败 {2}，跳过 {3}。\n"
            "输出位置：{4}\n\n"
            "建议：先抽查少量结果，再手动导入 Apple Photos。确认无误前，不要删除原始文件。"
        ).format(summary.copied, summary.repaired, summary.failed, summary.skipped, summary.output_dir)

    def open_output(self) -> None:
        if self._busy:
            return
        output = self.output_var.get()
        if not output:
            return
        subprocess.run(["open", output], check=False)

    def _run_background(
        self,
        busy_message: str,
        worker: Callable[[], T],
        on_success: Callable[[T], None],
        failure_title: str,
    ) -> None:
        self._set_busy(True, busy_message)

        def run() -> None:
            try:
                result = worker()
            except GuiValidationError as exc:
                message = str(exc)
                self.root.after(0, lambda message=message: self._finish_with_error(failure_title, message))
            except Exception as exc:  # pragma: no cover - exercised manually for environment-specific failures
                message = "原始文件没有被修改。错误：{0}".format(exc)
                self.root.after(0, lambda message=message: self._finish_with_error(failure_title, message))
            else:
                self.root.after(0, lambda result=result: self._finish_with_success(result, on_success))

        threading.Thread(target=run, daemon=True).start()

    def _finish_with_success(self, result: T, on_success: Callable[[T], None]) -> None:
        on_success(result)
        self._set_busy(False)

    def _finish_with_error(self, title: str, message: str) -> None:
        self.status_var.set("处理没有完成。请检查提示后重试，原始文件没有被修改。")
        self._set_busy(False)
        messagebox.showerror(title, message)

    def _set_busy(self, busy: bool, message: Optional[str] = None) -> None:
        self._busy = busy
        if message is not None:
            self.status_var.set(message)

        normal_or_disabled = "disabled" if busy else "normal"
        for button in (self.source_button, self.output_button, self.scan_button):
            if button is not None:
                button.configure(state=normal_or_disabled)

        if self.repair_button is not None:
            state = "normal" if (not busy and self._scan_completed) else "disabled"
            self.repair_button.configure(state=state)

        if self.open_button is not None:
            state = "normal" if (not busy and self._output_ready) else "disabled"
            self.open_button.configure(state=state)


def main() -> None:
    root = tk.Tk()
    PhotoDateRescueApp(root)
    root.mainloop()
