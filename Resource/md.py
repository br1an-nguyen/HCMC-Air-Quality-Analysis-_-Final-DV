from markitdown import MarkItDown

md = MarkItDown(enable_plugins=False) # Set to True to enable plugins
result = md.convert("Principles of data visualization (1).pdf")
print(result.text_content)