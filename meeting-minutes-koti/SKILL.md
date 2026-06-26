---
name: meeting-minutes-koti
description: Create Korean public-sector meeting minutes from audio recordings, captured meeting notice emails, and the official HWPX meeting-minutes template. Use when Codex needs to transcribe Korean meeting audio files, read .eml meeting notice emails for agenda/date/attendee context, and produce final Hangul HWPX minutes in official reporting style.
---

# Meeting Minutes KOTI

## Overview

Use this skill to turn Korean meeting recordings into official public-sector meeting minutes. The default final output is a filled HWPX using `회의록_양식.hwpx`.

Keep only these deliverables in the working meeting folder unless the user explicitly asks otherwise:

- `회의공지_참고정보.md`
- Final HWPX files named `YYMMDD - 회의제목 회의록.hwpx`

Transcripts, Markdown drafts, DOCX files, validation extracts, and experimental HWPX files are temporary working files. Remove them from the meeting folder after final HWPX files are created and verified.

## Workflow

1. Locate inputs:
   - Audio recordings: `.mp3`, `.m4a`, `.wav`, `.aac`, `.flac`, `.ogg`, `.webm`
   - Meeting notice emails: `.eml`
   - Template: prefer local `회의록_양식.hwpx`; otherwise use bundled `assets/회의록_양식.hwpx`
   - Optional context: project name, meeting date/time/place, attendee list, agenda, previous minutes

2. Transcribe each audio file locally with Whisper:

```powershell
python "C:\Users\KOTI\.codex\skills\meeting-minutes-koti\scripts\transcribe_local_whisper.py" `
  --out ".\recording_1_전사.md" `
  ".\recording_1.mp3"
```

Use `scripts/transcribe_local_whisper.py` as the only transcription path. It loads a Transformers Whisper model from the local Hugging Face cache and downloads the model automatically when it is not cached. If `torch`, `transformers`, `huggingface_hub`, or `imageio-ffmpeg` are unavailable, or the model cannot be downloaded because the network is unavailable, clearly report the blocker and do not invent transcript content.

3. Read captured meeting notice emails when `.eml` files exist:

```powershell
python "C:\Users\KOTI\.codex\skills\meeting-minutes-koti\scripts\parse_eml_notice.py" `
  --out ".\회의공지_참고정보.md" `
  ".\notice.eml"
```

Use notice email content as context, not as a substitute for the transcript. Prefer email metadata for meeting title, agenda, scheduled date/time, location/link, attendees, organizer, and requested preparation items. If email context conflicts with the audio transcript, trust the audio for actual discussion and mark the conflict under `확인 필요 사항` in the working draft.

4. Draft one Markdown minutes file per audio recording:
   - Read `references/report-style.md` for tone and selection rules.
   - Read `references/template-fields.md` for the target sections.
   - Read `references/email-notice.md` when `.eml` files are present.
   - Keep decisions, requests, issues, schedule, responsibilities, and follow-up actions.
   - Omit filler conversation, repeated acknowledgements, and unimportant digressions.
   - Mark uncertain names or inaudible segments as `[확인 필요: ...]`.

5. Fill the HWPX template:

```powershell
python "C:\Users\KOTI\.codex\skills\meeting-minutes-koti\scripts\minutes_md_to_hwpx_template.py" `
  --template ".\회의록_양식.hwpx" `
  --input ".\recording_1_회의록.md" `
  --output ".\recording_1_회의록_작업본.hwpx" `
  --style-reference ".\회의록_양식.hwpx"
```

6. Rename the verified HWPX to the official filename:

```powershell
python "C:\Users\KOTI\.codex\skills\meeting-minutes-koti\scripts\official_hwpx_name.py" `
  --input ".\recording_1_회의록.md" `
  --directory "."
```

The filename rule is:

- Date: use `개최일시` from the minutes draft, formatted as `YYMMDD`
- Title: use `회의명`, shorten repeated program prefixes when appropriate
- Format: `YYMMDD - 회의제목 회의록.hwpx`
- Example: `260522 - 온보딩 프로그램 회의록.hwpx`
- Remove Windows-invalid filename characters: `< > : " / \ | ? *`

