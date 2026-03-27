# Vercel Deployment Fix - 2026-03-27

## Problem

- Vercel build fails with: No flask entrypoint found.

## Plan

- Export a module-level Flask app instance in app.py as `app = create_app()` so Vercel can detect the entrypoint.
- Keep all existing routes and logic unchanged.

## Changes Made

- Updated `app.py` to export `app = create_app()` at module level.
- Kept existing `if __name__ == '__main__':` behavior and run command.

## Verification

- Checked IDE diagnostics for `app.py` and found no errors.
