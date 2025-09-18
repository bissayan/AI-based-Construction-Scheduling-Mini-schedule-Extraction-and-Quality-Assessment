# import os
# import jpype
# import glob
# import sys
# from py2neo import Graph, Node
# from sentence_transformers import SentenceTransformer
# import numpy as np

# # Configure basic logging for progress
# print = lambda *args, **kwargs: __import__('builtins').print(*args, **kwargs)  # Use print for progress

# # Log environment details (minimal)
# print(f"Python version: {sys.version}")
# print(f"JPype version: {jpype.__version__}")
# print(f"Working directory: {os.getcwd()}")
# print(f"MPXJ directory: {os.path.abspath('mpxj-14.2.0')}")

# # Configure Java environment for MPXJ
# jar_dir = os.path.abspath("mpxj-14.2.0")
# main_jar = os.path.join(jar_dir, "mpxj.jar")
# lib_jars = glob.glob(os.path.join(jar_dir, "lib", "*.jar"))
# if not os.path.exists(main_jar):
#     raise FileNotFoundError(f"MPXJ main JAR not found: {main_jar}")
# if not lib_jars:
#     raise FileNotFoundError(f"No JAR files found in {os.path.join(jar_dir, 'lib')}")

# classpath = os.pathsep.join([main_jar] + lib_jars)

# if not jpype.isJVMStarted():
#     try:
#         jpype.startJVM(*["-Xmx512m", "-Dfile.encoding=UTF-8"], classpath=classpath)
#         print("JVM started successfully with UTF-8 encoding")
#     except Exception as e:
#         raise Exception(f"Failed to start JVM: {str(e)}")

# UniversalProjectReader = jpype.JClass("org.mpxj.reader.UniversalProjectReader")
# reader = UniversalProjectReader()
# print("Java class UniversalProjectReader loaded successfully")

# # Load pre-trained embedding model
# embedding_model = SentenceTransformer('intfloat/e5-large')
# print("Loaded sentence transformer model: intfloat/e5-large")

# # Connect to Neo4j
# try:
#     graph = Graph("bolt://localhost:7687", auth=("neo4j", "1234567EH"))
#     print("Connected to Neo4j database")
# except Exception as e:
#     raise Exception(f"Failed to connect to Neo4j: {str(e)}")

# def safe_get(obj, method, default=None):
#     """Helper function to safely call Java object methods"""
#     try:
#         if obj and hasattr(obj, method):
#             result = getattr(obj, method)()
#             return result if result is not None else default
#         return default
#     except Exception:
#         return default

# def generate_embedding(text):
#     """Generate embedding for a given text using the sentence transformer"""
#     if not text or not isinstance(text, str):
#         print(f"Warning: Invalid or empty text for embedding, using zeros")
#         return np.zeros(embedding_model.get_sentence_embedding_dimension()).tolist()
#     embedding = embedding_model.encode(text, convert_to_numpy=True)
#     return embedding.tolist()

# def validate_file(file_path):
#     """Validate the existence and format of the input file"""
#     absolute_path = os.path.abspath(file_path)
#     if not os.path.exists(absolute_path):
#         raise FileNotFoundError(f"File not found: {absolute_path}")
    
#     file_ext = os.path.splitext(file_path)[1].lower()
#     supported_extensions = ['.xer', '.mpp', '.xml']
#     if file_ext not in supported_extensions:
#         raise ValueError(f"Unsupported file extension: {file_ext}. Supported: {supported_extensions}")
    
#     if file_ext == '.xer':
#         encodings = ['utf-8', 'latin-1', 'iso-8859-1']
#         valid_header = False
#         first_lines = None
#         for encoding in encodings:
#             try:
#                 with open(absolute_path, 'r', encoding=encoding) as f:
#                     first_lines = f.readlines()[:5]
#                     if any(line.startswith('%T') for line in first_lines):
#                         valid_header = True
#                         break
#             except Exception:
#                 continue
        
#         if not valid_header:
#             raise ValueError(f"Invalid .xer file structure: No %T headers found in {absolute_path}")
    
#     print(f"Validated file: {absolute_path} (extension: {file_ext})")
#     return file_ext

# def schedule2KG(file, graph, use_fallback_reader=False):
#     """Convert project schedule to knowledge graph with level-wise and sequence-wise embeddings"""
#     # Validate file
#     file_ext = validate_file(file)
#     print(f"Processing file: {file}")

