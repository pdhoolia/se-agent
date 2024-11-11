import nbformat
import sys

def renumber_execution_counts(notebook_path):
    # Load the notebook
    with open(notebook_path, "r") as f:
        nb = nbformat.read(f, as_version=4)

    # Adjust the execution count sequentially
    execution_count = 1
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.execution_count = execution_count
            execution_count += 1

    # Save the modified notebook with a new name
    output_path = notebook_path.replace(".ipynb", "_sequential.ipynb")
    with open(output_path, "w") as f:
        nbformat.write(nb, f)
    
    print(f"Cell execution counts updated sequentially and saved as '{output_path}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <notebook_path>")
    else:
        notebook_path = sys.argv[1]
        renumber_execution_counts(notebook_path)