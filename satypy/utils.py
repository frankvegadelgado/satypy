# Created on 04/29/2026
# Author: Frank Vega

import os

def get_file_names(directory):
  """
  Gets a list of all file names within a specified directory.

  Args:
    directory: The path to the directory.

  Returns:
    A list of file names within the directory.
  """
  try:
    return [f for f in os.listdir(directory) if not os.path.isdir(os.path.join(directory, f))]
  except FileNotFoundError:
    print(f"Directory '{directory}' not found.")
    return []

def get_extension_without_dot(filepath):
    """
    Gets the file extension without the dot from an absolute path.

    Args:
        filepath: The absolute path to the file.

    Returns:
        The file extension without the dot, or None if no extension is found.
    """

    filename = os.path.basename(filepath)
    _, ext = os.path.splitext(filename)
    return ext[1:] if ext else None

def convert_to_absolute_value_set(list_of_lists):
  """
  Converts a list of lists of integers (positive and negative) 
  to a set of their absolute values.

  Args:
    list_of_lists: A list of lists of integers.

  Returns:
    A set containing the absolute values of all integers 
    in the input lists.
  """
  absolute_values = set()
  for sublist in list_of_lists:
    for num in sublist:
      absolute_values.add(abs(num))
  return absolute_values

def println(msg, logger):
    logger.info(msg)

def output(msg, logger, use_logs):
    if use_logs:
        println(msg, logger)
    else:
        print(msg)
              
def evaluate_partial_assignment(truth_assignment, cnf_formula):
    simplified_formula = []
    for clause in cnf_formula:
        new_clause = []
        clause_satisfied = False
        for literal in clause:
            var = abs(literal)
            if (var in truth_assignment) or (-var in truth_assignment):
                if literal in truth_assignment:
                    clause_satisfied = True
                    break
                # else, the literal is false, so don't add it to new_clause
            else:
                new_clause.append(literal)
        if not clause_satisfied and new_clause:
            simplified_formula.append(new_clause)
        elif not clause_satisfied and not new_clause:
           return None    
    return [] if not simplified_formula else simplified_formula

def is_vertex_cover(graph, vertex_cover):
    """
    Verifies if a given set of vertices is a valid vertex cover for the graph.

    Args:
        graph (nx.Graph): The input graph.
        vertex_cover (set): A set of vertices to check.

    Returns:
        bool: True if the set is a valid vertex cover, False otherwise.
    """
    for u, v in graph.edges():
        if u not in vertex_cover and v not in vertex_cover:
            return False
    return True

def is_independent_set(G, subset):
    """
    Checks if a subset of nodes forms an independent set in the graph.
    """
    for u in subset:
        for v in subset:
            if u != v and G.has_edge(u, v):
                return False
    return True

def format_solution(answer, max_length=4096):
    lines = []
    # First line: status
    lines.append("s SATISFIABLE")
    
    if not answer:
        return '\n'.join(lines)
    
    # Start building the value line
    value_prefix = "v "
    current_line = value_prefix
    for num in map(str, answer):
        # Check if adding the next number would exceed the max line length
        if len(current_line) + len(num) + 1 > max_length:  # +1 for space
            lines.append(current_line)
            current_line = value_prefix
        if current_line != value_prefix:
            current_line += ' '
        current_line += num
    
    # Add the last value line if it's not empty
    if current_line != value_prefix:
        lines.append(current_line)
    
    return '\n'.join(lines)