#     # Clear existing graph
#     try:
#         graph.run("MATCH (n) DETACH DELETE n")
#         print("Cleared existing graph")
#     except Exception as e:
#         raise Exception(f"Failed to clear graph: {str(e)}")
    
#     # Read project file
#     try:
#         if use_fallback_reader and file_ext == '.xer':
#             print("Using PrimaveraXERFileReader for .xer file")
#             ProjectReader = jpype.JClass("org.mpxj.primavera.PrimaveraXERFileReader")
#             reader = ProjectReader()
#             reader.setCharset("UTF-8")
#         else:
#             print("Using UniversalProjectReader")
#             reader = UniversalProjectReader()
        
#         project = reader.read(file)
#         if not project:
#             raise ValueError("Failed to read project file: returned None")
#         print(f"Successfully read project file: {file}")
#     except Exception as e:
#         if file_ext == '.xer' and not use_fallback_reader:
#             print("Retrying with PrimaveraXERFileReader")
#             return schedule2KG(file, graph, use_fallback_reader=True)
#         raise ValueError(f"Unable to read project file: {str(e)}")
    
#     # Process tasks
#     tasks = safe_get(project, "getTasks", [])
#     if not tasks:
#         raise ValueError("No tasks found in project")
#     print(f"Found {len(tasks)} tasks in project")
    
#     task_count = 0
#     for task in tasks:
#         if not task:
#             continue
            
#         task_name = safe_get(task, "getName", "Unnamed Task")
#         task_uid = safe_get(task, "getUniqueID", "")
#         task_wbs = safe_get(task, "getWBS", "")
        
#         # Get parent info safely
#         parent_task = safe_get(task, "getParentTask")
#         parent_name = safe_get(parent_task, "getName", "") if parent_task else ""
        
#         # Common properties
#         props = {
#             "name": str(task_name),
#             "UID": str(task_uid) if task_uid else "Unknown",
#             "WBS": str(task_wbs) if task_wbs else "Unknown",
#             "Parent": str(parent_name)
#         }
        
#         # Handle dates safely
#         start_date = safe_get(task, "getStart")
#         finish_date = safe_get(task, "getFinish")
        
#         if start_date:
#             props["Start"] = str(start_date.toString()).split("T")[0]
#         if finish_date:
#             props["Finish"] = str(finish_date.toString()).split("T")[0]
        
#         # Create appropriate node type
#         if safe_get(task, "hasChildTasks", False):
#             node = Node("WBS", **props)
#         elif start_date is not None:
#             props.update({
#                 "Duration": str(safe_get(task, "getDuration", "")),
#                 "Total_Float": str(safe_get(task, "getTotalSlack", "")),
#                 "Critical_Path": str(safe_get(task, "getCritical", False))
#             })
#             node = Node("Task", **props)
#         else:
#             continue
            
#         graph.create(node)
#         task_count += 1
#         if task_count % 100 == 0:
#             print(f"Processed {task_count}/{len(tasks)} nodes")
    
#     # Create hierarchical relationships
#     for task in tasks:
#         if not task or not safe_get(task, "getSummary", False):
#             continue
            
#         task_uid = safe_get(task, "getUniqueID", "")
#         if not task_uid:
#             continue
            
#         children = safe_get(task, "getChildTasks", [])
#         for child in children:
#             if not child:
#                 continue
#             child_uid = safe_get(child, "getUniqueID", "")
#             if not child_uid:
#                 continue
                
#             label = "WBS" if safe_get(child, "getSummary", False) else "Task"
            
#             query = """
#                 MATCH (a:WBS {UID:$UID1})
#                 MATCH (b:%s {UID:$UID2})
#                 MERGE (a)-[:HAS]->(b)
#             """ % label
            
#             graph.run(query, UID1=str(task_uid), UID2=str(child_uid))
    
#     # Create successor relationships
#     for task in tasks:
#         if not task:
#             continue
            
#         task_uid = safe_get(task, "getUniqueID", "")
#         if not task_uid:
#             continue
            
#         successors = safe_get(task, "getSuccessors", [])
#         for relation in successors:
#             if not relation:
#                 continue
#             target_id = safe_get(relation, "getTarget")
#             if not target_id:
#                 continue
#             target_uid = safe_get(target_id, "getUniqueID")
            
