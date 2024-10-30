Title: Tool based code structure name generation

Description:
When generating package summary we ask the LLM to generate a semantic summary for the package based on semantic details of all the sub-packages and code files in the package. Apart from the semantic summary section, we also ask it to generate a code structures section with names of all the sub-packages, code files, functions, and classes there in.

Can we change the strategy here to ask the LLM to only generate the section on semantic summary for the package? Let's write a function that can recursively navigate all the code files in the package, and extract a comma separated list of all the sub-package, file, function, and class names there-in.