#!/usr/bin/env python3
""" Auto-generate a list of NOC Shop items for Sphinx to include."""

import os
import glob
import yaml
import subprocess
import mako.template


LIST_TEMPLATE_MD = mako.template.Template("""# List of NOC Shop Items

% if scan_results:
% for repo_name, repo_info in scan_results.items():
<%
    manifest = repo_info.get('manifest') or {}
    source_info = sources.get(repo_name) or {}
    
    # Use source file as fallback for manifest values
    title = manifest.get('title') or source_info.get('title') or repo_name
    brief = manifest.get('brief') or source_info.get('brief')
    authors = manifest.get('authors') or source_info.get('authors')
    license_info = manifest.get('license') or source_info.get('license')
    url = source_info.get('url')
%>
${'##'} ${title}

% if brief:
**Brief:** ${brief}

% endif
% if url:
**Repository:** [${url}](${url})

% endif
% if authors:
**Authors:** ${', '.join(authors) if isinstance(authors, list) else authors}

% endif
% if license_info:
**License:** ${license_info}

% endif
% if repo_info.get('rfnoc_blocks'):
${'###'} RFNoC Blocks

% for block in repo_info['rfnoc_blocks']:
- **${block['config'].get('name', block['name'])}**: ${block['config'].get('brief', 'No description available')}
% endfor

% endif
% if repo_info.get('rfnoc_modules'):
${'###'} RFNoC Modules

% for module in repo_info['rfnoc_modules']:
- **${module['name']}**
% endfor

% endif
% if repo_info.get('rfnoc_transport_adapters'):
${'###'} RFNoC Transport Adapters

% for adapter in repo_info['rfnoc_transport_adapters']:
- **${adapter['name']}**
% endfor

% endif

% endfor
% else:
No repositories found or scanned.
% endif
""")


def read_source_files():
    """Read all .yml files from sources directory and return as dictionary.
    
    Returns:
        dict: Dictionary with filename (without .yml) as key and YAML content as value
    """
    sources_dir = os.path.join(os.path.dirname(__file__), 'sources')
    yml_files = glob.glob(os.path.join(sources_dir, '*.yml'))
    
    result = {}
    for yml_file in yml_files:
        # Get filename without extension
        filename = os.path.splitext(os.path.basename(yml_file))[0]
        
        # Read and parse YAML content
        with open(yml_file, 'r') as f:
            try:
                content = yaml.safe_load(f)
                result[filename] = content
            except yaml.YAMLError as e:
                print(f"Error parsing {yml_file}: {e}")
                result[filename] = None
    
    return result


def clone_repositories(source_dict, clone_dir=None):
    """Clone repositories using shallow clones based on source dictionary.
    
    Args:
        source_dict (dict): Dictionary from read_source_files() with repo configurations
        clone_dir (str, optional): Directory to clone into. Defaults to 'cloned_repos' 
                                  in the same directory as this script.
    
    Returns:
        dict: Dictionary with repo names as keys and clone status/path as values
    """
    if clone_dir is None:
        clone_dir = os.path.join(os.path.dirname(__file__), 'cloned_repos')
    
    # Create clone directory if it doesn't exist
    os.makedirs(clone_dir, exist_ok=True)
    
    results = {}
    
    for repo_name, config in source_dict.items():
        if config is None:
            results[repo_name] = {'status': 'error', 'message': 'Invalid YAML config'}
            continue
            
        if 'source' not in config:
            results[repo_name] = {'status': 'error', 'message': 'No source URL found'}
            continue
        
        # Extract git URL (handle git+ prefix if present)
        git_url = config['source']
        if git_url.startswith('git+'):
            git_url = git_url[4:]  # Remove 'git+' prefix
        
        # Get branch if specified in config
        branch = config.get('gitbranch')
        
        # Target directory for this repo
        repo_dir = os.path.join(clone_dir, repo_name)
        
        try:
            # Remove existing directory if it exists
            if os.path.exists(repo_dir):
                import shutil
                shutil.rmtree(repo_dir)
            
            # Perform shallow clone
            cmd = [
                'git', 'clone', 
                '--depth', '1',  # Shallow clone
            ]
            
            # Only add branch option if specified in YAML
            if branch:
                cmd.extend(['--branch', branch])
            
            cmd.extend([git_url, repo_dir])
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            results[repo_name] = {
                'status': 'success', 
                'path': repo_dir,
                'branch': branch or 'default',
                'url': git_url
            }
            print(f"Successfully cloned {repo_name} to {repo_dir}")
            
        except subprocess.CalledProcessError as e:
            results[repo_name] = {
                'status': 'error', 
                'message': f"Git clone failed: {e.stderr}",
                'url': git_url
            }
            print(f"Failed to clone {repo_name}: {e.stderr}")
        except Exception as e:
            results[repo_name] = {
                'status': 'error', 
                'message': f"Unexpected error: {str(e)}",
                'url': git_url
            }
            print(f"Unexpected error cloning {repo_name}: {str(e)}")
    
    return results


