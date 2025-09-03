<%
    manifest = repo.get('manifest') or {}
    
    title = manifest.get('title')
    brief = manifest.get('brief')
    authors = manifest.get('authors')
    license_info = manifest.get('license')
    hdl_license_info = manifest.get('hdl_license')
    url = manifest.get('url')
    source = manifest.get('source', '')
%>
${'#'} ${title}

% if brief:
${brief}

% endif
% if url:
**Home page:** [${url | sanitize_url}](${url})

% endif
**Git repository:** [${source | sanitize_url}](${source})

% if authors:
**Authors:** ${', '.join(authors) if isinstance(authors, list) else authors}

% endif
% if repo.get('rfnoc_blocks'):
${'##'} RFNoC Blocks

% for block in repo['rfnoc_blocks']:
<%
  block_brief = block['config'].get('brief', 'No description available')
%>
- **${block['config'].get('name', block['name'])}**${ ": " + block_brief if block_brief else "" }
  - Software License: ${block['config'].get('license', license_info)}
  - HDL License: ${block['config'].get('hdl_license', hdl_license_info)}

% endfor

% endif
% if repo.get('rfnoc_modules'):
${'###'} RFNoC Modules

% for module in repo['rfnoc_modules']:
- **${module['name']}**
% endfor

% endif
% if repo.get('rfnoc_transport_adapters'):
${'###'} RFNoC Transport Adapters

% for adapter in repo['rfnoc_transport_adapters']:
- **${adapter['name']}**
% endfor

% endif