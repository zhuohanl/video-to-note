# pHash Spike

Date: 2026-06-06
Status: passed locally.

## Contract Locked

- Use Pillow + `imagehash.phash`.
- pHash is represented as a 64-bit hexadecimal string by default.
- Observed generated near-duplicate distance: 4.
- Observed generated different-frame distance: 28.
- Initial duplicate threshold: Hamming distance <= 8; tune later with real frames if needed.

## Command

`uv run python spikes/spike_phash.py`
