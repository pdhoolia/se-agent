While fetching code files to attach during change suggestions, can we be more tolerant about the fully qualified package.

E.g., if the fully qualified package is x.y.z (or x/y/z), and the filename is z.<ext>, i.e., the last part of the fully qualified package happens to be same as the filename without extension, then we want to fetch the file at x/y/z.<ext>

However if the fully qualified package is x.y (or x/y) and the filename is z.<ext>, then also we want to fetch the file at x/y/z.<ext>