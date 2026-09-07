# arXiv paper package

This directory contains the English Paper source for the public, fully synthetic Context-to-Card project.

- `main.tex`: arXiv-ready manuscript source.
- `references.bib`: bibliography with DOI/arXiv links.
- `main.pdf`: locally compiled nine-page review copy.

The paper intentionally reports the 40-case release as a deterministic reproducibility check, not as evidence of online effectiveness. All user, Event, POI, and environment examples are synthetic.

To compile in an environment with a LaTeX distribution (the checked build uses Tectonic):

```bash
tectonic -X compile main.tex
```

The source compiles locally to a nine-page PDF with four embedded TikZ architecture/workflow figures and a resolved bibliography. Before submission, replace the anonymous author line and perform the final arXiv metadata and license review.
