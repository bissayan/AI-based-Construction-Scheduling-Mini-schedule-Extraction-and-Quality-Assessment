import re
import os

def extract_task_and_duration(line):
    """Extract task name and duration from a line, handling various formats."""
    line = line.strip()
    if not line:
        return None, None

    # Regex patterns to match task and duration
    # Matches: "Task [X.Xh]", "Task (Duration: X.Xh)", "Task [Duration: Xh]", or similar
    patterns = [
        r'^(.*?)\s*\[(\d+\.\d+h)\]\s*$',  # e.g., "Task [112.0h]"
        r'^(.*?)\s*\(Duration:\s*(\d+\.\d+h)\)\s*(?:\(.+\))?$',  # e.g., "Task (Duration: 112.0h)"
        r'^(.*?)\s*\[Duration:\s*(\d+h)\]\s*(?:\(.+\))?$',  # e.g., "Task [Duration: 112h]"
        r'^(.*?)\s*Duration:\s*(\d+\.\d+h)\s*(?:\(.+\))?$',  # e.g., "Task Duration: 112.0h"
        r'^(.*?)\s*Duration:\s*(\d+h)\s*(?:\(.+\))?$',  # e.g., "Task Duration: 112h"
    ]

    for pattern in patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            task, duration = match.groups()
            # Normalize duration to remove decimal if not needed (e.g., 112.0h -> 112h)
            duration = duration.replace('.0h', 'h')
            return task.strip(), duration

    # Fallback: Split by spaces and look for duration
    parts = re.split(r'\s+', line)
    for part in parts:
        if re.match(r'\d+\.\d+h|\d+h', part, re.IGNORECASE):
            duration = part.replace('.0h', 'h')
            task = line.replace(part, '').strip('[]()').strip()
            # Clean up extra metadata like similarity scores
            task = re.sub(r'\(Similarity:.*?\)', '', task).strip()
            return task, duration

    print(f"Warning: Could not parse line: {line}")
    return None, None

def assign_parent_category(task):
    """Assign a parent category based on task name or prefix."""
    task = task.strip().lower()
    # General Milestones for initial or non-specific tasks
    if any(keyword in task for keyword in [
        "project work start", "site clearance", "boreholes", "preliminary cost",
        "ifc drawings", "building permit", "site surveying", "mobilization",
        "equipment yard", "security bonds", "insurances", "phase 02 accomplishment",
        "project finish", "commissioning", "training", "snaging", "handing over",
        "hand over", "o & m manuals", "project end", "down payment", "cleaning around"
    ]):
        return "General Milestones"
    # Sub-Contractor Prequalification
    elif any(keyword in task for keyword in [
        "submission of sub-contractor prequalification",
        "approval of sub-contractor prequalification"
    ]):
        return "Sub-Contractor Prequalification"
    # Material Management
    elif any(keyword in task for keyword in [
        "material submittals", "material approvals", "material purchase order"
    ]):
        return "Material Management"
    # Concrete-related tasks (drawings, pouring, etc.)
    elif any(keyword in task for keyword in [
        "drawings", "slab", "coulmns", "column", "foundation", "pouring", "shuttering",
        "rft formation", "rc ", "pc "
    ]):
        return "Concrete"
    # Finishing tasks
    elif any(keyword in task for keyword in [
        "plastering", "painting", "ceramic", "tiles", "sanitary", "insulation",
        "doors", "windows", "masonry", "handrail", "skirting", "stair"
    ]):
        return "Finishing"
    # Electrical and Mechanical
    elif any(keyword in task for keyword in [
        "electrical", "wiring", "conduits", "boxs", "hvac", "bms", "pas", "fas",
        "cctv", "smdb", "lighting", "earthing", "lightning", "elevator",
        "telephone", "intercom", "tv fixtures", "electric panels"
    ]):
        return "Electrical and Mechanical"
    # Fire Fighting Work
    elif any(keyword in task for keyword in [
        "fire fighting", "fire hose", "valves installation", "hydro test"
    ]):
        return "Fire Fighting Work"
    # As-built drawings
    elif "as built" in task:
        return "As built drawings"
    # Assign based on prefix (e.g., B01, S1, F2, etc.)
    prefix_match = re.match(r'^(b\d+|s\d+|f\d+|u\d+|ad|ac|gh|au|lb|mq|cf|ext|cdd)-', task)
    if prefix_match:
        return prefix_match.group(1).upper()
    # Default category
    return "Miscellaneous"

def process_file(input_filename, output_filename):
    """Process the input file and write to output in slab_RBE_all.txt format."""
    try:
        with open(input_filename, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()

        modified_lines = []
        for idx, line in enumerate(lines, 1):
            task, duration = extract_task_and_duration(line)
            if task and duration:
                parent = assign_parent_category(task)
                # Format line to match slab_RBE_all.txt
                formatted_line = f"{idx}. {task} [Duration: {duration}] (Parent: {parent})"
                modified_lines.append(formatted_line)
            else:
                print(f"Skipping line {idx}: {line.strip()}")

        # Write to output file
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            for line in modified_lines:
                outfile.write(line + '\n')

        print(f"File {input_filename} processed successfully. Output saved to {output_filename}")
        return True

    except FileNotFoundError:
        print(f"Error: Input file {input_filename} not found in the same directory as the script.")
        return False
    except Exception as e:
        print(f"Error processing file {input_filename}: {str(e)}")
        return False

def main():
    """Process both input files and generate corresponding output files."""
    input_files = ['level_similarity.txt', 'sequence_similarity.txt']
    output_files = ['level_similarity_converted.txt', 'sequence_similarity_converted.txt']

    for input_file, output_file in zip(input_files, output_files):
        if os.path.exists(input_file):
            process_file(input_file, output_file)
        else:
            print(f"Error: {input_file} not found in the same directory as the script.")

if __name__ == "__main__":
    main()