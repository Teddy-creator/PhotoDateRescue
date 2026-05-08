# Xiaomi Native Motion Photo Sample Validation

**Date:** 2026-05-08  
**Dataset:** local Xiaomi 14 export sample  
**Scope:** 3 Xiaomi native camera embedded dynamic-photo candidates  
**Original media:** not modified

## Goal

Validate the Xiaomi native camera sample path:

```text
Xiaomi native embedded JPEG dynamic photo
-> motion-extract
-> still image + short video
-> portable-pair package
-> makelive metadata write
-> live-inspect metadata check
```

This validation proves metadata writing for the local sample set. It does not prove Apple Photos / iPhone import recognition; that still requires manual import testing.

## Sample Set

The sample candidates were selected from `/tmp/pdr-xiaomi-native-audit/motion_candidates.csv` and written to:

```text
/tmp/pdr-xiaomi-native-sample-candidates.csv
```

Rows:

```text
DCIM/Camera/IMG_20260425_173116.jpg
DCIM/Camera/IMG_20260425_173310.jpg
DCIM/Camera/MVIMG_20250518_214522.jpg
```

The set intentionally includes both `MotionPhoto` metadata and `MicroVideoOffset` metadata.

## Commands

Extract embedded video pairs:

```bash
.venv/bin/photodaterescue motion-extract \
  --candidates-csv /tmp/pdr-xiaomi-native-sample-candidates.csv \
  --source-root /path/to/xiaomi-raw-export \
  --output /tmp/pdr-xiaomi-native-sample-output \
  --report /tmp/pdr-xiaomi-native-sample-report
```

Build portable pair packages:

```bash
.venv/bin/photodaterescue live-build \
  --backend portable-pair \
  --pairs-csv /tmp/pdr-xiaomi-native-sample-report/extracted_pairs.csv \
  --source-root /tmp/pdr-xiaomi-native-sample-output \
  --output /tmp/pdr-xiaomi-native-sample-pairs \
  --report /tmp/pdr-xiaomi-native-sample-pair-report
```

Build Apple Live Photo metadata outputs with `makelive`:

```bash
.venv/bin/photodaterescue live-build \
  --backend makelive \
  --makelive /path/to/makelive \
  --pairs-csv /tmp/pdr-xiaomi-native-sample-report/extracted_pairs.csv \
  --source-root /tmp/pdr-xiaomi-native-sample-output \
  --output /tmp/pdr-xiaomi-native-makelive-output \
  --report /tmp/pdr-xiaomi-native-makelive-report
```

Inspect Apple Live Photo metadata:

```bash
.venv/bin/photodaterescue live-inspect --image <pair-image.jpg> --video <pair-video.mp4>
```

## Results

`motion-extract`:

```text
planned=3
extracted=3
skipped=0
errors=0
source_type_counts.xiaomi_native_camera.extracted=3
```

Extracted videos:

```text
IMG_20260425_173116.mp4: h264 1440x1080, aac, duration 1.5913s
IMG_20260425_173310.mp4: h264 1440x1080, aac, duration 3.0580s
MVIMG_20250518_214522.mp4: h264 1080x1440, aac, duration 1.9907s
```

Extracted still images:

```text
JPEG 4096x3072
DateTimeOriginal preserved
CreateDate preserved
Make/Model preserved
```

`portable-pair`:

```text
planned=3
built=3
skipped=0
errors=0
status_counts.built_pair=3
```

`live-inspect` for all 3 portable pairs:

```text
apple_live_status=no_live_metadata
content_identifier_match=False
image_content_identifier=None
video_content_identifier=None
image_apple_makernotes_present=False
```

`makelive`:

```text
planned=3
built=3
skipped=0
errors=0
status_counts.built=3
```

`live-inspect` for all 3 `makelive` output pairs:

```text
apple_live_status=metadata_match
content_identifier_match=True
image_content_identifier=<UUID>
video_content_identifier=<same UUID>
image_apple_makernotes_present=True
```

`makelive --check --manual <image> <video>` reported all 3 output pairs as Live Photos with matching identifiers.

## Conclusion

The Xiaomi native camera extraction path is validated for this small sample:

- The tool can identify Xiaomi native embedded dynamic-photo candidates.
- The tool can extract a still image and valid short video from the embedded JPEG.
- The tool can preserve the pair relationship via `portable-pair`.
- On macOS with `makelive`, the tool can write matching Apple Live Photo metadata for this 3-sample set.

The Apple Photos / iPhone import path is not validated:

- Real Apple Photos / iPhone import behavior is still `not_tested`.

## Next Step

Run a real Apple Photos / iPhone import validation:

```text
-> Apple Photos / iPhone import checklist
```

Only after that should documentation claim Apple Photos import success for Xiaomi native camera samples.