#             rel_type = safe_get(relation, "getType", "Unknown")
#             lag = safe_get(relation, "getLag", "0")
            
#             graph.run("""
#                 MATCH (a:Task {UID:$UID1})
#                 MATCH (b:Task {UID:$UID2})
#                 MERGE (a)-[:SUCCESSOR {Relationship_Type:$Relationship, Lag:$Lag}]->(b)
#             """,
#             UID1=str(task_uid),
#             UID2=str(target_uid) if target_uid else "Unknown",
#             Lag=str(lag),
#             Relationship=str(rel_type))
    
#     # Calculate and store level-wise paths and embeddings
#     first_node = graph.run("MATCH (w:WBS {Parent: ''}) RETURN w.UID LIMIT 1").evaluate()
#     if not first_node:
#         first_node = graph.run("MATCH (w:WBS) RETURN w.UID LIMIT 1").evaluate()
#         print("Warning: No WBS node with empty Parent found; using first WBS node")
    
#     if first_node:
#         task_count = 0
#         for task in tasks:
#             if not task:
#                 continue
#             task_uid = safe_get(task, "getUniqueID", "")
#             if not task_uid:
#                 continue
#             is_summary = safe_get(task, "getSummary", False)
#             node_type = "WBS" if is_summary else "Task"
            
#             # Level-wise path
#             result = graph.run(f"""
#                 MATCH p=(w1:WBS {{UID:$UID1}})-[:HAS*]->(n1:{node_type} {{UID:$UID}})
#                 RETURN p
#                 LIMIT 1
#             """, UID1=first_node, UID=str(task_uid)).data()
            
#             path_str = "No Path" if not result else " → ".join([node['name'] for node in result[0]['p'].nodes])
#             level_embedding = generate_embedding(path_str) if result else generate_embedding("No Path")
            
#             graph.run(f"""
#                 MATCH (n:{node_type} {{UID:$UID}})
#                 SET n.Path_Level = $path,
#                     n.path_embedding_level = $embedding
#             """, UID=str(task_uid), path=path_str, embedding=level_embedding)
            
#             # Enhanced sequence-wise path with construction logic
#             if not is_summary:
#                 # Get construction sequence context (2 predecessors and 2 successors)
#                 seq_result = graph.run(f"""
#                     MATCH (t:Task {{UID:$UID}})
#                     OPTIONAL MATCH (pred1:Task)-[:SUCCESSOR]->(t)
#                     OPTIONAL MATCH (pred2:Task)-[:SUCCESSOR]->(pred1)
#                     OPTIONAL MATCH (t)-[:SUCCESSOR]->(suc1:Task)
#                     OPTIONAL MATCH (suc1)-[:SUCCESSOR]->(suc2:Task)
#                     WITH t, pred2, pred1, suc1, suc2
#                     RETURN 
#                         COALESCE(pred2.name, '') AS pred2_name,
#                         COALESCE(pred1.name, '') AS pred1_name,
#                         t.name AS current_name,
#                         COALESCE(suc1.name, '') AS suc1_name,
#                         COALESCE(suc2.name, '') AS suc2_name
#                     LIMIT 1
#                 """, UID=str(task_uid)).data()

#                 if seq_result:
#                     seq_data = seq_result[0]
#                     # Construct meaningful sequence path for construction workflow
#                     seq_parts = []
#                     if seq_data['pred2_name']:
#                         seq_parts.append(seq_data['pred2_name'])
#                     if seq_data['pred1_name']:
#                         seq_parts.append(seq_data['pred1_name'])
#                     seq_parts.append(seq_data['current_name'])
#                     if seq_data['suc1_name']:
#                         seq_parts.append(seq_data['suc1_name'])
#                     if seq_data['suc2_name']:
#                         seq_parts.append(seq_data['suc2_name'])
                    
#                     seq_path_str = " → ".join(seq_parts)
                    
#                     # Get the hierarchical context
#                     hierarchy_result = graph.run(f"""
#                         MATCH path=(root:WBS)-[:HAS*]->(t:Task {{UID:$UID}})
#                         RETURN REDUCE(s = '', n IN nodes(path) | s + ' > ' + n.name) AS hierarchy_path
#                         LIMIT 1
#                     """, UID=str(task_uid)).data()
                    
