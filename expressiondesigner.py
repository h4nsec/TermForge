import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import requests
import json
import sv_ttk  # Importing the sv_ttk library

left_insert = "272741003 | Laterality (attribute) | = 7771000 | Left (qualifier value) |"
right_insert = "272741003 | Laterality (attribute) | = 24028007 | Right (qualifier value) |"
bilateral_insert = "272741003 | Laterality (attribute) | = 51440002 | Right and left (qualifier value) |"
procedure_insert = "405813007 | Procedure site - Direct (attribute) |"
method_insert = "260686004 | Method (attribute) |"
contrast_insert = "424361007|Using substance (attribute)| = 385420005|Contrast media (substance)|"

class TSVEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("TSV Editor")
        self.root.geometry("1200x600")

        # Apply the dark theme
        sv_ttk.set_theme("dark")

        self.create_widgets()

    def create_widgets(self):
        # Configure grid layout for the root window
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Frame for the Table
        self.frame_table = ttk.Frame(self.root)
        self.frame_table.grid(row=0, column=0, sticky="nsew")

        # Frame for the Cell Editor
        self.frame_editor = ttk.Frame(self.root, width=300)
        self.frame_editor.grid(row=0, column=1, sticky="ns")
        self.frame_editor.grid_propagate(False)  # Prevent frame from resizing

        # Treeview for displaying the TSV file
        self.tree = ttk.Treeview(self.frame_table, show='headings')
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        self.scroll_x = ttk.Scrollbar(self.frame_table, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.scroll_y = ttk.Scrollbar(self.frame_table, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
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
        self.lbl_cell = ttk.Label(self.frame_editor, text="Selected Cell")
        self.lbl_cell.pack(pady=5)

        self.txt_cell = tk.Text(self.frame_editor, height=10, wrap=tk.WORD)  # Adjusted height
        self.txt_cell.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        # Frame for Update and Validate Buttons
        self.frame_buttons = ttk.Frame(self.frame_editor)
        self.frame_buttons.pack(pady=5)

        self.btn_update = ttk.Button(self.frame_buttons, text="Update Cell", command=self.update_cell)
        self.btn_update.pack(side=tk.LEFT, padx=5)

        self.btn_validate = ttk.Button(self.frame_buttons, text="Validate Code", command=self.validate_code)
        self.btn_validate.pack(side=tk.LEFT, padx=5)

        # Frame for Add Buttons
        self.frame_add_buttons = ttk.Frame(self.frame_editor)
        self.frame_add_buttons.pack(pady=5)
        
        self.btn_open_options = ttk.Button(self.frame_buttons, text="Quick Add", command=self.open_options)
        self.btn_open_options.pack(side=tk.LEFT, padx=5)
        
        self.response_frame = ttk.Frame(self.frame_table)
        self.response_frame.pack(fill=tk.BOTH, expand=True)
        
        self.response_text = scrolledtext.ScrolledText(self.response_frame, height=10, wrap=tk.WORD)
        self.response_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        self.df = None

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
        self.txt_cell.delete(1.0, tk.END)
        self.txt_cell.insert(tk.END, cell_value[self.selected_col])

    def update_cell(self):
        new_value = self.txt_cell.get(1.0, tk.END).strip()
        if self.df is not None and hasattr(self, 'selected_row') and hasattr(self, 'selected_col'):
            self.df.iat[self.selected_row, self.selected_col] = new_value
            self.update_treeview()
        else:
            messagebox.showwarning("Warning", "No cell selected")

    def validate_code(self):
        code = self.txt_cell.get(1.0, tk.END).strip()
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
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(tk.END, pretty_response)
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
        
        for display_text, value in options:
            button = ttk.Button(self.popup, text=display_text, command=lambda val=value: self.select_option(val), width=button_width)
            button.pack(padx=10, pady=5)
        

    def select_option(self, option):
        cursor_index = self.txt_cell.index(tk.INSERT)
        self.txt_cell.insert(cursor_index, option)
        self.popup.destroy()


def main():
    root = tk.Tk()
    TSVEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
