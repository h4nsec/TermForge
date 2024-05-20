import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import requests
import json
import sv_ttk  # Importing the sv_ttk library
import re

left_insert = "272741003 | Laterality (attribute) | = 7771000 | Left (qualifier value) |"
right_insert = "272741003 | Laterality (attribute) | = 24028007 | Right (qualifier value) |"
bilateral_insert = "272741003 | Laterality (attribute) | = 51440002 | Right and left (qualifier value) |"
procedure_insert = "405813007 | Procedure site - Direct (attribute) |"
method_insert = "260686004 | Method (attribute) |"
contrast_insert = "424361007|Using substance (attribute)| = 385420005|Contrast media (substance)|"

def highlight_snomed_expression(text_widget, expression):
    # Clear existing tags
    for tag in text_widget.tag_names():
        text_widget.tag_remove(tag, "1.0", "end")
    
    # Define regex patterns for different components
    patterns = {
        'definitionStatus': (r'(===|<<<)', 'definition_status'),
        'conceptReference': (r'(\d+ \|[^|]+\|)', 'concept_reference'),
        'attribute': (r'(\d+ \|[^|]+\| = \d+ \|[^|]+\|)', 'attribute'),
        'focusConcept': (r'(\d+ \|[^|]+\|(\s*\+\s*\d+ \|[^|]+\|)*)', 'focus_concept'),
        'refinement': (r': (\d+ \|[^|]+\| = \d+ \|[^|]+\|)', 'refinement')
    }

    # Apply tags to highlight the text
    for pattern, tag in patterns.values():
        for match in re.finditer(pattern, expression):
            start, end = match.span()
            start_idx = f"1.0 + {start} chars"
            end_idx = f"1.0 + {end} chars"
            text_widget.tag_add(tag, start_idx, end_idx)

    # Define tag styles
    text_widget.tag_config('definition_status', foreground='blue', font=('Helvetica', 10, 'bold'))
    text_widget.tag_config('concept_reference', foreground='green', font=('Helvetica', 10, 'italic'))
    text_widget.tag_config('attribute', foreground='red', font=('Helvetica', 10, 'underline'))
    text_widget.tag_config('focus_concept', foreground='purple', font=('Helvetica', 10, 'bold'))
    text_widget.tag_config('refinement', foreground='orange', font=('Helvetica', 10, 'italic'))

class TSVEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("TermForge")
        self.root.geometry("1200x600")

        # Apply the dark theme
        sv_ttk.set_theme("dark")

        self.create_widgets()
        self.create_context_menu()

    def create_widgets(self):
        # Configure grid layout for the root window
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        # Frame for the Table
        self.frame_table = ttk.Frame(self.root, padding=(10, 5))
        self.frame_table.grid(row=0, column=0, sticky="nsew")

        # Frame for the Cell Editor
        self.frame_editor = ttk.Frame(self.root, width=300, padding=(10, 5))
        self.frame_editor.grid(row=0, column=1, sticky="ns")
        self.frame_editor.grid_propagate(False)  # Prevent frame from resizing

        # Treeview for displaying the TSV file
        self.tree = ttk.Treeview(self.frame_table, show='headings')
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars for the Treeview
        self.scroll_x = ttk.Scrollbar(self.frame_table, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.scroll_y = ttk.Scrollbar(self.frame_table, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.scroll_x.grid(row=1, column=0, sticky="ew")
        self.scroll_y.grid(row=0, column=1, sticky="ns")

        # Set column and row configurations for frame_table to expand properly
        self.frame_table.grid_columnconfigure(0, weight=1)
        self.frame_table.grid_rowconfigure(0, weight=1)

        # Load and Save Buttons
        self.frame_load_save = ttk.Frame(self.frame_editor)
        self.frame_load_save.pack(pady=5)

        self.btn_load = ttk.Button(self.frame_load_save, text="Load TSV", command=self.load_tsv)
        self.btn_load.pack(side=tk.LEFT, padx=5)

        self.btn_save = ttk.Button(self.frame_load_save, text="Save TSV", command=self.save_tsv)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        # Button to delete a column
        self.btn_delete_col = ttk.Button(self.frame_load_save, text="Delete Column", command=self.delete_column)
        self.btn_delete_col.pack(side=tk.LEFT, padx=5)

        # Cell Editor Widgets
        self.lbl_cell = ttk.Label(self.frame_editor, text="Selected Cell", font=("Helvetica", 12, "bold"))
        self.lbl_cell.pack(pady=5)

        self.txt_cell = scrolledtext.ScrolledText(self.frame_editor, height=10, wrap=tk.WORD, font=("Helvetica", 10))
        self.txt_cell.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        # Bind right-click to show the context menu
        self.txt_cell.bind("<Button-3>", self.show_context_menu)

        # Frame for Update and Validate Buttons
        self.frame_buttons = ttk.Frame(self.frame_editor)
        self.frame_buttons.pack(pady=5)

        self.btn_update = ttk.Button(self.frame_buttons, text="Update Cell", command=self.update_cell)
        self.btn_update.pack(side=tk.LEFT, padx=5)

        self.btn_validate = ttk.Button(self.frame_buttons, text="Validate Code", command=self.validate_code)
        self.btn_validate.pack(side=tk.LEFT, padx=5)

        # Button to compare cells
        self.btn_compare = ttk.Button(self.frame_buttons, text="Compare Cell", command=self.compare_cell)
        self.btn_compare.pack(side=tk.LEFT, padx=5)

        # Frame for Add Buttons
        self.frame_add_buttons = ttk.Frame(self.frame_editor)
        self.frame_add_buttons.pack(pady=5)

        self.btn_open_options = ttk.Button(self.frame_buttons, text="Quick Add", command=self.open_options)
        self.btn_open_options.pack(side=tk.LEFT, padx=5)

        self.response_frame = ttk.Frame(self.root, padding=(10, 5))
        self.response_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.response_text = scrolledtext.ScrolledText(self.response_frame, height=10, wrap=tk.WORD, font=("Helvetica", 10))
        self.response_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        self.df = None

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Cut", command=self.cut_text)
        self.context_menu.add_command(label="Copy", command=self.copy_text)
        self.context_menu.add_command(label="Paste", command=self.paste_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Highlight Syntax", command=self.highlight_selected_text)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def cut_text(self):
        self.txt_cell.event_generate("<<Cut>>")

    def copy_text(self):
        self.txt_cell.event_generate("<<Copy>>")

    def paste_text(self):
        self.txt_cell.event_generate("<<Paste>>")

    def highlight_selected_text(self):
        text = self.txt_cell.get("1.0", "end").strip()
        highlight_snomed_expression(self.txt_cell, text)

    def load_tsv(self):
        file_path = filedialog.askopenfilename(filetypes=[("TSV files", "*.tsv")])
        if file_path:
            self.df = pd.read_csv(file_path, delimiter='\t')
            self.update_treeview()

    def save_tsv(self):
        if self.df is not None:
            file_path = filedialog.asksaveasfilename(defaultextension=".tsv", filetypes=[("TSV files", "*.tsv")])
            if file_path:
                self.df.to_csv(file_path, sep='\t', index=False)
                messagebox.showinfo("Success", "File saved successfully!")
        else:
            messagebox.showwarning("Warning", "No data to save")

    def update_treeview(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(self.df.columns)
        for col in self.df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        for index, row in self.df.iterrows():
            self.tree.insert("", "end", values=list(row))

        self.tree.bind("<ButtonRelease-1>", self.on_cell_select)

    def on_cell_select(self, event):
        selected_item = self.tree.selection()[0]
        cell_value = self.tree.item(selected_item, "values")
        col_index = self.tree.identify_column(event.x)[1:]
        row_index = self.tree.index(selected_item)
        self.selected_row = row_index
        self.selected_col = int(col_index) - 1
        self.txt_cell.delete("1.0", "end")
        self.txt_cell.insert("end", cell_value[self.selected_col])
        self.highlight_selected_text()  # Highlight the cell content

    def update_cell(self):
        new_value = self.txt_cell.get("1.0", "end").strip()
        if self.df is not None and hasattr(self, 'selected_row') and hasattr(self, 'selected_col'):
            self.df.iat[self.selected_row, self.selected_col] = new_value
            self.update_treeview()
        else:
            messagebox.showwarning("Warning", "No cell selected")

    def validate_code(self):
        code = self.txt_cell.get("1.0", "end").strip()
        if not code:
            messagebox.showwarning("Warning", "No code to validate")
            return

        url = "https://r4.ontoserver.csiro.au/fhir/CodeSystem/$validate-code"
        system = "http://snomed.info/sct"
        headers = {
            'Accept': 'application/fhir+json',
            'Content-Type': 'application/fhir+json'
        }
        params = {
            'url': system,
            'code': code,
            'system': system
        }

        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            pretty_response = json.dumps(response_json, indent=4)
            self.response_text.delete("1.0", "end")
            self.response_text.insert("end", pretty_response)
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Error making request: {str(e)}")

    def delete_column(self):
        if self.df is not None and hasattr(self, 'selected_col'):
            col_name = self.df.columns[self.selected_col]
            self.df.drop(columns=[col_name], inplace=True)
            self.update_treeview()
        else:
            messagebox.showwarning("Warning", "No column selected")

    def add_text(self, text):
        cursor_index = self.txt_cell.index(tk.INSERT)
        self.txt_cell.insert(cursor_index, text)

    def open_options(self):
        options = [
            ("Left Lateral", left_insert),
            ("Right Lateral", right_insert), 
            ("Bilateral", bilateral_insert),
            ("Procedure Site", procedure_insert),
            ("Method", method_insert),
            ("Contrast", contrast_insert)
        ]
        self.popup = tk.Toplevel(self.root)
        self.popup.title("Select Option")

        max_label_length = max(len(text) for text, _ in options)
        button_width = max_label_length + 2

        # Position the popup relative to the root window
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        self.popup.geometry(f"+{root_x + 100}+{root_y + 100}")

        for display_text, value in options:
            button = ttk.Button(self.popup, text=display_text, command=lambda val=value: self.select_option(val), width=button_width)
            button.pack(padx=10, pady=5)

    def select_option(self, option):
        cursor_index = self.txt_cell.index(tk.INSERT)
        self.txt_cell.insert(cursor_index, option)
        self.popup.destroy()

    def compare_cell(self):
        selected_item = self.tree.selection()[0]
        cell_value = self.tree.item(selected_item, "values")
        self.compare_popup(cell_value[self.selected_col])

    def compare_popup(self, cell_value):
        self.compare_window = tk.Toplevel(self.root)
        self.compare_window.title("Compare Cell")
        self.compare_text = scrolledtext.ScrolledText(self.compare_window, height=10, wrap=tk.WORD, font=("Helvetica", 10))
        self.compare_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        self.compare_text.insert("end", cell_value)

def main():
    root = tk.Tk()
    root.iconbitmap("img/termforge.ico")
    TSVEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
