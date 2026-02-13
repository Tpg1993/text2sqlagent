import pypdf

reader = pypdf.PdfReader("data/docs/support.pdf")
full_text = ""
for page in reader.pages:
    full_text += page.extract_text() + "\n"

print(full_text)