7. Verify and clean up:
   - Confirm each final `.hwpx` is a valid ZIP/HWPX package.
   - Optionally use `kordoc` to inspect HWPX content, but do not keep validation extracts in the meeting folder.
   - Delete temporary transcript, draft, DOCX, validation, and non-final HWPX files from the meeting folder.
   - Keep source `.mp3` and `.eml` files unless the user explicitly asks to remove them.

## Document Rules

- Write in Korean.
- Use public-sector reporting style: concise, formal, noun-ending where natural, and action-oriented.
- Do not write a verbatim transcript as the meeting minutes.
- Preserve the template's main fields: `과제명`, `회의명`, `개최일시·장소`, `참석인원`, `회의목적`, `회의내용`.
- For `회의내용`, organize content with major bullets and sub-bullets. Lead with agenda/result, then supporting discussion.
- Use exact dates/times from the transcript, notice email, or file/folder names only when reasonably inferable; otherwise mark `[확인 필요]`.
- Keep personal names, institution names, and technical terms as spoken when clear; do not normalize them beyond obvious spelling fixes.
- Add a short `확인 필요 사항` section at the end of the working Markdown draft if there are missing metadata fields or ambiguous transcript parts.

## HWPX Formatting Rules

- Preserve the current `회의록_양식.hwpx` layout and styles.
- Use the active local HWPX template as the target formatting source when the user edits the template.
- Align all table cell contents to the top.
- Keep paragraph line spacing at `160%` for every generated HWPX paragraph style.
- Resize the generated meeting-content row and total table height from the actual content length instead of preserving a fixed template height.
- Keep table text wrapping enabled so long content can expand naturally.
- Do not create arbitrary new styles for generated text.
- Apply existing role styles consistently:
  - `❑ 네모` or equivalent existing square-bullet style for lines beginning with `□` or `❑`
  - `- 하이픈` or equivalent existing hyphen-bullet style for lines beginning with `-`
  - Body/content style for regular field text
- Preserve KoPub Dotum and template typography.
- Do not force text to fit on one line. Wrapping is allowed.
- Do not apply negative character spacing. Keep character spacing at `0`, including the hyphen bullet style.
- Do not use paragraph condensation to prevent line breaks. Keep paragraph `condense` at `0`.
- Do not bottom-align long meeting-content cells.

## Kordoc Usage

Use `kordoc` for HWP/HWPX reading and output verification when needed:

```powershell
npx --yes --package kordoc --package pdfjs-dist kordoc ".\final.hwpx"
```

For fallback Markdown to HWPX generation, use the `markdownToHwpx()` Node API from `kordoc`. Prefer the template-filling script whenever the official template exists.

```powershell
node "C:\Users\KOTI\.codex\skills\meeting-minutes-koti\scripts\markdown_to_hwpx.mjs" ".\회의록.md" ".\회의록.hwpx"
```

## Resources

- `scripts/transcribe_local_whisper.py`: Transcribe audio locally with Transformers Whisper. Downloads the configured Hugging Face model automatically when it is not already cached.
- `scripts/parse_eml_notice.py`: Extract readable meeting notice context from `.eml` files.
- `scripts/minutes_md_to_hwpx_template.py`: Fill `회의록_양식.hwpx` from a meeting-minutes Markdown draft while preserving the HWPX template.
- `scripts/official_hwpx_name.py`: Build the official final HWPX filename from the draft fields.
- `scripts/minutes_md_to_docx.py`: Legacy Word output helper. Use only when the user explicitly asks for DOCX.
- `scripts/markdown_to_hwpx.mjs`: Fallback Markdown-to-HWPX converter using `kordoc`.
- `references/report-style.md`: Public-sector meeting-minutes drafting rules.
- `references/email-notice.md`: Rules for applying captured `.eml` meeting notices to minutes.
- `references/template-fields.md`: Field mapping for the bundled template.
- `assets/회의록_양식.hwpx`: Default HWPX template.

## Done When

- One final official HWPX exists per source recording.
- `회의공지_참고정보.md` exists when `.eml` notice files are present.
- The HWPX files preserve the template style roles and do not force text onto one line.
- The working folder contains only source files, `회의공지_참고정보.md`, and official final HWPX outputs.
