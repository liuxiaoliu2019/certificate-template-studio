# Contributing

Contributions that improve reliability, visual consistency, accessibility, documentation, schemas, or test coverage are welcome.

## Before submitting

1. Keep the fixed two-option startup menu unchanged unless the change is explicitly discussed first.
2. Do not commit textbook covers, publisher logos, downloaded certificate references, generated user artwork, personal paths, credentials, or project output directories.
3. Use fictional names and `*-not-included.*` placeholders in examples.
4. Preserve explicit landscape and portrait approval gates.
5. Preserve character identity locks whenever a design uses a source character.
6. Add or update tests for schema and state-machine changes.

Run:

```bash
python -m pip install -r requirements-dev.txt
python scripts/quick_validate.py .
python scripts/public_release_validate.py .
```

Use a focused branch and a concise English commit message. Explain the user-visible behavior, compatibility impact, and validation performed in the pull request.

By contributing code or documentation, you agree that it may be distributed under the MIT License. Only contribute visual assets that you have the right to license, and state their license clearly.
