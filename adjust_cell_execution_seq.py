import nbformat

# Load the notebook
notebook_path = "evaluate_localization_strategies.ipynb"
with open(notebook_path, "r") as f:
    nb = nbformat.read(f, as_version=4)

# Adjust the execution count sequentially
execution_count = 1
for cell in nb.cells:
    if cell.cell_type == "code":
        cell.execution_count = execution_count
        execution_count += 1

# Save the modified notebook
with open("evaluate_localization_strategies_sequential.ipynb", "w") as f:
    nbformat.write(nb, f)

print("Cell execution counts updated sequentially and saved as 'evaluate_localization_strategies_sequential.ipynb'")