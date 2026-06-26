# meeting-minutes-koti 배포 패키지

한국어 회의 녹음 파일을 전사하고, `.eml` 회의공지 메일을 참고하여 공무원 보고형식 회의록을 작성한 뒤, 공식 HWPX 회의록 파일을 생성하는 Codex skill입니다.

## 포함 파일

```text
meeting-minutes-koti-skill-package/
  README_INSTALL.md
  meeting-minutes-koti/
    SKILL.md
    assets/
      회의록_양식.hwpx
    references/
      email-notice.md
      report-style.md
      template-fields.md
      template-extracted.md
    scripts/
      minutes_md_to_hwpx_template.py
      official_hwpx_name.py
      parse_eml_notice.py
      transcribe_local_whisper.py
      markdown_to_hwpx.mjs
      minutes_md_to_docx.py
```

## 설치 방법

1. ZIP 파일을 풉니다.
2. `meeting-minutes-koti` 폴더를 Codex skill 폴더로 복사합니다.

Windows PowerShell:

```powershell
Copy-Item -LiteralPath ".\meeting-minutes-koti" -Destination "$env:USERPROFILE\.codex\skills\meeting-minutes-koti" -Recurse -Force
```

3. Codex를 다시 시작합니다.
4. 대화에서 `$meeting-minutes-koti`를 호출합니다.

예:

```text
$meeting-minutes-koti 이 폴더 녹음 파일들로 파일당 1개씩 회의록 작성해줘
```

## 권장 입력 파일

- 녹음 파일: `.mp3`, `.m4a`, `.wav`, `.aac`, `.flac`, `.ogg`, `.webm`
- 회의공지 메일: `.eml`
- 한글 양식: `회의록_양식.hwpx`

기본 양식은 `meeting-minutes-koti/assets/회의록_양식.hwpx`에 포함되어 있습니다. 다른 양식을 쓰려면 작업 폴더에 `회의록_양식.hwpx`를 두면 됩니다.

## 최종 산출물

작업 폴더에는 최종적으로 다음 파일만 남기는 것을 기본 원칙으로 합니다.

```text
회의공지_참고정보.md
YYMMDD - 회의제목 회의록.hwpx
```

예:

```text
260522 - 온보딩 프로그램 회의록.hwpx
```

전사 파일, Markdown 초안, DOCX 파일, 검증 추출 파일, 실험용 HWPX 파일은 작업 중간 산출물이므로 최종 확인 후 삭제합니다. 원본 녹음 파일과 `.eml` 파일은 삭제하지 않습니다.

## 필요 환경

필수:

- Python 3.10 이상

로컬 Whisper 전사를 사용할 경우:

```powershell
python -m pip install torch transformers huggingface_hub imageio-ffmpeg requests
```

Whisper model files are loaded from the local Hugging Face cache. If the configured model is not cached, the transcription script downloads it automatically from the Hugging Face Hub.

HWP/HWPX 검증이나 fallback 변환이 필요할 경우:

```powershell
npx --yes --package kordoc --package pdfjs-dist kordoc --help
```

## 주요 스크립트

### `.eml` 회의공지 추출

```powershell
python ".\meeting-minutes-koti\scripts\parse_eml_notice.py" `
  --out ".\회의공지_참고정보.md" `
  ".\회의공지.eml"
```

### 로컬 Whisper 전사

```powershell
python ".\meeting-minutes-koti\scripts\transcribe_local_whisper.py" `
  --out ".\recording_1_전사.md" `
  ".\recording_1.mp3"
```

### Markdown 회의록을 HWPX 양식에 채우기

```powershell
python ".\meeting-minutes-koti\scripts\minutes_md_to_hwpx_template.py" `
  --template ".\회의록_양식.hwpx" `
  --input ".\recording_1_회의록.md" `
  --output ".\recording_1_회의록_작업본.hwpx" `
  --style-reference ".\회의록_양식.hwpx"
```

### 공식 파일명 생성

```powershell
python ".\meeting-minutes-koti\scripts\official_hwpx_name.py" `
  --input ".\recording_1_회의록.md" `
  --directory "."
```

파일명 규칙:

- `개최일시`에서 `YYMMDD` 추출
- `회의명`을 공식 제목으로 정리
- `YYMMDD - 회의제목 회의록.hwpx` 형식 사용

## 작성 기준

- 회의록은 녹취록 전문이 아니라 안건별 요약 보고형식으로 작성합니다.
- 문체는 `~함`, `~예정`, `~필요`, `~검토` 중심의 공무원 보고 문체로 정리합니다.
- 회의공지 메일은 일정과 계획 정보로 참고하되, 실제 논의와 결정 사항은 녹음 전사 내용을 우선합니다.
- 참석자, 일시, 장소가 불확실하면 임의 작성하지 않고 `확인 필요 사항`에 남깁니다.
- HWPX는 기존 `회의록_양식.hwpx`의 스타일과 표 구조를 유지합니다.
- 표 크기와 행 높이는 임의 조정하지 않습니다.
- 네모 글머리표와 하이픈 글머리표는 양식의 기존 역할 스타일을 적용합니다.
- 자간은 0, 줄간격은 양식 기준 160%를 유지합니다.

## 검증 방법

설치 후 skill 구조 검증:

```powershell
$env:PYTHONUTF8="1"
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" "$env:USERPROFILE\.codex\skills\meeting-minutes-koti"
```

생성된 HWPX 구조 검증:

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead(".\260522 - 온보딩 프로그램 회의록.hwpx")
$zip.Entries | Select-Object FullName
$zip.Dispose()
```