def scan_cloned_repositories(clone_dir=None):
    """Scan all cloned repositories and extract information about RFNoC blocks.
    
    Args:
        clone_dir (str, optional): Directory containing cloned repos. Defaults to 'cloned_repos'
                                  in the same directory as this script.
    
    Returns:
        dict: Dictionary with repo names as keys and discovered information as values
    """
    if clone_dir is None:
        clone_dir = os.path.join(os.path.dirname(__file__), 'cloned_repos')
    
    if not os.path.exists(clone_dir):
        return {}
    
    scan_results = {}
    
    # Get all subdirectories (each should be a cloned repo)
    repo_dirs = [d for d in os.listdir(clone_dir) 
                 if os.path.isdir(os.path.join(clone_dir, d))]
    
    for repo_name in repo_dirs:
        repo_path = os.path.join(clone_dir, repo_name)
        repo_info = {
            'path': repo_path,
            'manifest': None,
            'readme': None,
            'rfnoc_blocks': [],
            'rfnoc_modules': [],
            'rfnoc_transport_adapters': [],
            'has_rfnoc': False
        }
        
        try:
            # Check for manifest.yml
            manifest_path = os.path.join(repo_path, 'manifest.yml')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    repo_info['manifest'] = yaml.safe_load(f)
            
            # Check for README.md
            readme_path = os.path.join(repo_path, 'README.md')
            if os.path.exists(readme_path):
                with open(readme_path, 'r') as f:
                    # Read first 100 lines for summary
                    lines = f.readlines()[:100]
                    repo_info['readme'] = ''.join(lines).strip()
            
            # Check for RFNoC structure
            rfnoc_dir = os.path.join(repo_path, 'rfnoc')
            if os.path.exists(rfnoc_dir):
                repo_info['has_rfnoc'] = True
                
                # Look for RFNoC blocks
                blocks_dir = os.path.join(rfnoc_dir, 'blocks')
                if os.path.exists(blocks_dir):
                    yml_files = glob.glob(os.path.join(blocks_dir, '*.yml'))
                    for yml_file in yml_files:
                        block_name = os.path.splitext(os.path.basename(yml_file))[0]
                        try:
                            with open(yml_file, 'r') as f:
                                block_info = yaml.safe_load(f)
                                repo_info['rfnoc_blocks'].append({
                                    'name': block_name,
                                    'file': yml_file,
                                    'config': block_info
                                })
                        except yaml.YAMLError as e:
                            print(f"Error parsing RFNoC block {yml_file}: {e}")
                
                # Look for RFNoC modules
                modules_dir = os.path.join(rfnoc_dir, 'modules')
                if os.path.exists(modules_dir):
                    yml_files = glob.glob(os.path.join(modules_dir, '*.yml'))
                    for yml_file in yml_files:
                        module_name = os.path.splitext(os.path.basename(yml_file))[0]
                        try:
                            with open(yml_file, 'r') as f:
                                module_info = yaml.safe_load(f)
                                repo_info['rfnoc_modules'].append({
                                    'name': module_name,
                                    'file': yml_file,
                                    'config': module_info
                                })
                        except yaml.YAMLError as e:
                            print(f"Error parsing RFNoC module {yml_file}: {e}")
                
                # Look for RFNoC transport adapters
                transport_dir = os.path.join(rfnoc_dir, 'transport_adapters')
                if os.path.exists(transport_dir):
                    yml_files = glob.glob(os.path.join(transport_dir, '*.yml'))
                    for yml_file in yml_files:
                        adapter_name = os.path.splitext(os.path.basename(yml_file))[0]
                        try:
                            with open(yml_file, 'r') as f:
                                adapter_info = yaml.safe_load(f)
                                repo_info['rfnoc_transport_adapters'].append({
                                    'name': adapter_name,
                                    'file': yml_file,
                                    'config': adapter_info
                                })
                        except yaml.YAMLError as e:
                            print(f"Error parsing RFNoC transport adapter {yml_file}: {e}")
        
        except Exception as e:
            repo_info['error'] = f"Error scanning repository: {str(e)}"
            print(f"Error scanning {repo_name}: {str(e)}")
        
        scan_results[repo_name] = repo_info
    
    return scan_results


def generate_shop_list():
    """ Generate a list of NOC Shop items for Sphinx to include."""
    print("Starting NOC Shop list generation...")
    
    # Read all source configurations
    print("Reading source files...")
    sources = read_source_files()
    print(f"Found {len(sources)} source configurations")
    
    # Clone all repositories
    print("Cloning repositories...")
    clone_results = clone_repositories(sources)
    successful_clones = [name for name, result in clone_results.items() 
                        if result['status'] == 'success']
    print(f"Successfully cloned {len(successful_clones)} repositories")
    
    # Scan cloned repositories for RFNoC components
    print("Scanning repositories...")
    scan_results = scan_cloned_repositories()
    
    # Generate output
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'source', 'autogen')
    os.makedirs(out_dir, exist_ok=True)
    out_path_md = os.path.join(out_dir, 'list.md')
    
    # Pass scan results to template for rendering
    with open(out_path_md, 'w') as f_md:
        f_md.write(LIST_TEMPLATE_MD.render(
            sources=sources,
            clone_results=clone_results,
            scan_results=scan_results
        ))
    
    print(f"Generated shop list at {out_path_md}")
    return scan_results
