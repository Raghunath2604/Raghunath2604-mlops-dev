import re
import os

path = "c:/Users/raghu/Downloads/mlopsdev-phase1-launch/mlops-dev/frontend/dashboard.html"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add escapeHTML function
escape_func = """function escapeHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}"""

content = re.sub(
    r'const PAGE_TITLES = \{.*?\};',
    "const PAGE_TITLES = {overview:'Overview',devices:'Devices',deployments:'Deployments',events:'Event log',drift:'Drift monitor',settings:'Settings'};\n\n" + escape_func,
    content
)

# 2. Replace d.name, d.hw_class, d.model_name, etc. with escaped versions in all innerHTML templates

# renderOvTable
content = re.sub(
    r'\$\{d\.name\}',
    r'${escapeHTML(d.name)}',
    content
)

content = re.sub(
    r'\$\{d\.hw_class\}',
    r'${escapeHTML(d.hw_class)}',
    content
)

content = re.sub(
    r'\$\{d\.os_info\}',
    r'${escapeHTML(d.os_info)}',
    content
)

content = re.sub(
    r'\$\{d\.model_name \? d\.model_name \+ \' \' \+ \(d\.model_tag\|\|\'\'\) : \'<span class="no-mod">None</span>\'\}',
    r'${d.model_name ? escapeHTML(d.model_name) + \' \' + escapeHTML(d.model_tag||\'\') : \'<span class="no-mod">None</span>\'}',
    content
)

content = re.sub(
    r'\$\{d\.model_name\}',
    r'${escapeHTML(d.model_name)}',
    content
)
content = re.sub(
    r'\$\{d\.model_tag\}',
    r'${escapeHTML(d.model_tag)}',
    content
)

content = re.sub(
    r'\$\{e\.action\}',
    r'${escapeHTML(e.action)}',
    content
)
content = re.sub(
    r'\$\{e\.details\}',
    r'${escapeHTML(e.details)}',
    content
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated successfully")