#                     hierarchy_path = hierarchy_result[0]['hierarchy_path'][3:] if hierarchy_result else ""
                    
#                     # Combine sequence and hierarchy for richer context
#                     full_context = f"{hierarchy_path} | Sequence: {seq_path_str}" if hierarchy_path else seq_path_str
#                     seq_embedding = generate_embedding(full_context)
                    
#                     graph.run(f"""
#                         MATCH (n:Task {{UID:$UID}})
#                         SET n.Path_Sequence = $path,
#                             n.path_embedding_sequence = $embedding,
#                             n.sequence_context = $context
#                     """, UID=str(task_uid), 
#                        path=seq_path_str, 
#                        embedding=seq_embedding,
#                        context=full_context)
#                 else:
#                     seq_embedding = generate_embedding("No Sequence")
#                     graph.run(f"""
#                         MATCH (n:Task {{UID:$UID}})
#                         SET n.Path_Sequence = 'No Sequence',
#                             n.path_embedding_sequence = $embedding
#                     """, UID=str(task_uid), embedding=seq_embedding)
                
#                 task_count += 1
#                 if task_count % 50 == 0 or task_count == len(tasks):
#                     print(f"Processed {task_count}/{len(tasks)} sequence embeddings")

#     print("Knowledge graph creation with enhanced sequence embeddings completed successfully")

# # Execute the conversion
# try:
#     file_path = "Hotel & Apartment programme.xer"
#     schedule2KG(file_path, graph)
# except Exception as e:
#     print(f"Failed to convert schedule: {str(e)}")
#     print("Troubleshooting Steps:")
#     print("1. Verify MPXJ 14.2.0 Installation:")
#     print("   - Ensure 'mpxj-14.2.0' directory contains mpxj.jar and lib folder with JARs (e.g., poi-5.4.1.jar).")
#     print("2. Verify File Path:")
#     print(f"   - Ensure 'Residential_Buildings_Egypt.xer' exists in {os.getcwd()}.")    
#     print(f"   - Use absolute path if needed (e.g., '/path/to/Residential_Buildings_Egypt.xer').")
#     print("3. Check .xer File Format:")
#     print("   - Open in a text editor to confirm '%T' headers (e.g., '%T PROJECT').")
#     print("4. Try Fallback Reader:")
#     print("   - Run with: schedule2KG(file_path, graph, use_fallback_reader=True)")
#     print("5. Convert to .xml:")
#     print("   - Export schedule as .xml from Primavera P6 and update file_path.")
#     print("6. Test with Sample File:")
#     print("   - Download a sample .xer from https://www.mpxj.org/ and test.")






























import os
import jpype
import glob
import sys
from py2neo import Graph, Node
from sentence_transformers import SentenceTransformer
import numpy as np

# Configure basic logging for progress
print = lambda *args, **kwargs: __import__('builtins').print(*args, **kwargs)  # Use print for progress

# Log environment details (minimal)
print(f"Python version: {sys.version}")
print(f"JPype version: {jpype.__version__}")
print(f"Working directory: {os.getcwd()}")
print(f"MPXJ directory: {os.path.abspath('mpxj-14.2.0')}")

# Configure Java environment for MPXJ
jar_dir = os.path.abspath("mpxj-14.2.0")
main_jar = os.path.join(jar_dir, "mpxj.jar")
lib_jars = glob.glob(os.path.join(jar_dir, "lib", "*.jar"))
if not os.path.exists(main_jar):
    raise FileNotFoundError(f"MPXJ main JAR not found: {main_jar}")
if not lib_jars:
    raise FileNotFoundError(f"No JAR files found in {os.path.join(jar_dir, 'lib')}")

classpath = os.pathsep.join([main_jar] + lib_jars)

if not jpype.isJVMStarted():
    try:
        jpype.startJVM(*["-Xmx512m", "-Dfile.encoding=UTF-8"], classpath=classpath)
        print("JVM started successfully with UTF-8 encoding")
    except Exception as e:
        raise Exception(f"Failed to start JVM: {str(e)}")

UniversalProjectReader = jpype.JClass("org.mpxj.reader.UniversalProjectReader")
reader = UniversalProjectReader()
print("Java class UniversalProjectReader loaded successfully")

# Load pre-trained embedding model
embedding_model = SentenceTransformer('intfloat/e5-large')
print("Loaded sentence transformer model: intfloat/e5-large")

