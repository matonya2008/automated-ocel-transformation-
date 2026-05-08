# Sanitization Checklist

Use this checklist before pushing the repository to the public `matonya2008` account.

- Remove any raw industrial logs or plant extracts.
- Remove confidential object identifiers, operator identifiers, and internal codes if they came from real logs.
- Remove `.env` files, secrets, SSH material, API keys, and access tokens.
- Remove absolute local filesystem paths from scripts, notebooks, and docs.
- Remove partner names from code comments or config files unless already disclosed in the paper.
- Verify that all CSV files in `data/` are synthetic or aggregate-only.
- Verify that all figures can be regenerated from the public sample data or safe aggregate CSVs.
- Verify that the final `README.md` does not claim public assets that have not yet been uploaded.
- Tag the GitHub release before minting the Zenodo DOI.
