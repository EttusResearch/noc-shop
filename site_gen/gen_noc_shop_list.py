#!/usr/bin/env python3
""" Auto-generate a list of NOC Shop items for Sphinx to include."""

import os
import glob
import yaml
import subprocess
import mako.template


def sanitize_url(url_str):
    """Sanitize a URL for display in a Markdown file.

    This should return the string url_str, but in a way that it is nicer to
    display. This means:
    - Remove any http://, https:// prefix
    - Remove a git+ prefix
    """
    url_str = url_str.replace('http://', '').replace('https://', '').replace('git+', '')
    return url_str


def render_template_to_file(data, template_path, out_path):
    """Render a Mako template to a file."""
    template = mako.template.Template(filename=template_path)
    with open(out_path, 'w') as f:
        f.write(template.render(**data, sanitize_url=sanitize_url))


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
        clone_dir (str, optional): Directory to clone into. Defaults to 'build/cloned_repos' 
                                  in the same directory as this script.
    
    Returns:
        dict: Dictionary with repo names as keys and clone status/path as values
    """
    if clone_dir is None:
        clone_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'cloned_repos')
    
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


def scan_cloned_repositories(clone_dir=None, sources=None):
    """Scan all cloned repositories and extract information about RFNoC blocks.
    
    Args:
        clone_dir (str, optional): Directory containing cloned repos. Defaults to 'build/cloned_repos'
        sources (dict, optional): Source configurations to use as defaults for manifest values.
    
    Returns:
        dict: Dictionary with repo names as keys and discovered information as values
    """
    if clone_dir is None:
        clone_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'cloned_repos')
    
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
            # Start with source file values as defaults
            source_info = sources.get(repo_name, {}) if sources else {}
            merged_manifest = source_info.copy()
            
            # Check for manifest.yml and merge with source defaults
            manifest_path = os.path.join(repo_path, 'manifest.yml')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    manifest_data = yaml.safe_load(f) or {}
                    # Manifest values override source values
                    merged_manifest.update(manifest_data)
            
            repo_info['manifest'] = merged_manifest
            
            # Check for README.md
            readme_path = os.path.join(repo_path, 'README.md')
            if os.path.exists(readme_path):
                with open(readme_path, 'r') as f:
                    # Read first 100 lines for summary
                    lines = f.readlines()[:100]
                    repo_info['readme'] = ''.join(lines).strip()
            
            # Check for RFNoC structure
            # Use rfnoc_path from source config if provided, otherwise default to 'rfnoc'
            rfnoc_subpath = source_info.get('rfnoc_path', 'rfnoc')
            rfnoc_dir = os.path.join(repo_path, rfnoc_subpath)
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
    scan_results = scan_cloned_repositories(sources=sources)
    
    # Generate output directory
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'source', 'autogen')
    os.makedirs(out_dir, exist_ok=True)
    
    # Generate one file per repository
    generated_files = []
    oot_template_path = os.path.join(os.path.dirname(__file__), 'oot-page.md.mako')
    
    for repo_name, repo_info in scan_results.items():
        # Create filename based on repo name
        filename = f"{repo_name}.md"
        oot_page_path = os.path.join(out_dir, filename)
        
        # Render template for this repository using the helper function
        render_template_to_file(
            data={
                'repo': repo_info,
                'repo_name': repo_name
            },
            template_path=oot_template_path,
            out_path=oot_page_path
        )
        
        generated_files.append(filename)
        print(f"Generated {filename}")
    
    # Generate index file with list of all repositories
    index_template_path = os.path.join(os.path.dirname(__file__), 'index.md.mako')
    index_path = os.path.join(out_dir, '..', 'index.md')
    
    render_template_to_file(
        data={'scan_results': scan_results},
        template_path=index_template_path,
        out_path=index_path
    )

    print(f"Generated {len(generated_files)} repository pages and index at {out_dir}")
    return scan_results


def main():
    """Main function for running the script directly."""
    try:
        result = generate_shop_list()
        print("\nSummary:")
        print(f"Processed {len(result)} repositories:")
        for repo_name, repo_info in result.items():
            blocks_count = len(repo_info.get('rfnoc_blocks', []))
            modules_count = len(repo_info.get('rfnoc_modules', []))
            adapters_count = len(repo_info.get('rfnoc_transport_adapters', []))
            print(f"  - {repo_name}: {blocks_count} blocks, {modules_count} modules, {adapters_count} adapters")
        
        print("\nGeneration completed successfully!")
        
    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
