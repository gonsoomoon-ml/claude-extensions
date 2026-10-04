"""Make a slim black base template from an existing AWS deck (keeps master + layouts, drops all slides).

Usage: python3 make_base.py <source.pptx> <base-black.pptx>
Result: ~7MB file whose layouts ("1_Blank", "Title Only", "Title Slide", "Thank You", "Code") provide the
black gradient background, the AWS logo and the copyright line — so build code adds no background image,
no logo, no page numbers.

The result is an AWS template — keep it out of public repositories (`assets/` is git-ignored in this profile).
"""
import sys
from pptx import Presentation

src, dst = sys.argv[1], sys.argv[2]
prs = Presentation(src)
lst = prs.slides._sldIdLst
for sid in list(lst):
    prs.part.drop_rel(sid.rId); lst.remove(sid)
prs.save(dst)
print("layouts:", [l.name for l in prs.slide_layouts])