# Connect to Neo4j
try:
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "1234567EEE"))
    print("Connected to Neo4j database")
except Exception as e:
    raise Exception(f"Failed to connect to Neo4j: {str(e)}")

def safe_get(obj, method, default=None):
    """Helper function to safely call Java object methods"""
    try:
        if obj and hasattr(obj, method):
            result = getattr(obj, method)()
            return result if result is not None else default
        return default
    except Exception:
        return default

def generate_embedding(text):
    """Generate embedding for a given text using the sentence transformer"""
    if not text or not isinstance(text, str):
        print(f"Warning: Invalid or empty text for embedding, using zeros")
        return np.zeros(embedding_model.get_sentence_embedding_dimension()).tolist()
    embedding = embedding_model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def validate_file(file_path):
    """Validate the existence and format of the input file"""
    absolute_path = os.path.abspath(file_path)
    if not os.path.exists(absolute_path):
        raise FileNotFoundError(f"File not found: {absolute_path}")
    
    file_ext = os.path.splitext(file_path)[1].lower()
    supported_extensions = ['.xer', '.mpp', '.xml']
    if file_ext not in supported_extensions:
        raise ValueError(f"Unsupported file extension: {file_ext}. Supported: {supported_extensions}")
    
    if file_ext == '.xer':
        encodings = ['utf-8', 'latin-1', 'iso-8859-1']
        valid_header = False
        first_lines = None
        for encoding in encodings:
            try:
                with open(absolute_path, 'r', encoding=encoding) as f:
                    first_lines = f.readlines()[:5]
                    if any(line.startswith('%T') for line in first_lines):
                        valid_header = True
                        break
            except Exception:
                continue
        
        if not valid_header:
            raise ValueError(f"Invalid .xer file structure: No %T headers found in {absolute_path}")
    
    print(f"Validated file: {absolute_path} (extension: {file_ext})")
    return file_ext

