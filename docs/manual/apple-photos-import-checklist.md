# Apple Photos Import Checklist

Use this after `photodaterescue repair` finishes and before you trust the repaired library at full scale.

## 1. Verify the source stayed untouched

- Compare a repaired sample and its source copy.
- Run:

```bash
exiftool -time:all -a -G1 /path/to/source.jpg
exiftool -time:all -a -G1 /path/to/repaired.jpg
```

- Confirm the source file was not edited in place.

## 2. Check the generated reports

- Open `summary.json`
- Open `files.csv`
- Open `high_risk.csv`
- Make sure the number of `repairable` files matches your expectation.

## 3. Import a small repaired sample into Apple Photos first

- Do not import the full repaired folder first.
- Start with a folder that contains:
  - a known-good EXIF photo
  - a known-bad downloaded image
  - one high-risk file you intentionally left out

## 4. Inspect the timeline placement

- Confirm repaired files no longer appear under the import day if a better timestamp was available.
- Confirm already-correct files still land on the expected date if you used `--copy-all`.

## 5. Only then scale up

- Once the sample import looks correct, run the tool on the larger directory.
- Keep the original export untouched until you are satisfied with the repaired result.
