import os
import re
import json
import threading
import traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import chardet

from error_classifier import ErrorClassifier, ParsedError


class CK3LogParser:
    """CK3 Log Analyzer — анализ ошибок с привязкой к модам из Workshop"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CK3 Log Analyzer")
        self.root.geometry("1200x800")
        self._scanning = False
        # Классификатор ошибок
        self.classifier = ErrorClassifier()
        # Хранилища
        self.mod_errors = {}
        self.mod_cache = {}
        self.parsed_errors = []

        # 🟢 язык интерфейса и словарь переводов (двуязычный RU/EN)
        self.lang = tk.StringVar(value="ru")
        # попробуем загрузить язык из конфига ДО построения UI
        cfg_path = Path("config.json")
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if cfg.get("lang") in ("ru", "en"):
                        self.lang.set(cfg["lang"])
            except Exception:
                pass  # игнорируем ошибки
                
        self.translations = {
            "ru": {
                # GUI подписи
                "cfg": "Конфигурация",
                "logs": "Папка логов",
                "workshop": "Папка Workshop",
                "localmods": "Локальные моды",
                "browse": "Обзор",
                "scan": "🔍 Сканировать",
                "stop": "🟥 Стоп",
                "scanning": "Сканирование...",
                "export": "💾 Экспорт JSON",
                "open_log": "🧾 Открыть error.log",
                "check_conf": "🧩 Проверить конфликты",
                "show_window": "Показать окно",
                "exit": "Выход",
                "editor": "Редактор",
                "ready": "Готово",

                # Правая панель
                "info_actions": "Информация и действия",
                "file": "Файл",
                "line": "Строка",
                "type": "Тип",
                "message": "Сообщение",
                "open_folder": "📁 Открыть папку",
                "open_file": "📝 Открыть файл",
                "show_in_log": "🔍 Показать строку в error.log",
                "open_in_mod": "📄 Открыть строку в файле мода",

                # Универсальные сообщения
                "no_selection": "Нет выбора",
                "select_error": "Выберите ошибку в дереве.",
                "no_file": "Файл не найден",
                "no_error_log": "Файл error.log не найден.",
                "no_data": "Нет данных",
                "not_found": "Не найдено",
                "no_error": "Нет ошибки",
                "directory": "Это директория",
                "choose_node": "Выберите узел в дереве ошибок.",
                "no_mod": "Не удалось определить мод для {file}",
                "missing_dir": "Путь '{path}' отсутствует в {mod}",
                "analysis_done": "✅ Анализ завершён.",
                "analysis_start": "▶️ Начат анализ файла ошибок",
                "analysis_stop": "⛔ Остановка сканирования...",
                "analysis_error": "❌ Ошибка анализа",
                "export_done": "Отчёт сохранён:",
                "export_no_data": "Перед экспортом выполните анализ.",
                "export_success": "Отчёт сохранён: {path}",
                "export_failed": "Ошибка экспорта: {err}",
                "warn_no_data": "Перед экспортом выполните анализ.",
                "no_link": "Нет ссылки на строку в error.log", 
                "select_errorline": "Выберите конкретную строку ошибки, а не мод или файл.",
                "editor_not_found": "⚠️ Не найден выбранный редактор, открыт {file}",
                "notepadpp_not_found": "⚠️ Не найден Notepad++. Проверьте PATH или установку.",
                "notepad_line_jump": "ℹ️ Стандартный Notepad не поддерживает переход к строке.",
                "file_opened_no_jump": "⚠️ Файл открыт без перехода к строке: {file}",
                "file_open_error": "❌ Ошибка открытия {file}: {err}",
                "config_loaded": "⚙️ Настройки config.json загружены.",
                "config_load_error": "⚠️ Ошибка загрузки config.json: {err}",
                "config_saved": "💾 Настройки сохранены (config.json).",
                "config_save_error": "⚠️ Ошибка сохранения config.json: {err}",
                "copied_to_clipboard": "📋 Скопировано: {text}",
                "close": "Закрыть",                
                "scan_stop": "⛔ Остановка сканирования...",
                "log_not_found": "❌ error.log не найден. Укажите правильную папку в 'Logs Folder'.",
                "log_read": "📖 Чтение лога: {file}",
                "log_read_failed": "⚠️ Не удалось прочитать error.log (файл пуст или повреждён).",
                "classify_start": "▶️ Классификация ошибок...",
                "classify_empty": "⚠️ Ошибки не найдены в логе.",
                "classify_found": "Найдено {count} совпадений...",
                "classify_cats": "Категории: {stats}",
                "workshop_not_found": "⚠️ Указанная папка Workshop не найдена.",
                "build_struct_start": "🧩 Построение структуры модов...",
                "build_struct_done": "✅ Построение структуры завершено.",
                "mods_found": "📦 Обнаружено {count} модов с ошибками (всего записей: ~{errors}).",
                "analysis_done_log": "✅ Анализ завершён.",
                "analysis_failed": "❌ Ошибка анализа: {err}",
                "workshop_index": "📂 Индексируем Workshop ({total} модов)...",
                "index_error": "⚠️ Ошибка индексации {mod}: {err}",
                "index_done": "✅ Индексация завершена ({count} модов).",
                "process_errors": "🧩 Обработка {count} ошибок...",
                "scan_aborted": "⛔ Сканирование прервано пользователем.",
                "match_exact": "🟢 Exact match: {file} → {mod}",
                "match_indexed": "🟢 Indexed match: {file} → {mod}",
                "match_loose": "🟡 Loose match: {file} → {mod}",
                "bom_all_ok": "✅ Все '{file}' имеют корректную кодировку — ошибка из лога устарела?",
                "read_error": "⚠️ Ошибка чтения {file}: {err}",

                "mod_folder_opened": "📂 Открыта директория мода: {path}",
                "folder_opened": "📂 Открыта папка: {path}",
                "folder_not_found": "⚠️ Папка не найдена: {path} → {mod}",
                "skip_dir": "ℹ️ Пропущено открытие директории: {path}",
                "file_opened": "📝 Открыт файл: {file}",
                "file_not_found": "⚠️ Файл не найден: {file} в {mod}",

                "tray_created": "🟢 Иконка в трее создана",
                "icon_load_error": "⚠️ Ошибка загрузки иконки: {err}",
                "check_conflicts_start": "🧩 Проверка совместимости модов...",
                "check_conflicts_done": "✅ Проверка завершена. Конфликты показаны древовидно: мод → файлы → другие моды.",
                "file_or_folder": "Файл / Папка",
                "error_type": "Тип ошибки",
                "line_short": "Строка",
                "message_short": "Сообщение",
                "col_type": "Тип",
                "col_count": "Кол-во",
                "col_mods": "Другие моды",
                "col_note": "Комментарий",
                "line_opened_in": "📄 Открыта строка {line} в: {file}",
                "found_same_name": "🟡 Найден одноимённый файл: {file}",
                "file_not_found_simple": "⚠️ Файл не найден: {file}",
                "file_not_in_mod": "Файл {file} не найден в моде {mod}",
                "others_count": "{count} других",
                # Игровой набор
                "playset": "Игровой набор (Playset)",
                "playset_only": "Игровой набор",
                "browse_playset": "Обзор",
                "check_conf_playset": "🧩 Проверить конфликты (Playset)",
                "playset_load_error": "⚠️ Ошибка чтения файла набора: {err}",
                "playset_not_found": "⚠️ Файл набора не найден.",
                "playset_limited": "🎯 Проверка ограничена игровым набором ({count} модов).",                
                
            },

            "en": {
                # GUI labels
                "cfg": "Configuration",
                "logs": "Logs Folder",
                "workshop": "Workshop Folder",
                "localmods": "Local Mods",
                "browse": "Browse",
                "scan": "🔍 Scan",
                "stop": "🟥 Stop",
                "scanning": "Scanning...",
                "export": "💾 Export JSON",
                "open_log": "🧾 Open error.log",
                "check_conf": "🧩 Check Conflicts",
                "show_window": "Show window",
                "exit": "Exit",
                "editor": "Editor",
                "ready": "Ready",

                # Right panel
                "info_actions": "Information and Actions",
                "file": "File",
                "line": "Line",
                "type": "Type",
                "message": "Message",
                "open_folder": "📁 Open Folder",
                "open_file": "📝 Open File",
                "show_in_log": "🔍 Show line in error.log",
                "open_in_mod": "📄 Open line in mod file",

                # Messages
                "no_selection": "No selection",
                "select_error": "Select an error in the tree.",
                "no_file": "File not found",
                "no_error_log": "error.log not found.",
                "no_data": "No data available",
                "not_found": "Not found",
                "no_error": "No error",
                "directory": "This is a directory",
                "choose_node": "Select a node in the error tree.",
                "no_mod": "Unable to determine mod for {file}",
                "missing_dir": "Path '{path}' does not exist in {mod}",
                "analysis_done": "✅ Analysis complete.",
                "analysis_start": "▶️ Starting error log analysis...",
                "analysis_stop": "⛔ Stopping scan...",
                "analysis_error": "❌ Analysis failed",
                "export_done": "Report saved:",
                "export_no_data": "Run analysis before export.",
                "export_success": "Report saved: {path}",
                "export_failed": "Export error: {err}",
                "warn_no_data": "Run analysis before export.",
                "no_link": "No reference to line in error.log", 
                "select_errorline": "Select a specific error line, not a mod or file.",
                "editor_not_found": "⚠️ Selected editor not found, opened {file}", 
                "notepadpp_not_found": "⚠️ Notepad++ not found. Check PATH or installation.",
                "notepad_line_jump": "ℹ️ Standard Notepad does not support jumping to a line.",
                "file_opened_no_jump": "⚠️ File opened without jumping to line: {file}",
                "file_open_error": "❌ Failed to open {file}: {err}",
                "config_loaded": "⚙️ Config.json loaded.",
                "config_load_error": "⚠️ Config.json load error: {err}",
                "config_saved": "💾 Config.json saved.",
                "config_save_error": "⚠️ Config.json save error: {err}",
                "copied_to_clipboard": "📋 Copied: {text}",
                "close": "Close",                
                "scan_stop": "⛔ Stop scanning...",
                "log_not_found": "❌ error.log not found. Choose correct folder in 'Logs Folder'.",
                "log_read": "📖 Reading log: {file}",
                "log_read_failed": "⚠️ Cannot read error.log (empty or damaged).",
                "classify_start": "▶️ Classifying errors...",
                "classify_empty": "⚠️ No errors found in log.",
                "classify_found": "Found {count} matches...",
                "classify_cats": "Categories: {stats}",
                "workshop_not_found": "⚠️ Workshop folder not found.",
                "build_struct_start": "🧩 Building mod structure...",
                "build_struct_done": "✅ Building structure complete.",
                "mods_found": "📦 Found {count} mods with errors (total records: ~{errors}).",
                "analysis_done_log": "✅ Analysis complete.",
                "analysis_failed": "❌ Analysis failed: {err}",
                "workshop_index": "📂 Indexing Workshop ({total} mods)...",
                "index_error": "⚠️ Indexing error {mod}: {err}",
                "index_done": "✅ Indexing complete ({count} mods).",
                "process_errors": "🧩 Processing {count} errors...",
                "scan_aborted": "⛔ Scanning aborted by user.",
                "match_exact": "🟢 Exact match: {file} → {mod}",
                "match_indexed": "🟢 Indexed match: {file} → {mod}",
                "match_loose": "🟡 Loose match: {file} → {mod}",
                "bom_all_ok": "✅ All '{file}' files have correct encoding — log warning obsolete?",
                "read_error": "⚠️ Read error {file}: {err}",

                "mod_folder_opened": "📂 Mod folder opened: {path}",
                "folder_opened": "📂 Folder opened: {path}",
                "folder_not_found": "⚠️ Folder not found: {path} → {mod}",
                "skip_dir": "ℹ️ Directory opening skipped: {path}",
                "file_opened": "📝 File opened: {file}",
                "file_not_found": "⚠️ File not found: {file} in {mod}",

                "tray_created": "🟢 Tray icon created",
                "icon_load_error": "⚠️ Icon load error: {err}",
                "check_conflicts_start": "🧩 Checking mod compatibility...",
                "check_conflicts_done": "✅ Check complete. Conflicts shown: mod → files → other mods.",
                "file_or_folder": "File / Folder",
                "error_type": "Error Type",
                "line_short": "Line",
                "message_short": "Message",
                "col_type": "Type",
                "col_count": "Count",
                "col_mods": "Other Mods",
                "col_note": "Comment",
                "line_opened_in": "📄 Opened line {line} in: {file}",
                "found_same_name": "🟡 Found file with same name: {file}",
                "file_not_found_simple": "⚠️ File not found: {file}",
                "file_not_in_mod": "File {file} not found in mod {mod}",
                "others_count": "{count} others",
                # Playset
                "playset": "Playset File",
                "playset_only": "Playset",
                "browse_playset": "Browse",
                "check_conf_playset": "🧩 Check Conflicts (Playset)",
                "playset_load_error": "⚠️ Playset file read error: {err}",
                "playset_not_found": "⚠️ Playset file not found.",
                "playset_limited": "🎯 Check limited to selected playset ({count} mods).",

            }
        }

        # GUI элементы
        self.tree = None
        self.details_text = None
        self.log_text = None
        self.progress = None
        self.logs_entry = None
        self.workshop_entry = None
        self.localmods_entry = None
        
        self.status_var = tk.StringVar(value="Ready")
        self.editor_choice = tk.StringVar(value="vscode")  # по умолчанию VS Code
        
        # Настройки набора (Playset)
        self.playset_entry = None
        self.playset_path = tk.StringVar(value="")
        self.playset_enabled = tk.BooleanVar(value=False)
        
        # Рисуем интерфейс
        self._setup_ui()
        self._load_config()


    def i18n(self, key):
        return self.translations[self.lang.get()].get(key, key)
    # ──────────────────────────────── UI ────────────────────────────────
    def _setup_ui(self):
        t = self.i18n
        menubar = tk.Menu(self.root)
        langmenu = tk.Menu(menubar, tearoff=0)

        def change_language(lang_code):
            """Меняет язык и сохраняет выбор в config.json"""
            self.lang.set(lang_code)
            # 💾 сразу сохраняем язык в конфиг
            self._save_config()
            # 🔄 перерисовываем интерфейс
            self._redraw_ui()

        langmenu.add_radiobutton(label="Русский", variable=self.lang, value="ru", command=lambda: change_language("ru"))
        langmenu.add_radiobutton(label="English", variable=self.lang, value="en", command=lambda: change_language("en"))
        menubar.add_cascade(label="Language", menu=langmenu)
        self.root.config(menu=menubar)    
        """Создание интерфейса в один экран с вкладками и правой панелью"""
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ─── верхние настройки ─────────────────────────────────────
        cfg = ttk.LabelFrame(main, text=t("cfg"), padding=8)
        cfg.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(cfg, text=t("logs")).grid(row=0, column=0, sticky=tk.W)
        self.logs_entry = ttk.Entry(cfg, width=70)
        self.logs_entry.grid(row=0, column=1, padx=5)
        ttk.Button(cfg, text=t("browse"), command=self._browse_logs).grid(row=0, column=2)
        # ─── Workshop Folder ───
        ttk.Label(cfg, text=t("workshop")).grid(row=1, column=0, sticky=tk.W)
        self.workshop_entry = ttk.Entry(cfg, width=70)
        self.workshop_entry.grid(row=1, column=1, padx=5)
        ttk.Button(cfg, text=t("browse"), command=self._browse_workshop).grid(row=1, column=2)

        # ─── Новый блок: Local Mods Folder ───
        ttk.Label(cfg, text=t("localmods")).grid(row=2, column=0, sticky=tk.W)
        self.localmods_entry = ttk.Entry(cfg, width=70)
        self.localmods_entry.grid(row=2, column=1, padx=5)
        ttk.Button(cfg, text=t("browse"), command=self._browse_localmods).grid(row=2, column=2)

        # ─── Новый блок: Игровой набор (Playset) ───────────────────
        self.playset_check = ttk.Checkbutton(
            cfg, text=t("playset_only"), variable=self.playset_enabled, command=self._save_config)
        self.playset_check.grid(row=3, column=0, sticky=tk.W)

        self.playset_entry = ttk.Entry(cfg, width=70, textvariable=self.playset_path)
        self.playset_entry.grid(row=3, column=1, padx=5)
        ttk.Button(cfg, text=t("browse_playset"), command=self._browse_playset).grid(row=3, column=2)

        editor_frame = ttk.LabelFrame(cfg, text=t("editor"), padding=(5, 2))
        editor_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(8, 0))
        ttk.Radiobutton(editor_frame, text="VS Code",
                        variable=self.editor_choice, value="vscode").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(editor_frame, text="Notepad++",
                        variable=self.editor_choice, value="notepadpp").pack(side=tk.LEFT, padx=5)

        # ─── кнопки действий и статус ───────────────────────────────
        act = ttk.Frame(main)
        act.pack(fill=tk.X, pady=5)
        self.scan_btn = ttk.Button(act, text="🔍 Scan", command=self.start_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=3)
        ttk.Button(act, text=t("export"), command=self.export_json).pack(side=tk.LEFT, padx=3)
        ttk.Button(act, text=t("open_log"), command=self._open_error_log).pack(side=tk.LEFT, padx=3)
        ttk.Button(act, text=t("check_conf"), command=self._check_mod_conflicts).pack(side=tk.LEFT, padx=3)
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 5))

        # ─── основной горизонтальный разделитель: вкладки + панель ───
        splitter = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        splitter.pack(fill=tk.BOTH, expand=True)

        # =========== левая часть → Notebook с тремя вкладками ===========
        left = ttk.Frame(splitter)
        splitter.add(left, weight=5)
        notebook = ttk.Notebook(left)
        notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook = notebook

        # --- вкладка LOG ---
        tab_log = ttk.Frame(notebook, padding=5)
        self.log_text = scrolledtext.ScrolledText(tab_log, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        notebook.add(tab_log, text="🧾  Log")

        # --- вкладка ERRORS ---
        tab_err = ttk.Frame(notebook, padding=5)
        tab_err.rowconfigure(0, weight=1)
        tab_err.columnconfigure(0, weight=1)

        cols = ("type", "line", "message")
        self.tree = ttk.Treeview(tab_err, columns=cols, show="tree headings")
        self.tree.heading("#0", text=t("file_or_folder"))
        self.tree.heading("type", text=t("error_type"))
        self.tree.heading("line", text=t("line_short"))
        self.tree.heading("message", text=t("message_short"))

        yscroll = ttk.Scrollbar(tab_err, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        # 👇 Используем grid для правильного масштабирования
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        notebook.add(tab_err, text="📦  Errors by Mods")

        # --- вкладка CONFLICTS ---
        tab_conf = ttk.Frame(notebook, padding=5)
        tab_conf.rowconfigure(0, weight=1)
        tab_conf.columnconfigure(0, weight=1)

        # Дерево конфликтов: теперь иерархическое (мод → файлы → другие моды)
        self.conf_tree = ttk.Treeview(
            tab_conf,
            columns=("type", "count", "mods", "note"),
            show="tree headings",
        )
        for c, txt, w in [
            ("type", t("col_type"), 100),
            ("count", t("col_count"), 70),
            ("mods", t("col_mods"), 300),
            ("note", t("col_note"), 280),
        ]:
            self.conf_tree.heading(c, text=txt)
            self.conf_tree.column(c, width=w, anchor="w")
        # 👇 Обработка двойного клика на строке "Другие моды"
        self.conf_tree.bind("<Double-1>", self._on_conflict_double_click)
        
        yscroll_conf = ttk.Scrollbar(tab_conf, orient="vertical", command=self.conf_tree.yview)
        self.conf_tree.configure(yscrollcommand=yscroll_conf.set)

        # 👇 Используем grid для масштабирования
        self.conf_tree.grid(row=0, column=0, sticky="nsew")
        yscroll_conf.grid(row=0, column=1, sticky="ns")

        notebook.add(tab_conf, text="🧩  Conflicts")

        # по умолчанию открыть лог
        notebook.select(tab_log)

        # =========== правая часть → панель деталей файла ===========
        right = ttk.LabelFrame(splitter, text=t("info_actions"))
        splitter.add(right, weight=2)

        self.file_label = ttk.Label(right, text=f"{t('file')}: —")
        self.file_label.pack(anchor="w", pady=(5, 0), padx=5)
        self.line_label = ttk.Label(right, text=f"{t('line')}: —")
        self.line_label.pack(anchor="w", padx=5)
        self.type_label = ttk.Label(right, text=f"{t('type')}: —")
        self.type_label.pack(anchor="w", padx=5)
        self.msg_label  = ttk.Label(right, text=f"{t('message')}: —", wraplength=350)
        self.msg_label.pack(anchor="w", padx=5, pady=(0, 10))

        btns = ttk.Frame(right)
        btns.pack(fill=tk.X, pady=5, padx=5)
        ttk.Button(btns, text=t("open_folder"), command=self._open_selected_folder).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text=t("open_file"), command=self._open_selected_file).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text=t("show_in_log"), command=self._show_errorline_in_log).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text=t("open_in_mod"), command=self._open_error_in_mod_file).pack(fill=tk.X, pady=2)

        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._setup_copy_paste()

    def _redraw_ui(self):
        """Полная перерисовка интерфейса при смене языка без потери данных."""
        # ---- Сохраняем данные перед пересозданием ----
        saved_logs = self.logs_entry.get() if self.logs_entry else ""
        saved_ws = self.workshop_entry.get() if self.workshop_entry else ""
        saved_local = self.localmods_entry.get() if self.localmods_entry else ""
        saved_editor = self.editor_choice.get() if hasattr(self, "editor_choice") else "vscode"
        saved_playset = self.playset_path.get() if hasattr(self, "playset_path") else ""
        saved_playset_flag = self.playset_enabled.get() if hasattr(self, "playset_enabled") else False
        
        # Уничтожаем старые элементы
        for widget in self.root.winfo_children():
            widget.destroy()

        # ---- Пересоздаём интерфейс заново ----
        self._setup_ui()

        # ---- Восстанавливаем значения ----
        self.logs_entry.delete(0, tk.END)
        self.logs_entry.insert(0, saved_logs)
        self.workshop_entry.delete(0, tk.END)
        self.workshop_entry.insert(0, saved_ws)
        self.localmods_entry.delete(0, tk.END)
        self.localmods_entry.insert(0, saved_local)
        self.editor_choice.set(saved_editor)
        self.playset_path.set(saved_playset)
        self.playset_enabled.set(saved_playset_flag)
        # ---- Обновляем статус и заголовок ----
        self.root.title("CK3 Log Analyzer")
        self.status_var.set(self.i18n("ready"))

        # Обновляем иконку трея (чтобы переводы элементов меню тоже обновились)
        if hasattr(self, "tray_icon"):
            try:
                self.tray_icon.visible = False
                self.tray_icon.stop()
            except Exception:
                pass
            from threading import Thread
            from PIL import Image
            import pystray, os, sys
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_path, "icon.ico")
            try:
                image = Image.open(icon_path)
            except Exception:
                image = Image.new("RGB", (64, 64), "gray")

            menu = pystray.Menu(
                pystray.MenuItem(self.i18n("show_window"), lambda icon, item: self.root.deiconify()),
                pystray.MenuItem(self.i18n("exit"), lambda icon, item: os._exit(0))
            )
            from threading import Thread
            self.tray_icon = pystray.Icon("ck3logparser", image, "CK3 Log Analyzer", menu)
            Thread(target=self.tray_icon.run, daemon=True).start()

    def _open_error_in_mod_file(self):
        """Открывает строку ошибки непосредственно в нужном файле мода (с точным совпадением пути)."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(self.i18n("no_selection"), self.i18n("select_error"))
            return

        item = sel[0]
        vals = self.tree.item(item, "values")

        if not vals or len(vals) < 5:
            messagebox.showwarning(self.i18n("no_data"), self.i18n("warn_no_data"))
            return

        # безопасная распаковка
        err_type = vals[0] if len(vals) > 0 else ""
        line_str = vals[1] if len(vals) > 1 else ""
        err_msg  = vals[2] if len(vals) > 2 else ""
        log_line = vals[3] if len(vals) > 3 else ""
        err_file = vals[4] if len(vals) > 4 else ""
        mod_id   = vals[5] if len(vals) > 5 else ""  # 🟢 теперь учитываем шестой элемент

        line_num = int(line_str) if str(line_str).isdigit() else 1
        rel_path = (err_file or "").replace("\\", "/").lower().lstrip("./").strip("'")
        if not rel_path:
            parent = self.tree.parent(item)
            rel_path = self.tree.item(parent, "text").replace("\\", "/").lower()

        target_mod = self.mod_errors.get(mod_id)
        if target_mod:
            candidate = Path(target_mod["path"]) / rel_path
            if candidate.exists():
                self._open_file_at_line(candidate, line_num)
                self._log(self.i18n("line_opened_in").format(line=line_num, file=candidate))
                return

        # 🔍 fallback если прямого совпадения нет
        filename = Path(rel_path).name
        for mod in self.mod_errors.values():
            base = Path(mod.get("path", ""))
            for root, _, files in os.walk(base):
                for f in files:
                    if f.lower() == filename:
                        self._open_file_at_line(Path(root) / f, line_num)
                        self._log(self.i18n("found_same_name").format(file=Path(root) / f))
                        return

        messagebox.showinfo(self.i18n("not_found"), self.i18n("no_mod").format(file=rel_path))
        self._log(self.i18n("file_not_found_simple").format(file=rel_path))

    def _open_file_at_line(self, file_path, line_num=1):
        """Открывает указанный файл на заданной строке в выбранном редакторе."""
        import shutil, subprocess

        editor = self.editor_choice.get()
        path_str = str(Path(file_path).resolve())

        try:
            if editor == "vscode":
                exe = shutil.which("code")
                if exe:
                    subprocess.Popen([exe, "-g", f"{path_str}:{line_num}"])
                    return

            elif editor == "notepadpp":
                # 👇 Классический набор аргументов, который всегда работает
                possible_paths = [
                    shutil.which("notepad++"),
                    r"C:\Program Files\Notepad++\notepad++.exe",
                    r"C:\Program Files (x86)\Notepad++\notepad++.exe"
                ]
                exe = next((p for p in possible_paths if p and Path(p).exists()), None)
                if exe:
                    # /multiInst — всегда создаёт новое окно,
                    # -n<line> — переход к строке
                    subprocess.Popen([
                        exe,
                        "-multiInst",
                        f"-n{line_num}",
                        path_str
                    ],
                    shell=False)
                    return
                else:
                    self._log(self.i18n("notepadpp_not_found"))

            elif editor == "sublime":
                exe = shutil.which("subl")
                if exe:
                    subprocess.Popen([exe, f"{path_str}:{line_num}"])
                    return

            elif editor == "notepad":
                exe = shutil.which("notepad.exe")
                if exe:
                    subprocess.Popen([exe, path_str])
                    self._log(self.i18n("notepad_line_jump"))
                    return

            # fallback
            os.startfile(file_path)
            self._log(self.i18n("file_opened_no_jump").format(file=file_path))

        except Exception as e:
            self._log(self.i18n("file_open_error").format(file=file_path, err=e))

    # ──────────────────────────────── CONFIG ────────────────────────────────

    def _load_config(self):
        try:
            config_path = Path("config.json")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if cfg.get("logs_path"):
                    self.logs_entry.insert(0, cfg["logs_path"])
                if cfg.get("workshop_path"):
                    self.workshop_entry.insert(0, cfg["workshop_path"])
                if cfg.get("localmods_path"):
                    self.localmods_entry.insert(0, cfg["localmods_path"])
                if cfg.get("playset_path"):
                    self.playset_path.set(cfg["playset_path"])
                if cfg.get("playset_enabled") is not None:
                    self.playset_enabled.set(cfg["playset_enabled"])
                if cfg.get("editor") in ("vscode", "notepadpp"):
                    self.editor_choice.set(cfg["editor"])
                if cfg.get("lang") in ("ru", "en"):  # 🟢 восстанавливаем язык
                    self.lang.set(cfg["lang"])
                self._log(self.i18n("config_loaded"))
        except Exception as e:
            self._log(self.i18n("config_load_error").format(err=e))

    def _save_config(self):
        cfg = {
            "logs_path": self.logs_entry.get().strip(),
            "workshop_path": self.workshop_entry.get().strip(),
            "localmods_path": self.localmods_entry.get().strip(),  # 🟢 добавлено
            "editor": self.editor_choice.get(),
            "lang": self.lang.get(),     # 🟢 добавляем язык
            "playset_path": self.playset_path.get().strip(),
            "playset_enabled": self.playset_enabled.get(),
        }
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            self._log(self.i18n("config_saved"))
        except Exception as e:
            self._log(self.i18n("config_save_error").format(err=e))

    def _setup_copy_paste(self):
        """Общая система копирования (ПКМ и Ctrl+C)"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Copy", command=self._copy_text)

        widgets = []
        if self.tree:
            widgets.append(self.tree)
        if hasattr(self, "log_text") and self.log_text:
            widgets.append(self.log_text)

        for widget in widgets:
            widget.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
            widget.bind("<Control-c>", lambda e: self._copy_text())
            widget.bind("<Control-C>", lambda e: self._copy_text())

        if self.tree:
            self.tree.bind("<Control-c>", lambda e: self._copy_selected_tree_item())
            self.tree.bind("<Control-C>", lambda e: self._copy_selected_tree_item())            

    def _copy_selected_tree_item(self):
        """Копирует выделенную строку из дерева"""
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        # текст и значения
        text = self.tree.item(item, "text")
        vals = self.tree.item(item, "values")
        out = text
        if vals:
            out += "  |  " + "  |  ".join(str(v) for v in vals if v)
        self.root.clipboard_clear()
        self.root.clipboard_append(out)
        self._log(self.i18n("copied_to_clipboard").format(text=out))

    # ──────────────────────────────── LOG TOOLS ────────────────────────────────
    def _browse_logs(self):
        """Диалог выбора папки логов"""
        folder = filedialog.askdirectory(title=self.i18n("logs"))
        if folder:
            self.logs_entry.delete(0, tk.END)
            self.logs_entry.insert(0, folder)
            # 💾 сохраняем конфигурацию, сразу после выбора
            self._save_config()

    def _browse_workshop(self):
        """Диалог выбора папки Workshop"""
        folder = filedialog.askdirectory(title=self.i18n("workshop"))
        if folder:
            self.workshop_entry.delete(0, tk.END)
            self.workshop_entry.insert(0, folder)
            # 💾 сохраняем конфигурацию, сразу после выбора
            self._save_config()

    def _browse_localmods(self):
        """Диалог выбора папки локальных модов"""
        folder = filedialog.askdirectory(title=self.i18n("localmods"))
        if folder:
            self.localmods_entry.delete(0, tk.END)
            self.localmods_entry.insert(0, folder)
            self._save_config()

    def _browse_playset(self):
        """Выбор файла набора (Playset JSON)"""
        file_path = filedialog.askopenfilename(
            title=self.i18n("playset"),
            filetypes=[("JSON", "*.json"), ("All", "*.*")]
        )
        if file_path:
            self.playset_path.set(file_path)
            self._save_config()

    def _log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    def _copy_text(self):
        try:
            widget = self.root.focus_get()
            text = ""
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                try:
                    text = widget.get("sel.first", "sel.last")
                except tk.TclError:
                    text = widget.get("1.0", "end")
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            pass

    # ──────────────────────────────── ANALYSIS ────────────────────────────────
    def start_scan(self):
        if self._scanning:
            self._scanning = False
            self._log(self.i18n("scan_stop"))
            return

        self._scanning = True
        self.progress.start()
        self.scan_btn.config(text=self.i18n("stop"))
        self.status_var.set(self.i18n("scanning"))

        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        """Главный процесс анализа error.log"""
        try:
            # 1️⃣ Поиск файла error.log
            log_file = self._find_log_file()
            if not log_file:
                self._log(self.i18n("log_not_found"))
                return

            # 2️⃣ Чтение содержимого
            self._log(self.i18n("log_read").format(file=log_file))
            data = self._read_log_file(log_file)
            if not data:
                self._log(self.i18n("log_read_failed"))
                return

            # 3️⃣ Классификация строк
            self._log(self.i18n("classify_start"))
            parsed = self.classifier.classify_block(data)
            if not parsed:
                self._log(self.i18n("classify_empty"))
                return

            # 💾 сохраняем весь список в атрибут
            self.parsed_errors = parsed
            # создаём индекс для быстрого поиска ошибок по тексту
            self.error_index = {}
            for e in parsed:
                if e.message:
                    self.error_index.setdefault(e.message.strip(), []).append(e)            

            self._log(self.i18n("classify_found").format(count=len(parsed)))

            # 3.1️⃣ Вывод статистики по категориям
            cat_stat = {}
            for e in parsed:
                cat_stat[e.category] = cat_stat.get(e.category, 0) + 1
            sorted_cats = ', '.join(f"{k}: {v}" for k, v in sorted(cat_stat.items()))
            self._log(self.i18n("classify_cats").format(stats=sorted_cats))

            # 4️⃣ Сканирование Workshop
            ws_path = Path(self.workshop_entry.get().strip())
            local_path = Path(self.localmods_entry.get().strip())

            paths_to_check = []
            if ws_path.exists():
                paths_to_check.append(ws_path)
            if local_path.exists():
                paths_to_check.append(local_path)

            if not paths_to_check:
                self._log(self.i18n("workshop_not_found"))
                return

            # 5️⃣ Построение структуры модов и файлов
            self._log(self.i18n("build_struct_start"))
            self.mod_errors = {}

            for mod_dir in paths_to_check:
                self._log(f"📂 {self.i18n('workshop')} / {self.i18n('localmods')}: {mod_dir}")
                mods_part = self._build_mod_structure(parsed, mod_dir)
                self.mod_errors.update(mods_part)

            total_mods = len(self.mod_errors)
            total_errs = sum(
                len(v) if isinstance(v, list) else 0
                for mod in self.mod_errors.values()
                for v in mod.get("errors", {}).values()
            )
            self._log(self.i18n("mods_found").format(count=total_mods, errors=total_errs))

            # 6️⃣ Отображение в GUI
            self._display_mod_tree(self.mod_errors)
            self._log(self.i18n("analysis_done_log"))

        except Exception as e:
            self._log(self.i18n("analysis_failed").format(err=e))

        finally:
            self._scanning = False
            self.scan_btn.config(text="🔍 Scan")
            self.progress.stop()
            self.status_var.set("Ready")

    def _find_log_file(self) -> Path | None:
        base = Path(self.logs_entry.get())
        locations = [
            base,
            base / "logs",
            Path.home() / "Documents" / "Paradox Interactive" / "Crusader Kings III" / "logs"
        ]
        for loc in locations:
            f = loc / "error.log"
            if f.exists():
                return f
        return None

    def _read_log_file(self, file_path: Path) -> str | None:
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
                enc = chardet.detect(raw)["encoding"] or "utf-8"
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                return f.read()
        except Exception as e:
            self._log(self.i18n("read_error").format(file=file_path, err=e))
            return None

    # ──────────────────────────────── CORE STRUCTURE ────────────────────────────────

    def _build_mod_structure(self, parsed_errors, ws_path: Path):
        """
        Распределяет ошибки по структуре модов.
        Делает точное сопоставление путей (common/...),
        добавляет реальную проверку кодировки для ENCODING_ERROR.
        """

        import fnmatch

        def _check_bom_encoding(file_path: Path):
            """Проверяет наличие BOM и корректность UTF-8 кодировки"""
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
                has_bom = data.startswith(b"\xef\xbb\xbf")
                import chardet
                enc = chardet.detect(data)["encoding"] or ""
                ok = enc.lower().startswith("utf") and has_bom
                return ok, enc, has_bom
            except Exception:
                return False, "unknown", False

        mods: dict[str, dict] = {}
        file_index: dict[str, dict[str, Path]] = {}

        mod_dirs = [d for d in ws_path.iterdir() if d.is_dir()]
        total_mods = len(mod_dirs)
        self._log(self.i18n("workshop_index").format(total=total_mods))

        # ─── Индексация Workshop ──────────────────────────────────────
        self.progress.start()
        for i, mod_dir in enumerate(mod_dirs, 1):
            try:
                info = self.get_mod_info(mod_dir)
                # добавляем id внутрь словаря, чтобы он не терялся потом
                mods[info["id"]] = {
                    "id": info["id"],        # 🟢 добавлен ключ id
                    "name": info["name"],
                    "path": str(mod_dir),
                    "errors": {}
                }

                rel_index = {}
                for root, _, files in os.walk(mod_dir):
                    for f in files:
                        if not f.lower().endswith((".txt", ".gui", ".yml", ".csv")):
                            continue
                        try:
                            rel_path = str(Path(root).relative_to(mod_dir) / f).replace("\\", "/").lower()
                            rel_index[rel_path] = Path(root) / f
                        except Exception:
                            continue
                file_index[info["id"]] = rel_index

            except Exception as e:
                self._log(self.i18n("index_error").format(mod=mod_dir, err=e))

            if i % 5 == 0 or i == total_mods:
                self.status_var.set(f"Indexing Workshop... {i}/{total_mods}")
                self.root.update_idletasks()

        self.progress.stop()
        self._log(self.i18n("index_done").format(count=len(file_index)))
        self._log(self.i18n("process_errors").format(count=len(parsed_errors)))

        # ─── Распределение ошибок ────────────────────────────────────
        self.progress.start()
        for i, err in enumerate(parsed_errors, 1):
            if not self._scanning:
                self._log(self.i18n("scan_aborted"))
                break
            if not err.file:
                continue

            # 🩹 добавляем .txt только для Unrecognized loc key
            if (err.type in {"UNRECOGNIZED_LOC_KEY_SIMPLE", "UNRECOGNIZED_LOC_KEY_NEAR"}
                    and '/' not in err.file
                    and not err.file.lower().endswith(('.txt', '.yml', '.gui', '.dds', '.csv'))):
                rel_key = f"{err.file}.txt"
            else:
                rel_key = err.file.strip().replace("\\", "/").lower().lstrip("./").strip("'")

            # спец-обработка для ENCODING_ERROR (BOM-ошилки)
            if err.type == "ENCODING_ERROR":
                possible_rel_keys = [
                    rel_key,
                    "mod/" + rel_key,
                    "content/" + rel_key,
                    "game/" + rel_key,
                ]
            else:
                possible_rel_keys = [rel_key]

            found_in_mod = None
            found_path: Path | None = None

            # ── 1. Точное совпадение полного пути ─────────────────────
            for rel_variant in possible_rel_keys:
                rel_variant = rel_variant.strip("./").replace("\\", "/").lower()
                for mod_id, mod_info in mods.items():
                    mod_path = Path(mod_info.get("path", ""))
                    if not mod_path.exists():
                        continue
                    candidate = (mod_path / rel_variant).resolve()
                    if candidate.exists():
                        found_in_mod = mod_id
                        found_path = candidate
                        self._log(self.i18n("match_exact").format(file=rel_variant, mod=mod_info["name"]))
                        break
                if found_in_mod:
                    break

            # ── 2. Совпадение по индексу файлов ───────────────────────
            if not found_in_mod:
                for mod_id, rel_index in file_index.items():
                    if rel_key in rel_index:
                        found_in_mod = mod_id
                        found_path = rel_index[rel_key]
                        self._log(self.i18n("match_indexed").format(file=rel_key, mod=mods[mod_id]["name"]))
                        break

            # ── 3. Поиск среди всех модов одинаковых файлов и проверка BOM ───────
            if err.type == "ENCODING_ERROR":
                directory, filename = os.path.split(rel_key)
                same_named = []
                for mod_id, rel_index in file_index.items():
                    for rel, p in rel_index.items():
                        if rel.endswith("/" + filename):
                            same_named.append((mod_id, p))

                if not same_named:
                    continue

                # Проверяем каждый найденный файл
                self._log(f"🔍 Найдено {len(same_named)} файлов '{filename}' в разных модах:")
                bad_files = []
                for mid, path_ in same_named:
                    ok, enc, has_bom = _check_bom_encoding(path_)
                    status = "OK" if ok else "BAD"
                    self._log(
                        f"   {mods[mid]['name']} → {path_.relative_to(ws_path)} "
                        f"| encoding={enc}, BOM={'yes' if has_bom else 'no'} → {status}"
                    )
                    if not ok:
                        bad_files.append((mid, path_, enc, has_bom))

                if not bad_files:
                    # если все норм — просто пропускаем ошибку
                    self._log(self.i18n("bom_all_ok").format(file=filename))
                    continue

                # Для каждого bad‑файла добавляем ошибку в соответствующий мод
                for mid, path_, enc, has_bom in bad_files:
                    mark = "✅" if has_bom else "❌"
                    self._log(
                        f"{mark} {path_.name}: encoding={enc or 'n/a'}, BOM={'yes' if has_bom else 'no'} "
                        f"→ {mods[mid]['name']}"
                    )
                    mod_info = mods[mid]
                    rel_path = str(path_.relative_to(mod_info["path"])).replace("\\", "/")
                    self._insert_mod_error(mod_info["errors"], rel_path, err)

                continue  # важное — чтобы не проходить прочие поиски ниже

            # ── 4. Последний запасной поиск по имени ───────────────
            if not found_in_mod:
                directory, pattern = os.path.split(rel_key)
                for mod_id, rel_index in file_index.items():
                    for rel, p in rel_index.items():
                        if fnmatch.fnmatch(Path(rel).name.lower(), pattern.lower()):
                            found_in_mod, found_path = mod_id, p
                            break
                if found_in_mod:
                    self._log(self.i18n("match_loose").format(file=pattern, mod=mods[found_in_mod]["name"]))

            # ── Добавляем ошибку ───────────────────────────────────────
            if found_in_mod and found_path:
                try:
                    # 🔍 Проверяем кодировку для ENCODING_ERROR
                    if err.type == "ENCODING_ERROR":
                        ok, enc, has_bom = _check_bom_encoding(found_path)
                        mark = "✅" if ok else "❌"
                        self._log(
                            f"{mark} {found_path.name}: encoding={enc or 'n/a'}, BOM={'yes' if has_bom else 'no'} "
                            f"→ {mods[found_in_mod]['name']}"
                        )

                    mod_info = mods[found_in_mod]
                    rel_path = str(found_path.relative_to(mod_info["path"])).replace("\\", "/")
                    self._insert_mod_error(mod_info["errors"], rel_path, err)
                    continue
                except Exception:
                    pass

            # если не нашли — кладем в Unknown
            mods.setdefault("Unknown", {"name": "Unknown Origin", "errors": {}})
            self._insert_mod_error(mods["Unknown"]["errors"], rel_key, err)

            if i % 200 == 0 or i == len(parsed_errors):
                self.status_var.set(f"Linking errors... {i}/{len(parsed_errors)}")
                self.root.update_idletasks()

        self.progress.stop()
        self._log(self.i18n("build_struct_done"))

        # Убираем моды без ошибок
        mods = {mid: m for mid, m in mods.items() if m.get("errors")}
        return mods

    def _check_mod_conflicts(self):
        """
        Проверка Workshop и локальных модов на конфликты и зависимости.
        Отображает древовидно: мод → файлы → другие моды.
        """
        t = self.i18n
        self.notebook.select(2)
        self.conf_tree.configure(show="tree headings")
        self.conf_tree.delete(*self.conf_tree.get_children())

        # 🟢 Сбор путей для анализа
        ws_path = Path(self.workshop_entry.get().strip())
        local_path = Path(self.localmods_entry.get().strip())
        paths_to_check = []
        if ws_path.exists():
            paths_to_check.append(ws_path)
        if local_path.exists():
            paths_to_check.append(local_path)

        if not paths_to_check:
            messagebox.showwarning(self.i18n("analysis_error"), self.i18n("workshop_not_found"))
            return

        # ⚙️ Если активен фильтр по набору (Playset)
        playset_ids = set()
        if self.playset_enabled.get():
            playset_file = Path(self.playset_path.get().strip())
            if playset_file.exists():
                try:
                    with open(playset_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    playset_ids = {m["steamId"] for m in data.get("mods", []) if m.get("enabled", True)}
                    self._log(self.i18n("playset_limited").format(count=len(playset_ids)))
                except Exception as e:
                    self._log(self.i18n("playset_load_error").format(err=e))
            else:
                self._log(self.i18n("playset_not_found"))

        self._log(self.i18n("check_conflicts_start"))
        duplicates: dict[str, list[str]] = {}
        mod_info: dict[str, dict] = {}

        # 🔁 Проходим по всем каталогам модов (Workshop + Local Mods)
        for base_path in paths_to_check:
            if not base_path.exists():
                continue

            mods = [d for d in base_path.iterdir() if d.is_dir()]
            # фильтрация по Playset, если задан
            if playset_ids:
                mods = [d for d in mods if any(d.name.endswith(mid) for mid in playset_ids)]

            for mod_dir in mods:
                mid = mod_dir.name
                desc = mod_dir / "descriptor.mod"
                name, replaces, deps, remote_id = None, [], [], None

                # чтение descriptor.mod
                if desc.exists():
                    try:
                        with open(desc, "r", encoding="utf-8-sig", errors="ignore") as f:
                            lines = f.readlines()
                        for i, line in enumerate(lines):
                            s = line.strip()
                            if s.lower().startswith("name="):
                                name = s.split("=", 1)[1].strip().strip('"')
                            elif s.lower().startswith("replace_path"):
                                replaces.append(s.split("=", 1)[1].strip().strip('"{} '))
                            elif s.lower().startswith("remote_file_id="):
                                remote_id = s.split("=", 1)[1].strip().strip('"')
                            elif s.lower().startswith("dependencies"):
                                import re
                                joined = "".join(lines[i : i + 20])
                                m = re.search(r"dependencies\s*=\s*\{([^}]*)\}", joined, re.IGNORECASE | re.DOTALL)
                                if m:
                                    inner = m.group(1)
                                    deps += re.findall(r'"([^"]+)"', inner)
                    except Exception as e:
                        self._log(f"⚠️ Ошибка чтения {desc}: {e}")

                mod_info[mid] = {
                    "id": mid,
                    "name": name or f"Mod_{mid}",
                    "replaces": replaces,
                    "deps": deps,
                    "remote_id": remote_id,
                    "files": set(),
                    "path": str(mod_dir)
                }

                # индексация файлов
                for root, _, files in os.walk(mod_dir):
                    for f in files:
                        if not f.lower().endswith((".txt", ".yml", ".gui", ".csv")):
                            continue
                        rel = str(Path(root).relative_to(mod_dir) / f).replace("\\", "/").lower()
                        duplicates.setdefault(rel, []).append(mid)
                        mod_info[mid]["files"].add(rel)

        # ─── построение дерева в UI ───
        for mid, info in sorted(mod_info.items(), key=lambda x: x[1]["name"].lower()):
            mod_node = self.conf_tree.insert(
                "",
                "end",
                text=f"{info['name']} (ID: {mid})",
                values=("", "", "", ""),
                open=False,
            )

            # replace_path из descriptor.mod
            for r in info["replaces"]:
                self.conf_tree.insert(mod_node, "end",
                    text=f"[replace_path] {r}",
                    values=("override", "", "", "")
                )

            # dependencies
            if info["deps"]:
                self.conf_tree.insert(mod_node, "end",
                    text=f"[dependencies] {', '.join(info['deps'])}",
                    values=("dependency", "", "", "")
                )

            # конфликты по файлам
            for file_rel in sorted(info["files"]):
                mod_list = duplicates.get(file_rel, [])
                if len(mod_list) > 1:  # конфликт ≥2 модов
                    others = [mod_info[m]["name"] for m in mod_list if m != mid]
                    self.conf_tree.insert(
                        mod_node,
                        "end",
                        text=file_rel,
                        values=(
                            "conflict",
                            t("others_count").format(count=len(others)),
                            ", ".join(others),
                            "",
                        ),
                    )

        self._log(self.i18n("check_conflicts_done"))

    def _insert_mod_error(self, tree, rel_path, err: ParsedError):
        """Добавляет ошибку в иерархическую структуру мод/папка/файл"""
        parts = rel_path.split("/")
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node.setdefault(parts[-1], []).append(err)

    def get_mod_info(self, mod_dir: Path):
        """Читает название мода даже при нестандартных .mod файлах"""
        mod_id = mod_dir.name
        if mod_id in self.mod_cache:
            return self.mod_cache[mod_id]

        mod_name = f"Mod_{mod_id}"
        mod_path = str(mod_dir)

        # приоритет — descriptor.mod и стандартные комбинации
        candidates = [
            mod_dir / "descriptor.mod",
            mod_dir / f"{mod_id}.mod"
        ]

        # если не нашли — добавить все *.mod из корня
        mod_files = list(mod_dir.glob("*.mod"))
        for f in mod_files:
            if f not in candidates:
                candidates.append(f)

        # пройти все возможные файлы и искать name=
        for desc in candidates:
            if not desc.exists():
                continue
            try:
                with open(desc, "r", encoding="utf-8-sig", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.lower().startswith("name="):
                            raw = line.split("=", 1)[1].strip().strip('"')
                            if raw:
                                mod_name = raw
                                break
            except Exception as e:
                self._log(f"⚠️ Ошибка чтения {desc}: {e}")
            if mod_name != f"Mod_{mod_id}":
                break  # нашли корректное имя — выходим

        info = {"id": mod_id, "name": mod_name, "path": mod_path}
        self.mod_cache[mod_id] = info
        return info

    # ──────────────────────────────── TREE DISPLAY ────────────────────────────────
    def _display_mod_tree(self, mods):
        self.tree.delete(*self.tree.get_children())
        for mod_id, mod in sorted(mods.items(), key=lambda x: x[1]["name"].lower()):
            mod_node = self.tree.insert(
                "",
                "end",
                text=f"{mod['name']} (ID: {mod_id})",
                open=False,
                values=("", "", "", "", "", mod_id)  # 🟢 добавляем id мода как 6‑й элемент
            )
            self._add_tree_nodes(mod_node, mod["errors"], mod_id=mod_id)

    def _add_tree_nodes(self, parent, data, prefix="", mod_id=None):
        for name, content in sorted(data.items(), key=lambda x: x[0].lower()):
            new_prefix = f"{prefix}/{name}" if prefix else name
            if isinstance(content, dict):
                node = self.tree.insert(
                    parent, "end",
                    text=name,
                    values=("", "", "", "", new_prefix, mod_id)  # 🟢 сохраняем и путь, и мод
                )
                self._add_tree_nodes(node, content, new_prefix, mod_id)
            else:
                real_file_path = ""
                for err in content:
                    if err.file:
                        real_file_path = err.file
                        break
                file_node = self.tree.insert(
                    parent, "end",
                    text=name,
                    values=("", "", "", "", real_file_path or new_prefix, mod_id)
                )
                for err in sorted(content,
                                  key=lambda e: int(e.line) if (e.line and str(e.line).isdigit()) else 0):
                    self.tree.insert(
                        file_node,
                        "end",
                        values=(
                            err.type,
                            err.line or "",
                            err.message or "",
                            err.log_line or "",
                            err.file or new_prefix,
                            mod_id,  # 🟢 прокидываем id мода в ошибки тоже
                        )
                    )

    # ──────────────────────────────── Новые действия ────────────────────────────────
    def _open_selected_folder(self):
        """Открывает именно ту папку, что принадлежит корректному моду."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(self.i18n("no_selection"), self.i18n("select_error"))
            return

        item = sel[0]
        vals = self.tree.item(item, "values")
        rel_path = (vals[4] or "") if len(vals) >= 5 else ""
        mod_id = (vals[5] or "") if len(vals) >= 6 else ""
        rel_path = rel_path.replace("\\", "/").lstrip("./").strip("'")

        # Если выбран корневой мод
        if not rel_path and mod_id:
            mod = self.mod_errors.get(mod_id)
            if mod and mod.get("path"):
                os.startfile(mod["path"])
                self._log(self.i18n("mod_folder_opened").format(path=mod["path"]))
                return
            messagebox.showinfo(self.i18n("not_found"), self.i18n("no_mod").format(file=mod_id))
            return

        # Если это подпапка
        target_mod = self.mod_errors.get(mod_id)
        if not target_mod:
            messagebox.showinfo(self.i18n("not_found"), self.i18n("no_mod").format(file=rel_path))
            return

        mod_path = Path(target_mod["path"])
        target = (mod_path / rel_path).resolve()
        if target.exists():
            folder = target if target.is_dir() else target.parent
            os.startfile(folder)
            self._log(self.i18n("folder_opened").format(path=folder))
        else:
            messagebox.showinfo(self.i18n("not_found"), self.i18n("missing_dir").format(path=rel_path, mod=mod_path))
            self._log(self.i18n("folder_not_found").format(path=rel_path, mod=mod_path))

    def _open_selected_file(self):
        """Открывает файл, принадлежащий конкретному моду."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(self.i18n("no_selection"), self.i18n("select_error"))
            return

        item = sel[0]
        vals = self.tree.item(item, "values")
        rel_path = (vals[4] or "") if len(vals) >= 5 else ""
        mod_id = (vals[5] or "") if len(vals) >= 6 else ""
        if not rel_path:
            rel_path = self.tree.item(item, "text")
        rel_path = rel_path.replace("\\", "/").lstrip("./").strip("'")

        target_mod = self.mod_errors.get(mod_id)
        if not target_mod:
            messagebox.showinfo(self.i18n("not_found"), self.i18n("no_mod").format(file=rel_path))
            return

        p = (Path(target_mod["path"]) / rel_path).resolve()
        if p.exists():
            if p.is_dir():
                messagebox.showinfo(self.i18n("directory"), f"{p} — {self.i18n('directory').lower()}.")
                self._log(self.i18n("skip_dir").format(path=p))
                return
            os.startfile(p)
            self._log(self.i18n("file_opened").format(file=p))
        else:
            messagebox.showinfo(self.i18n("not_found"),
                    self.i18n("file_not_in_mod").format(file=rel_path, mod=target_mod["name"]))
            self._log(self.i18n("file_not_found").format(file=rel_path, mod=mod_id))

    def _show_errorline_in_log(self):
        """Открывает error.log и позиционирует на строке, где расположено сообщение об ошибке."""
        log_file = self._find_log_file()
        if not log_file or not log_file.exists():
            messagebox.showinfo(self.i18n("no_error_log"), self.i18n("no_error_log"))
            return

        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(self.i18n("no_error"), self.i18n("select_error"))
            return

        item = sel[0]
        parent = self.tree.parent(item)

        # 🚫 если выбран не элемент с ошибкой
        if not parent:
            messagebox.showinfo(self.i18n("no_error"), self.i18n("choose_node"))
            return

        values = self.tree.item(item, "values")
        if not values or len(values) < 4:
            messagebox.showinfo(self.i18n("no_data"), self.i18n("warn_no_data"))
            return

        # log_line хранится в 4‑м элементе values
        log_line = values[3]
        if not log_line or not str(log_line).isdigit():
            messagebox.showinfo(self.i18n("no_link"), self.i18n("select_errorline"))
            return

        line_num = int(log_line)
        self._open_file_at_line(log_file, line_num)
        self._log(f"🪶 Переход к строке {line_num} в error.log ({log_file})")

    def _open_error_log(self):
        """Открывает error.log в выбранном редакторе."""
        log_file = self._find_log_file()
        if not log_file or not log_file.exists():
            messagebox.showinfo(self.i18n("no_error_log"), self.i18n("no_error_log"))
            return

        editor = self.editor_choice.get()

        import shutil, subprocess
        if editor == "vscode":
            exe = shutil.which("code")
            if exe:
                subprocess.Popen([exe, str(log_file)])
                return
        elif editor == "notepadpp":
            exe = shutil.which("notepad++")
            if exe:
                subprocess.Popen([exe, str(log_file)])
                return

        os.startfile(log_file)
        self._log(self.i18n("editor_not_found").format(file=log_file))

    # ──────────────────────────────── Обновлённый выбор ────────────────────────────────
    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        vals = self.tree.item(item, "values")
        if not vals:
            return

        # безопасно извлекаем первые три
        err_type = vals[0] if len(vals) > 0 else ""
        err_line = vals[1] if len(vals) > 1 else ""
        err_msg  = vals[2] if len(vals) > 2 else ""
        text = self.tree.item(item, "text")


        t = self.i18n
        self.file_label.config(text=f"{t('file')}: {text}")
        self.line_label.config(text=f"{t('line')}: {err_line or '—'}")
        self.type_label.config(text=f"{t('type')}: {err_type or '—'}")
        msg_short = (err_msg if len(err_msg) < 150 else err_msg[:147] + "…")
        self.msg_label.config(text=f"{t('message')}: {msg_short}")

    # ──────────────────────────────── EXPORT ────────────────────────────────
    def export_json(self):
        if not self.mod_errors:
            messagebox.showwarning(self.i18n("no_data"), self.i18n("warn_no_data"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            data = {}
            for mod_id, mod in self.mod_errors.items():
                data[mod_id] = {
                    "name": mod["name"],
                    "errors": self._flatten_errors(mod["errors"])
                }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo(self.i18n("export_done"), self.i18n("export_success").format(path=path))
        except Exception as e:
            messagebox.showerror(self.i18n("analysis_error"), self.i18n("export_failed").format(err=e))

    def _flatten_errors(self, errors_tree):
        """Разворачивает дерево для JSON экспорта"""
        flat = {}

        def walk(prefix, node):
            for k, v in node.items():
                if isinstance(v, dict):
                    walk(prefix + "/" + k if prefix else k, v)
                else:
                    flat[prefix + "/" + k if prefix else k] = [e.to_dict() for e in v]

        walk("", errors_tree)
        return flat

    # ──────────────────────────────── UTILITY ────────────────────────────────
    def toggle_scope(self):
        self.show_scope = not self.show_scope

    # ────────────────────────────── POPUP ДЛЯ "ДРУГИЕ МОДЫ" ──────────────────────────────
    def _on_conflict_double_click(self, event):
        """Реакция на двойной клик по элементу в дереве конфликтов."""
        item = self.conf_tree.identify_row(event.y)
        column = self.conf_tree.identify_column(event.x)
        if not item or column != "#3":  # "#3" — третий столбец ("mods")
            return

        values = self.conf_tree.item(item, "values")
        if not values or len(values) < 3:
            return

        mods_raw = values[2] or ""
        if not mods_raw.strip():
            return

        mods_list = [m.strip() for m in mods_raw.split(",") if m.strip()]
        if not mods_list:
            return

        self._show_mods_popup(mods_list, x=event.x_root, y=event.y_root)

    def _show_mods_popup(self, mods_list, x=0, y=0):
        """Создаёт всплывающее окно с прокручиваемым списком 'Другие моды'."""
        popup = tk.Toplevel(self.root)
        popup.title(self.i18n("col_mods"))
        popup.geometry(f"250x200+{x}+{y}")
        popup.resizable(False, False)
        popup.transient(self.root)

        frame = ttk.Frame(popup, padding=5)
        frame.pack(fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(frame, activestyle="dotbox", selectmode=tk.BROWSE)
        for mod_name in mods_list:
            listbox.insert(tk.END, mod_name)

        yscroll = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=yscroll.set)

        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(popup, text=self.i18n("close"), command=popup.destroy).pack(pady=4)


import os, sys, threading
import pystray
from PIL import Image

# ────────────────────────────── функция для создания иконки в трее ──────────────────────────────
def create_tray_icon(app):
    """Создаёт иконку в системном трее (минимизирует в трей, восстанавливает окно)."""

    # находим путь к icon.ico (работает и при .py, и при .exe)
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS   # временная папка PyInstaller
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    icon_path = os.path.join(base_path, "icon.ico")

    # если иконки нет — делаем заглушку
    try:
        image = Image.open(icon_path)
    except Exception:
        image = Image.new("RGB", (64, 64), "gray")

    # действия из меню трея
    def on_open(icon, item):
        app.root.deiconify()
        app.root.after(0, app.root.lift)

    def on_quit(icon, item):
        # полное завершение
        icon.stop()
        app.root.after(0, app.root.destroy)

    menu = pystray.Menu(
        pystray.MenuItem(app.i18n("show_window"), on_open),
        pystray.MenuItem(app.i18n("exit"), on_quit)
    )
    tray_icon = pystray.Icon("ck3logparser", image, "CK3 Log Analyzer", menu)
    app.tray_icon = tray_icon
    threading.Thread(target=tray_icon.run, daemon=True).start()
    print(app.i18n("tray_created"))

# ────────────────────────────── основной запуск Tkinter ──────────────────────────────
if __name__ == "__main__":
    import sys, os, threading, pystray
    from PIL import Image

    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    icon_file = os.path.join(application_path, "icon.ico")

    root = tk.Tk()
    app = CK3LogParser(root)

    # установить иконку окна
    if os.path.exists(icon_file):
        try:
            root.iconbitmap(icon_file)
        except Exception as e:
            print(app.i18n("icon_load_error").format(err=e))

    # создать иконку в системном трее
    create_tray_icon(app)

    # корректное завершение
    def on_exit():
        if hasattr(app, "tray_icon"):
            try:
                app.tray_icon.stop()
            except Exception:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_exit)
    root.mainloop()
