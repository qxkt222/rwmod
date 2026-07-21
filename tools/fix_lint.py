import os
os.chdir(r"D:\1233344\rwmod")

# 1. workshop.py - add import re (missing from _scrape_collection_page)
with open("src/rwmod/workshop.py", "r", encoding="utf-8") as f:
    c = f.read()

# The file already has import re at top. Check if it exists.
if "import re" not in c[:50]:
    # Add import re after the docstring
    c = c.replace(
        "import json",
        "import re\nimport json",
        1
    )
    print("Added import re to workshop.py")
else:
    # import re exists but might be scoped wrong - check if it appears twice
    print("import re already exists, checking usage...")
    # The issue is in _scrape_collection_page which is a separate function -
    # it should have access to the module-level import re. Let me check if re is at module level.
    first = c.split("import re")
    print(f"Found {len(first)-1} occurrences of import re")

# 2. Fix E501 lines in workshop.py - line 148 and 173
c = c.replace(
    'log.info("Collection %s: found %d mods via user API key", collection_id, len(result))',
    'log.info(\n                    "Collection %s: found %d mods via user API key",\n                    collection_id, len(result),\n                )'
)

c = c.replace(
    '                headers={"User-Agent": "rwmod/1.0", "Content-Type": "application/x-www-form-urlencoded"},',
    '                headers={\n                    "User-Agent": "rwmod/1.0",\n                    "Content-Type": "application/x-www-form-urlencoded",\n                },'
)

with open("src/rwmod/workshop.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(c)

print("workshop.py fixed")
