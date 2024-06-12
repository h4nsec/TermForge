import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import pandas as pd
import requests
import json
import sv_ttk  # Importing the sv_ttk library
import re
from urllib.parse import quote
import threading

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
    text_widget.tag_config('focus_concept', foreground='pink', font=('Helvetica', 10, 'bold'))
    text_widget.tag_config('refinement', foreground='orange', font=('Helvetica', 10, 'italic'))

class TSVEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("TermForge")
        self.root.geometry("1200x800")

        # Apply the dark theme
        sv_ttk.set_theme("dark")

        # Define the search terms here
        self.search_terms = [
            ("ECL", "ECL"),
            ("Clinical Findings", "<< 404684003 | Clinical finding (finding) |"), 
            ("Procedures", "<< 71388002 | Procedure (procedure) |"), 
            ("Body Structures", "<< 123037004 | Body structure (body structure) |")
        ]

        self.hidden_columns = []

        self.create_widgets()
        self.create_context_menu()
        self.create_popup_menus()

    def create_widgets(self):
        # Create a PanedWindow to hold the resizable frames
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Frame for the Table
        self.frame_table = ttk.Frame(self.paned_window, padding=(10, 5))
        self.paned_window.add(self.frame_table, weight=3)

        # Frame for the Cell Editor
        self.frame_editor = ttk.Frame(self.paned_window, width=300, height=400, padding=(10, 5))
        self.paned_window.add(self.frame_editor, weight=1)

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

        # Export Button
        self.btn_export = ttk.Button(self.frame_load_save, text="Export", command=self.show_export_menu)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        # Column Operations Button
        self.btn_column_ops = ttk.Button(self.frame_load_save, text="Column Operations", command=self.show_column_menu)
        self.btn_column_ops.pack(side=tk.LEFT, padx=5)

        # Cell Editor Widgets
        self.lbl_cell = ttk.Label(self.frame_editor, text="Selected Cell", font=("Helvetica", 12, "bold"))
        self.lbl_cell.pack(pady=5)

        # Search Frame and Widgets
        self.frame_search = ttk.Frame(self.frame_editor)
        self.frame_search.pack(pady=5)

        self.search_entry = ttk.Entry(self.frame_search, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        self.btn_search = ttk.Button(self.frame_search, text="Search", command=self.search_text)
        self.btn_search.pack(side=tk.LEFT, padx=5)

        self.replace_entry = ttk.Entry(self.frame_search, width=20)
        self.replace_entry.pack(side=tk.LEFT, padx=5)
        
        self.btn_replace = ttk.Button(self.frame_search, text="Replace", command=self.replace_text)
        self.btn_replace.pack(side=tk.LEFT, padx=5)

        self.txt_cell = scrolledtext.ScrolledText(self.frame_editor, height=10, wrap=tk.WORD, font=("Helvetica", 10), undo=True)
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

        # Create a frame for validation response and SNOMED search
        self.frame_validation_search = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.frame_validation_search.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Validation Response Frame
        self.response_frame = ttk.Frame(self.frame_validation_search, padding=(10, 5))
        self.frame_validation_search.add(self.response_frame, weight=1)

        self.response_text = scrolledtext.ScrolledText(self.response_frame, height=10, wrap=tk.WORD, font=("Helvetica", 10))
        self.response_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        # SNOMED-CT Search Frame
        self.frame_snomed_search = ttk.Frame(self.frame_validation_search, padding=(10, 5))
        self.frame_validation_search.add(self.frame_snomed_search, weight=1)

        search_term_frame = ttk.Frame(self.frame_snomed_search)
        search_term_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_term_frame, text="Search Term:").pack(side=tk.LEFT, padx=5)
        self.snomed_search_entry = ttk.Entry(search_term_frame, width=30)
        self.snomed_search_entry.pack(side=tk.LEFT, padx=5)

        self.search_term_var = tk.StringVar()
        self.search_term_var.set(self.search_terms[0][0])
        self.dropdown_search = ttk.OptionMenu(search_term_frame, self.search_term_var, *[term[0] for term in self.search_terms])
        self.dropdown_search.pack(side=tk.LEFT, padx=5)

        self.btn_snomed_search = ttk.Button(search_term_frame, text="Search", command=self.start_snomed_search_thread)
        self.btn_snomed_search.pack(side=tk.LEFT, padx=5)

        self.snomed_results_listbox = tk.Listbox(self.frame_snomed_search, width=150, height=20)
        self.snomed_results_listbox.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        self.snomed_results_listbox.bind('<Double-1>', self.insert_snomed_concept)

        self.status_bar = ttk.Label(self.root, text="Rows: 0 | Current Cell: None", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.df = None

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Cut", command=self.cut_text)
        self.context_menu.add_command(label="Copy", command=self.copy_text)
        self.context_menu.add_command(label="Paste", command=self.paste_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Highlight Syntax", command=self.highlight_selected_text)

    def create_popup_menus(self):
        # Export Menu
        self.export_menu = tk.Menu(self.root, tearoff=0)
        self.export_menu.add_command(label="Export CSV", command=lambda: self.export_data('csv'))
        self.export_menu.add_command(label="Export Excel", command=lambda: self.export_data('xlsx'))
        self.export_menu.add_command(label="Export JSON", command=lambda: self.export_data('json'))
        self.export_menu.add_command(label="Export TXT", command=lambda: self.export_data('txt'))

        # Column Operations Menu
        self.column_menu = tk.Menu(self.root, tearoff=0)
        self.column_menu.add_command(label="Hide Column", command=self.hide_column)
        self.column_menu.add_command(label="Show Columns", command=self.show_columns)
        self.column_menu.add_command(label="Add Column", command=self.add_column)
        self.column_menu.add_command(label="Delete Column", command=self.delete_column)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def show_export_menu(self):
        try:
            self.export_menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            self.export_menu.grab_release()

    def show_column_menu(self):
        try:
            self.column_menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            self.column_menu.grab_release()

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
            try:
                self.df = pd.read_csv(file_path, delimiter='\t')
                self.update_treeview()
                self.update_status_bar()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")

    def save_tsv(self):
        if self.df is not None:
            file_path = filedialog.asksaveasfilename(defaultextension=".tsv", filetypes=[("TSV files", "*.tsv")])
            if file_path:
                try:
                    self.df.to_csv(file_path, sep='\t', index=False)
                    messagebox.showinfo("Success", "File saved successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file: {e}")
        else:
            messagebox.showwarning("Warning", "No data to save")

    def update_treeview(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = [col for col in self.df.columns if col not in self.hidden_columns]
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview_column(_col, False))
            self.tree.column(col, width=100)

        for index, row in self.df.iterrows():
            values = [row[col] for col in self.tree["columns"]]
            self.tree.insert("", "end", values=values)

        self.tree.bind("<ButtonRelease-1>", self.on_cell_select)

    def update_status_bar(self):
        num_rows = len(self.df) if self.df is not None else 0
        current_cell = f"Row: {self.selected_row}, Column: {self.selected_col}" if hasattr(self, 'selected_row') and hasattr(self, 'selected_col') else "None"
        self.status_bar.config(text=f"Rows: {num_rows} | Current Cell: {current_cell}")

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
        self.update_status_bar()

    def update_cell(self):
        new_value = self.txt_cell.get("1.0", "end").strip()
        if self.df is not None and hasattr(self, 'selected_row') and hasattr(self, 'selected_col'):
            self.df.iat[self.selected_row, self.selected_col] = new_value
            self.update_treeview()
            self.update_status_bar()
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
            self.update_status_bar()
        else:
            messagebox.showwarning("Warning", "No column selected")

    def hide_column(self):
        if self.df is not None and hasattr(self, 'selected_col'):
            col_name = self.df.columns[self.selected_col]
            if col_name not in self.hidden_columns:
                self.hidden_columns.append(col_name)
                self.update_treeview()
        else:
            messagebox.showwarning("Warning", "No column selected")

    def show_columns(self):
        self.hidden_columns = []
        self.update_treeview()

    def add_column(self):
        if self.df is not None:
            col_name = simpledialog.askstring("Add Column", "Enter column name:")
            if col_name:
                self.df[col_name] = ""
                self.update_treeview()
        else:
            messagebox.showwarning("Warning", "No data to add column to")

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

    def search_text(self):
        search_term = self.search_entry.get()
        self.txt_cell.tag_remove('search', '1.0', tk.END)
        
        if search_term:
            start_pos = '1.0'
            while True:
                start_pos = self.txt_cell.search(search_term, start_pos, stopindex=tk.END)
                if not start_pos:
                    break
                end_pos = f"{start_pos}+{len(search_term)}c"
                self.txt_cell.tag_add('search', start_pos, end_pos)
                start_pos = end_pos

            self.txt_cell.tag_config('search', background='yellow', foreground='black')

    def replace_text(self):
        search_term = self.search_entry.get()
        replace_term = self.replace_entry.get()
        content = self.txt_cell.get("1.0", tk.END)
        new_content = content.replace(search_term, replace_term)
        self.txt_cell.delete("1.0", tk.END)
        self.txt_cell.insert("1.0", new_content)

    def sort_treeview_column(self, col, reverse):
        if self.df is not None:
            self.df.sort_values(by=col, ascending=not reverse, inplace=True)
            self.update_treeview()
            self.tree.heading(col, command=lambda: self.sort_treeview_column(col, not reverse))

    def export_data(self, export_format):
        if self.df is not None:
            file_path = filedialog.asksaveasfilename(defaultextension=f".{export_format}", filetypes=[(f"{export_format.upper()} files", f"*.{export_format}")])
            if file_path:
                try:
                    if export_format == 'csv':
                        self.df.to_csv(file_path, index=False)
                    elif export_format == 'xlsx':
                        self.df.to_excel(file_path, index=False)
                    elif export_format == 'json':
                        self.df.to_json(file_path, orient='records', lines=True)
                    elif export_format == 'txt':
                        self.df.to_csv(file_path, sep="\t", index=False)
                    messagebox.showinfo("Success", f"File exported successfully as {export_format.upper()}!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export file: {e}")
        else:
            messagebox.showwarning("Warning", "No data to export")

    def open_settings(self):
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        
        ttk.Label(self.settings_window, text="Font Size").grid(row=0, column=0, padx=10, pady=10)
        self.font_size_var = tk.StringVar(value="10")
        ttk.Entry(self.settings_window, textvariable=self.font_size_var).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(self.settings_window, text="Theme").grid(row=1, column=0, padx=10, pady=10)
        self.theme_var = tk.StringVar(value="dark")
        ttk.Combobox(self.settings_window, textvariable=self.theme_var, values=["light", "dark"]).grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Button(self.settings_window, text="Apply", command=self.apply_settings).grid(row=2, column=0, columnspan=2, pady=10)

    def apply_settings(self):
        font_size = self.font_size_var.get()
        theme = self.theme_var.get()
        
        self.txt_cell.config(font=("Helvetica", int(font_size)))
        sv_ttk.set_theme(theme)
        self.settings_window.destroy()

    def start_snomed_search_thread(self):
        threading.Thread(target=self.search_snomed).start()

    def search_snomed(self):
        search_term = self.snomed_search_entry.get()
        selected_search_term = self.search_term_var.get()
        ecl = next((term[1] for term in self.search_terms if term[0] == selected_search_term), None)
        if not search_term or not ecl:
            messagebox.showwarning("Warning", "Please enter a search term and select a category")
            return
        
        encoded_search_term = quote(search_term)
        url = f"https://snowstorm.snomedtools.org/snowstorm/snomed-ct/MAIN/concepts?activeFilter=true&term={encoded_search_term}&ecl={quote(ecl)}&includeLeafFlag=false&form=inferred&offset=0&limit=50"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            self.display_snomed_results(response_json)
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Error fetching SNOMED-CT concepts: {str(e)}")

    def display_snomed_results(self, results):
        self.snomed_results_listbox.delete(0, tk.END)
        for item in results.get('items', []):
            concept_id = item.get('conceptId')
            term = item.get('fsn', {}).get('term')
            if concept_id and term:
                concept = f"{concept_id} | {term} |"
                self.snomed_results_listbox.insert(tk.END, concept)

    def insert_snomed_concept(self, event):
        selected_concept = self.snomed_results_listbox.get(self.snomed_results_listbox.curselection())
        cursor_index = self.txt_cell.index(tk.INSERT)
        self.txt_cell.insert(cursor_index, selected_concept)

def main():
    root = tk.Tk()
    root.iconbitmap("img/termforge.ico")
    TSVEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
