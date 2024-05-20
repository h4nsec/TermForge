import re

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
      start_idx = str(start)
      end_idx = str(end)
      text_widget.tag_add(tag, start_idx, end_idx)

  # Define tag styles
  text_widget.tag_config('definition_status', foreground='blue', font=('Helvetica', 10, 'bold'))
  text_widget.tag_config('concept_reference', foreground='green', font=('Helvetica', 10, 'italic'))
  text_widget.tag_config('attribute', foreground='red', font=('Helvetica', 10, 'underline'))
  text_widget.tag_config('focus_concept', foreground='purple', font=('Helvetica', 10, 'bold'))
  text_widget.tag_config('refinement', foreground='orange', font=('Helvetica', 10, 'italic'))