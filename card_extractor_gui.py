#!/usr/bin/env python3
"""
Magic Card Name Extractor - GUI Version
Drag-and-drop interface for extracting card names.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import pytesseract
from PIL import Image
import csv
import threading
from datetime import datetime

class CardExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Magic Card Name Extractor")
        self.root.geometry("650x600")

        title = tk.Label(root, text="Magic Card Extractor", font=("Arial", 16, "bold"))
        title.pack(pady=10)

        instructions = tk.Label(
            root,
            text="Select images to extract card names. Choose format and click 'Process'.",
            font=("Arial", 10)
        )
        instructions.pack()

        format_frame = tk.Frame(root)
        format_frame.pack(pady=10)

        tk.Label(format_frame, text="Output Format:", font=("Arial", 10)).pack(side="left", padx=5)

        self.format_var = tk.StringVar(value="txt")
        tk.Radiobutton(format_frame, text="TXT", variable=self.format_var, value="txt").pack(side="left", padx=5)
        tk.Radiobutton(format_frame, text="CSV", variable=self.format_var, value="csv").pack(side="left", padx=5)

        list_label = tk.Label(root, text="Selected Images:", font=("Arial", 10, "bold"))
        list_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.file_listbox = tk.Listbox(root, height=8)
        self.file_listbox.pack(padx=10, pady=5, fill="both", expand=True)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Add Images", command=self.add_files).pack(side="left", padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear_list).pack(side="left", padx=5)
        tk.Button(button_frame, text="Process", command=self.process_files).pack(side="left", padx=5)

        results_label = tk.Label(root, text="Results:", font=("Arial", 10, "bold"))
        results_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.results_text = scrolledtext.ScrolledText(root, height=8, width=60)
        self.results_text.pack(padx=10, pady=5, fill="both", expand=True)

        self.status_label = tk.Label(root, text="Ready", font=("Arial", 9))
        self.status_label.pack(pady=5)

        self.files = []

    def add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")]
        )
        self.files.extend(files)
        self.update_file_list()

    def clear_list(self):
        self.files = []
        self.update_file_list()
        self.results_text.delete("1.0", tk.END)

    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for f in self.files:
            self.file_listbox.insert(tk.END, Path(f).name)

    def process_files(self):
        if not self.files:
            messagebox.showwarning("No files", "Please select images first.")
            return

        thread = threading.Thread(target=self._process_thread)
        thread.start()

    def _process_thread(self):
        self.status_label.config(text="Processing...")
        self.root.update()

        format_type = self.format_var.get()
        all_cards = []
        results_text = ""

        for image_file in self.files:
            try:
                self.status_label.config(text=f"Processing: {Path(image_file).name}")
                self.root.update()

                img = Image.open(image_file)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                text = pytesseract.image_to_string(img)
                lines = text.strip().split('\n')

                skip_words = {'First', 'Legendary', 'Creature', 'Artifact', 'Enchantment', 'Sorcery', 'Instant'}
                for line in lines[:10]:
                    line = line.strip()
                    if line and line not in skip_words and len(line) > 2 and not line.isupper():
                        all_cards.append((line, Path(image_file).name))
                        results_text += f"{Path(image_file).name}: {line}\n"
                        break

            except Exception as e:
                results_text += f"{Path(image_file).name}: ERROR - {e}\n"

        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", results_text)
        self.status_label.config(text=f"Found {len(all_cards)} card names")

        output_filename = f"card_names.{format_type}"
        output_path = Path(output_filename)

        if format_type == 'csv':
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Card Name', 'Image Source', 'Extracted Date'])
                for card_name, image_source in all_cards:
                    writer.writerow([card_name, image_source, datetime.now().isoformat()])
        else:
            with open(output_path, 'w') as f:
                for card_name, _ in all_cards:
                    f.write(card_name + '\n')

        messagebox.showinfo("Success", f"Extracted {len(all_cards)} cards.\nSaved to: {output_path.absolute()}\nFormat: {format_type.upper()}")

if __name__ == '__main__':
    root = tk.Tk()
    app = CardExtractorGUI(root)
    root.mainloop()
