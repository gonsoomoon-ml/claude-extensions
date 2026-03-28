---
name: aws-blog-table
description: Generate a styled HTML table for AWS blog posts (dark header, alternating rows, compact nowrap columns). Use this when making a table HTML to insert in an AWS blog HTML file.
---

Generate an HTML table for AWS blog posts. The table must be fully self-contained with all styles inline — do NOT rely on blog CSS for backgrounds, colors, or borders.

## Structure rules
- Use `<table>` > `<tbody>` only — no `<thead>` or `<th>`
- Header row uses `<td>` (not `<th>`) — AWS blog CMS strips `<th>` styling
- No `width:100%` — table fits content naturally

## Header cells (first `<tr>`)
- `background-color:#232F3E;color:#ffffff;padding:8px 12px;border:1px solid #D5DBDB !important;text-align:center;font-weight:700`

## Data cells
- Odd rows: `background-color:#ffffff`
- Even rows: `background-color:#F2F3F3`
- All data cells: `color:#000000;padding:8px 12px;border:1px solid #D5DBDB !important;text-align:left`
- First column of data rows: add `font-weight:600`
- Short/fixed-width columns (names, numbers): add `white-space:nowrap`
- Long text columns (descriptions): omit `white-space:nowrap` to allow wrapping

## Table-level style
- `border-collapse:collapse;font-family:'Segoe UI',Arial,sans-serif;font-size:12px`

## Why inline `background-color` is required
AWS blog CSS (`blog.css`, `style-awsm.css`, `style-awsm-base.css`) provides NO background colors for table cells. Without explicit `background-color`, header text (`color:#ffffff`) becomes invisible on white background.

The user will provide the table data as text or markdown.
Output the complete inline-styled `<table>` HTML.
If the user wants a preview, wrap it in a minimal HTML document and open in browser.
