# Gotchas

- **File Encodings**: `Brand and Founder Stories.docx` parsing directly generated Unicode character `₹` causing `cp1252` encode errors in Windows Python scripts without `encoding='utf-8'`.
- **Artifact Paths**: Artifact creation requires absolute paths to the system's brain folder structure, not arbitrary workspace locations.
- **Shopify Zip Upload Validations**: Using standard Windows `Compress-Archive` to zip a Shopify theme folder often fails on upload (`missing template layout/theme.liquid`) because it wrongly encodes paths with backward slashes (`\`). Use the `tar -a -c -f ...` utility on Windows to create a POSIX-compliant zip file.
