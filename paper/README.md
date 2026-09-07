# arXiv paper package

This directory contains the English Paper source for the public, fully synthetic Context-to-Card project.

- `main.tex`: arXiv-ready manuscript source.
- `references.bib`: bibliography with DOI/arXiv links.

The paper intentionally reports the 40-case release as a deterministic reproducibility check, not as evidence of online effectiveness. All user, Event, POI, and environment examples are synthetic.

To compile in an environment with a LaTeX distribution:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The current workspace does not include a LaTeX compiler; source-level checks and repository tests are run locally, while final PDF compilation should be performed in a TeX environment before arXiv submission.
