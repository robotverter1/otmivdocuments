import flet as ft
import json
import os
from datetime import datetime
from threading import Timer
from pathlib import Path

class TextEditorApp:
    def __init__(self):
        # Состояние приложения
        self.current_file_path = None
        self.is_modified = False
        self.editor_content = ""
        self.autosave_enabled = True
        self.autosave_interval = 30  # секунды
        self.autosave_timer = None
        self.config_file = "editor_config.json"
        self.autosave_file = "autosave.txt"
        
        # UI элементы (будут инициализированы в build)
        self.text_field = None
        self.file_list = None
        self.page = None
        
    def load_config(self):
        """Загрузка настроек из файла конфигурации"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.autosave_enabled = config.get('autosave_enabled', True)
                    self.autosave_interval = config.get('autosave_interval', 30)
                    # Валидация интервала (от 10 до 300 секунд)
                    self.autosave_interval = max(10, min(300, self.autosave_interval))
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
    
    def save_config(self):
        """Сохранение настроек в файл конфигурации"""
        try:
            config = {
                'autosave_enabled': self.autosave_enabled,
                'autosave_interval': self.autosave_interval
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    def start_autosave_timer(self):
        """Запуск таймера автосохранения"""
        if self.autosave_timer:
            self.autosave_timer.cancel()
        
        if self.autosave_enabled:
            self.autosave_timer = Timer(self.autosave_interval, self.perform_autosave)
            self.autosave_timer.daemon = True
            self.autosave_timer.start()
    
    def stop_autosave_timer(self):
        """Остановка таймера автосохранения"""
        if self.autosave_timer:
            self.autosave_timer.cancel()
            self.autosave_timer = None
    
    def perform_autosave(self):
        """Выполнение автосохранения"""
        if self.is_modified and self.text_field:
            try:
                with open(self.autosave_file, 'w', encoding='utf-8') as f:
                    f.write(self.text_field.value or "")
                print(f"Автосохранение выполнено: {datetime.now()}")
            except Exception as e:
                print(f"Ошибка автосохранения: {e}")
        
        # Перезапуск таймера
        self.start_autosave_timer()
    
    def cleanup_autosave(self):
        """Очистка файла автосохранения"""
        try:
            if os.path.exists(self.autosave_file):
                os.remove(self.autosave_file)
                print("Файл автосохранения удален")
        except Exception as e:
            print(f"Ошибка удаления файла автосохранения: {e}")
    
    def check_unsaved_changes(self, action_callback):
        """Проверка несохраненных изменений перед действием"""
        if self.is_modified:
            def handle_dialog_result(e):
                dialog.open = False
                self.page.update()
                
                if e.control.text == "Сохранить":
                    self.save_file(None)
                    action_callback()
                elif e.control.text == "Не сохранять":
                    action_callback()
                # Если "Отмена" - ничего не делаем
            
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Несохраненные изменения"),
                content=ft.Text("У вас есть несохраненные изменения. Сохранить их?"),
                actions=[
                    ft.TextButton("Сохранить", on_click=handle_dialog_result),
                    ft.TextButton("Не сохранять", on_click=handle_dialog_result),
                    ft.TextButton("Отмена", on_click=handle_dialog_result),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
        else:
            action_callback()
    
    def open_file_dialog(self, e):
        """Открытие диалога выбора файла"""
        def handle_file_picker_result(e: ft.FilePickerResultEvent):
            if e.files:
                file_path = e.files[0].path
                self.load_file_content(file_path)
        
        file_picker = ft.FilePicker(on_result=handle_file_picker_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        # Проверка несохраненных изменений перед открытием
        self.check_unsaved_changes(lambda: file_picker.pick_files(
            allowed_extensions=["txt", "md", "json", "py"],
            dialog_title="Открыть файл"
        ))
    
    def load_file_content(self, file_path):
        """Загрузка содержимого файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.text_field.value = content
                self.current_file_path = file_path
                self.is_modified = False
                self.editor_content = content
                self.page.title = f"Text Editor - {os.path.basename(file_path)}"
                self.page.update()
                print(f"Файл открыт: {file_path}")
        except Exception as e:
            self.show_error_dialog(f"Ошибка открытия файла: {e}")
    
    def save_file(self, e):
        """Сохранение файла"""
        if self.current_file_path:
            self.save_to_path(self.current_file_path)
        else:
            self.save_file_as(e)
    
    def save_file_as(self, e):
        """Сохранение файла как..."""
        def handle_save_result(e: ft.FilePickerResultEvent):
            if e.path:
                self.save_to_path(e.path)
        
        file_picker = ft.FilePicker(on_result=handle_save_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        file_picker.save_file(
            dialog_title="Сохранить файл как",
            file_name="document.txt",
            allowed_extensions=["txt", "md", "json", "py"]
        )
    
    def save_to_path(self, file_path):
        """Сохранение в указанный путь"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.text_field.value or "")
            
            self.current_file_path = file_path
            self.is_modified = False
            self.editor_content = self.text_field.value
            self.page.title = f"Text Editor - {os.path.basename(file_path)}"
            self.cleanup_autosave()  # Удаляем autosave после успешного сохранения
            self.page.update()
            print(f"Файл сохранен: {file_path}")
        except Exception as e:
            self.show_error_dialog(f"Ошибка сохранения файла: {e}")
    
    def on_text_change(self, e):
        """Обработчик изменения текста"""
        if self.text_field.value != self.editor_content:
            self.is_modified = True
            if not self.page.title.endswith("*"):
                self.page.title += " *"
                self.page.update()
    
    def show_error_dialog(self, message):
        """Показ диалога ошибки"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ошибка"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_dialog(self):
        """Закрытие диалога"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def show_settings_dialog(self, e):
        """Показ диалога настроек"""
        autosave_switch = ft.Switch(
            value=self.autosave_enabled,
            label="Включить автосохранение"
        )
        
        interval_field = ft.TextField(
            label="Интервал автосохранения (сек)",
            value=str(self.autosave_interval),
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="От 10 до 300 секунд"
        )
        
        def save_settings(e):
            try:
                new_interval = int(interval_field.value)
                # Валидация интервала
                if new_interval < 10 or new_interval > 300:
                    self.show_error_dialog("Интервал должен быть от 10 до 300 секунд")
                    return
                
                self.autosave_enabled = autosave_switch.value
                self.autosave_interval = new_interval
                self.save_config()
                
                # Перезапуск таймера с новыми настройками
                self.stop_autosave_timer()
                self.start_autosave_timer()
                
                self.close_dialog()
                print("Настройки сохранены")
            except ValueError:
                self.show_error_dialog("Введите корректное число")
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Настройки"),
            content=ft.Column([
                autosave_switch,
                interval_field,
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Сохранить", on_click=save_settings),
                ft.TextButton("Отмена", on_click=lambda e: self.close_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def on_window_close(self, e):
        """Обработчик закрытия окна"""
        def perform_close():
            self.stop_autosave_timer()
            self.save_config()
            if not self.is_modified:
                self.cleanup_autosave()
            self.page.window_destroy()
        
        if self.is_modified:
            e.control.page.window_prevent_close = True
            self.check_unsaved_changes(perform_close)
        else:
            perform_close()
    
    def build(self, page: ft.Page):
        """Построение интерфейса"""
        self.page = page
        page.title = "Text Editor"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.window_prevent_close = True
        page.on_window_event = lambda e: self.on_window_close(e) if e.data == "close" else None
        
        # Загрузка конфигурации
        self.load_config()
        
        # Текстовое поле редактора
        self.text_field = ft.TextField(
            multiline=True,
            min_lines=20,
            max_lines=None,
            expand=True,
            border=ft.InputBorder.NONE,
            text_size=16,
            on_change=self.on_text_change,
        )
        
        # Меню файлов
        menu_bar = ft.Row([
            ft.TextButton("Открыть", icon=ft.Icons.FOLDER_OPEN, on_click=self.open_file_dialog),
            ft.TextButton("Сохранить", icon=ft.Icons.SAVE, on_click=self.save_file),
            ft.TextButton("Сохранить как", icon=ft.Icons.SAVE_AS, on_click=self.save_file_as),
            ft.TextButton("Настройки", icon=ft.Icons.SETTINGS, on_click=self.show_settings_dialog),
        ], spacing=5)
        
        # Основной layout
        page.add(
            ft.Column([
                menu_bar,
                ft.Divider(height=1),
                self.text_field,
            ], expand=True, spacing=0)
        )
        
        # Запуск автосохранения
        self.start_autosave_timer()

def main(page: ft.Page):
    app = TextEditorApp()
    app.build(page)

if __name__ == "__main__":
    ft.app(target=main)