def schedule2KG(file, graph, use_fallback_reader=False):
    """Convert project schedule to knowledge graph with level-wise and sequence-wise embeddings"""
    # Validate file
    file_ext = validate_file(file)
    print(f"Processing file: {file}")

    # Clear existing graph
    try:
        graph.run("MATCH (n) DETACH DELETE n")
        print("Cleared existing graph")
    except Exception as e:
        raise Exception(f"Failed to clear graph: {str(e)}")
    
    # Read project file
    try:
        if use_fallback_reader and file_ext == '.xer':
            print("Using PrimaveraXERFileReader for .xer file")
            ProjectReader = jpype.JClass("org.mpxj.primavera.PrimaveraXERFileReader")
            reader = ProjectReader()
            reader.setCharset("UTF-8")
        else:
            print("Using UniversalProjectReader")
            reader = UniversalProjectReader()
        
        project = reader.read(file)
        if not project:
            raise ValueError("Failed to read project file: returned None")
        print(f"Successfully read project file: {file}")
    except Exception as e:
        if file_ext == '.xer' and not use_fallback_reader:
            print("Retrying with PrimaveraXERFileReader")
            return schedule2KG(file, graph, use_fallback_reader=True)
        raise ValueError(f"Unable to read project file: {str(e)}")
    
    # Process tasks
    tasks = safe_get(project, "getTasks", [])
    if not tasks:
        raise ValueError("No tasks found in project")
    print(f"Found {len(tasks)} tasks in project")
    
    task_count = 0
    for task in tasks:
        if not task:
            continue
            
        task_name = safe_get(task, "getName", "Unnamed Task")
        task_uid = safe_get(task, "getUniqueID", "")
        task_wbs = safe_get(task, "getWBS", "")
        
        # Get parent info safely
        parent_task = safe_get(task, "getParentTask")
        parent_name = safe_get(parent_task, "getName", "") if parent_task else ""
        
        # Common properties
        props = {
            "name": str(task_name),
            "UID": str(task_uid) if task_uid else "Unknown",
            "WBS": str(task_wbs) if task_wbs else "Unknown",
            "Parent": str(parent_name)
        }
        
        # Handle dates safely
        start_date = safe_get(task, "getStart")
        finish_date = safe_get(task, "getFinish")
        
        if start_date:
            props["Start"] = str(start_date.toString()).split("T")[0]
        if finish_date:
            props["Finish"] = str(finish_date.toString()).split("T")[0]
        
        # Create appropriate node type
        if safe_get(task, "hasChildTasks", False):
            node = Node("WBS", **props)
        elif start_date is not None:
            props.update({
                "Duration": str(safe_get(task, "getDuration", "")),
                "Total_Float": str(safe_get(task, "getTotalSlack", "")),
                "Critical_Path": str(safe_get(task, "getCritical", False))
            })
            node = Node("Task", **props)
        else:
            continue
            
        graph.create(node)
        task_count += 1
        if task_count % 100 == 0:
            print(f"Processed {task_count}/{len(tasks)} nodes")
    
    # Create hierarchical relationships
    for task in tasks:
        if not task or not safe_get(task, "getSummary", False):
            continue
            
        task_uid = safe_get(task, "getUniqueID", "")
        if not task_uid:
            continue
            
        children = safe_get(task, "getChildTasks", [])
        for child in children:
            if not child:
                continue
            child_uid = safe_get(child, "getUniqueID", "")
            if not child_uid:
                continue
                
            label = "WBS" if safe_get(child, "getSummary", False) else "Task"
            
            query = """
                MATCH (a:WBS {UID:$UID1})
                MATCH (b:%s {UID:$UID2})
                MERGE (a)-[:HAS]->(b)
            """ % label
            
            graph.run(query, UID1=str(task_uid), UID2=str(child_uid))
    
    # Create successor relationships
    for task in tasks:
        if not task:
            continue
            
        task_uid = safe_get(task, "getUniqueID", "")
        if not task_uid:
            continue
            
        successors = safe_get(task, "getSuccessors", [])
        for relation in successors:
            if not relation:
                continue
            target_id = safe_get(relation, "getTarget")
            if not target_id:
                continue
            target_uid = safe_get(target_id, "getUniqueID")
            
            rel_type = safe_get(relation, "getType", "Unknown")
            lag = safe_get(relation, "getLag", "0")
            
            graph.run("""
                MATCH (a:Task {UID:$UID1})
                MATCH (b:Task {UID:$UID2})
                MERGE (a)-[:SUCCESSOR {Relationship_Type:$Relationship, Lag:$Lag}]->(b)
            """,
            UID1=str(task_uid),
            UID2=str(target_uid) if target_uid else "Unknown",
            Lag=str(lag),
            Relationship=str(rel_type))
    
    # Calculate and store level-wise paths and embeddings
    first_node = graph.run("MATCH (w:WBS {Parent: ''}) RETURN w.UID LIMIT 1").evaluate()
    if not first_node:
        first_node = graph.run("MATCH (w:WBS) RETURN w.UID LIMIT 1").evaluate()
        print("Warning: No WBS node with empty Parent found; using first WBS node")
    
    if first_node:
        task_count = 0
        for task in tasks:
            if not task:
                continue
            task_uid = safe_get(task, "getUniqueID", "")
            if not task_uid:
                continue
            is_summary = safe_get(task, "getSummary", False)
            node_type = "WBS" if is_summary else "Task"
            
            # Level-wise path
            result = graph.run(f"""
                MATCH p=(w1:WBS {{UID:$UID1}})-[:HAS*]->(n1:{node_type} {{UID:$UID}})
                RETURN p
                LIMIT 1
            """, UID1=first_node, UID=str(task_uid)).data()
            
            path_str = "No Path" if not result else " → ".join([node['name'] for node in result[0]['p'].nodes])
            level_embedding = generate_embedding(path_str) if result else generate_embedding("No Path")
            
            graph.run(f"""
                MATCH (n:{node_type} {{UID:$UID}})
                SET n.Path_Level = $path,
                    n.path_embedding_level = $embedding
            """, UID=str(task_uid), path=path_str, embedding=level_embedding)
            
            # Enhanced sequence-wise path with construction logic
            if task:  # Ensure task exists before processing
                task_uid = safe_get(task, "getUniqueID", "")
                if task_uid:
                    # Get construction sequence context (2 predecessors and 2 successors)
                    seq_result = graph.run(f"""
                        MATCH (t:Task {{UID:$UID}})
                        OPTIONAL MATCH (pred1:Task)-[:SUCCESSOR]->(t)
                        OPTIONAL MATCH (pred2:Task)-[:SUCCESSOR]->(pred1)
                        OPTIONAL MATCH (t)-[:SUCCESSOR]->(suc1:Task)
                        OPTIONAL MATCH (suc1)-[:SUCCESSOR]->(suc2:Task)
                        WITH t, pred2, pred1, suc1, suc2
                        RETURN 
                            COALESCE(pred2.name, '') AS pred2_name,
                            COALESCE(pred1.name, '') AS pred1_name,
                            t.name AS current_name,
                            COALESCE(suc1.name, '') AS suc1_name,
                            COALESCE(suc2.name, '') AS suc2_name
                        LIMIT 1
                    """, UID=str(task_uid)).data()

                    if seq_result:
                        seq_data = seq_result[0]
                        # Construct meaningful sequence path for construction workflow
                        seq_parts = []
                        if seq_data['pred2_name']:
                            seq_parts.append(seq_data['pred2_name'])
                        if seq_data['pred1_name']:
                            seq_parts.append(seq_data['pred1_name'])
                        seq_parts.append(seq_data['current_name'])
                        if seq_data['suc1_name']:
                            seq_parts.append(seq_data['suc1_name'])
                        if seq_data['suc2_name']:
                            seq_parts.append(seq_data['suc2_name'])
                        
                        seq_path_str = " → ".join(seq_parts) if seq_parts else "No Sequence"
                        
                        # Get the hierarchical context
                        hierarchy_result = graph.run(f"""
                            MATCH path=(root:WBS)-[:HAS*]->(t:Task {{UID:$UID}})
                            RETURN REDUCE(s = '', n IN nodes(path) | s + ' > ' + n.name) AS hierarchy_path
                            LIMIT 1
                        """, UID=str(task_uid)).data()
                        
                        hierarchy_path = hierarchy_result[0]['hierarchy_path'][3:] if hierarchy_result and hierarchy_result[0]['hierarchy_path'] else ""
                        
                        # Combine sequence and hierarchy for richer context
                        full_context = f"{hierarchy_path} | Sequence: {seq_path_str}" if hierarchy_path and seq_path_str != "No Sequence" else seq_path_str
                        seq_embedding = generate_embedding(full_context if full_context else "No Sequence")
                        
                        graph.run(f"""
                            MATCH (n:Task {{UID:$UID}})
                            SET n.Path_Sequence = $path,
                                n.path_embedding_sequence = $embedding,
                                n.sequence_context = $context
                        """, UID=str(task_uid), 
                           path=seq_path_str, 
                           embedding=seq_embedding,
                           context=full_context)
                    else:
                        print(f"Warning: No sequence data for task UID {task_uid} (name: {task_name})")
                        seq_embedding = generate_embedding("No Sequence")
                        graph.run(f"""
                            MATCH (n:Task {{UID:$UID}})
                            SET n.Path_Sequence = 'No Sequence',
                                n.path_embedding_sequence = $embedding
                        """, UID=str(task_uid), embedding=seq_embedding)
                
                task_count += 1
                if task_count % 50 == 0 or task_count == len(tasks):
                    print(f"Processed {task_count}/{len(tasks)} sequence embeddings")

    print("Knowledge graph creation with enhanced sequence embeddings completed successfully")

# Execute the conversion
try:
    file_path = "Hotel & Apartment programme.xer"
    schedule2KG(file_path, graph)
except Exception as e:
    print(f"Failed to convert schedule: {str(e)}")
    print("Troubleshooting Steps:")
    print("1. Verify MPXJ 14.2.0 Installation:")
    print("   - Ensure 'mpxj-14.2.0' directory contains mpxj.jar and lib folder with JARs (e.g., poi-5.4.1.jar).")
    print("2. Verify File Path:")
    print(f"   - Ensure 'Residential_Buildings_Egypt.xer' exists in {os.getcwd()}.")    
    print(f"   - Use absolute path if needed (e.g., '/path/to/Residential_Buildings_Egypt.xer').")
    print("3. Check .xer File Format:")
    print("   - Open in a text editor to confirm '%T' headers (e.g., '%T PROJECT').")
    print("4. Try Fallback Reader:")
    print("   - Run with: schedule2KG(file_path, graph, use_fallback_reader=True)")
    print("5. Convert to .xml:")
    print("   - Export schedule as .xml from Primavera P6 and update file_path.")
    print("6. Test with Sample File:")
    print("   - Download a sample .xer from https://www.mpxj.org/ and test.")