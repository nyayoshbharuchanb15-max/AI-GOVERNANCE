# Contributing to AI Governance MCP Server

Thank you for considering contributing. By submitting any contribution
(code, documentation, feedback), you agree to the following terms designed
to protect the intellectual property of the project.

## Developer Certificate of Origin (DCO)

To maintain legal integrity and protect the project's IP, every contributor
must certify that they have the right to submit their contribution under
the project's license terms.

By making a contribution, you certify:

1. The contribution was created in whole or in part by you, and you have
   the right to submit it under the project's license; OR
2. The contribution is based upon previous work that you have the right
   to submit under the project's license; OR
3. The contribution was provided directly to you by someone who certified
   (1) or (2), and you have not modified it.

You understand that your contribution:
- Becomes part of a project that uses a **dual-licensing model** (see LICENSE.md)
- Does NOT grant you any ownership or patent rights to the project
- May be used commercially under the terms of the Commercial License

### Signing Off

All commit messages must include a `Signed-off-by` line:

```
Signed-off-by: Your Name <your.email@example.com>
```

This can be added automatically with:
```bash
git commit -s -m "Your commit message"
```

## Contributor License Agreement (CLA)

If your contribution is significant (new features, substantial code changes),
you may be asked to sign a formal Contributor License Agreement that:
- Grants the project owner the right to use your contribution commercially
- Confirms you have the right to submit the work
- Does not affect your ownership of the original work

## Our Standards

- Write clear, commented code
- Include regulatory mapping comments for compliance features
- Test your changes
- Keep documentation updated

## macOS Development Notes

### Building the `cryptography` wheel

The `cryptography` package requires Rust and OpenSSL development headers
to build from source. On macOS, this often fails with:

```
error: can't find Rust compiler
```

**Solution — install Rust via rustup:**

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

If you still see OpenSSL header errors, install OpenSSL via Homebrew:

```bash
brew install openssl
export LDFLAGS="-L/opt/homebrew/opt/openssl/lib"
export CPPFLAGS="-I/opt/homebrew/opt/openssl/include"
```

Then re-run `pip install -r requirements.txt`.

### Pre-built wheels (alternative)

Install a pre-built `cryptography` wheel to avoid the Rust build:

```bash
pip install cryptography --only-binary=:all:
```

If your Python version is not available as a pre-built wheel, upgrade
Python via Homebrew: `brew install python@3.12`.

### Running without a database

The server starts and serves the `/health` endpoint even when PostgreSQL,
Neo4j, or Redis are unavailable (graceful degradation). Dependencies are
probed at runtime and reported in the health response.

Alembic migrations are provided in `python-backend/alembic/`. Run them
against a live database with:

```bash
cd python-backend
ALEMBIC_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" alembic upgrade head
```

## Questions?

Open an issue at https://github.com/nyayoshbharuchanb15-max/AI-GOVERNANCE
