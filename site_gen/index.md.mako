# The NoC Shop

Welcome to the NoC Shop! This is a collection of RFNoC blocks you can use in your applications.

Check out the following repositories containing RFNoC blocks:

% for repo_name, repo_info in scan_results.items():
<%
    manifest = repo_info.get('manifest') or {}
    # Extract values from merged manifest (which includes source defaults)
    title = manifest.get('title', repo_name)
    brief = manifest.get('brief')
    authors = manifest.get('authors')
    license_info = manifest.get('license')
    url = manifest.get('url')
    source = manifest.get('source')
%>
-  [${title}](autogen/${repo_name})${ ": " + brief if brief else "" }
% endfor


Do you have RFNoC blocks you would like to add to this list? Take a look at our
[instructions on adding out-of-tree modules to the NoC Shop](add_your_oot)!

```{toctree}
:caption: Noc Shop
:hidden:

% for repo_name, repo_info in scan_results.items():
autogen/${repo_name}
% endfor

add_your_oot
```
