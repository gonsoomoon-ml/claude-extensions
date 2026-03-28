---
name: aws-blog-table
description: Generate a styled HTML table for AWS blog posts (dark header, alternating rows, compact nowrap columns). Use this when making a table HTML to insert in an AWS blog HTML file.
---

Generate an HTML table with this exact style:
- No `width:100%` — table fits content naturally
- Header: background `#232F3E`, white text, `padding:8px 12px`, `text-align:center`
- Rows: alternating `#ffffff` / `#F2F3F3`
- All data cells: `color:#000000`, `white-space:nowrap`, border `1px solid #D5DBDB`, `text-align:left`
- First column: `font-weight:600` (no special color)
- Font: 'Segoe UI', Arial, sans-serif at 12px
- Border-collapse: collapse

The user will provide the table data as text or markdown.
Output the complete inline-styled <table> HTML.
If the user wants a preview, wrap it in a minimal HTML document and open in browser.
