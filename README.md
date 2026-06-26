# meeting-minutes-koti · 사용설명서

한국어 회의 **녹음 파일**과 **회의공지 메일(.eml)** 을 입력받아, 공무원 보고형식의 **회의록**을 작성하고 공식 한글 **HWPX 파일**까지 자동으로 생성하는 [Codex](https://developers.openai.com/codex) 스킬입니다.

> 녹음 → (로컬 Whisper) 전사 → 안건별 요약 회의록 초안 → `회의록_양식.hwpx` 채우기 → `YYMMDD - 회의제목 회의록.hwpx` 공식 파일 산출

---

## 목차

1. [무엇을 하는 스킬인가요](#무엇을-하는-스킬인가요)
2. [동작 흐름 한눈에 보기](#동작-흐름-한눈에-보기)
3. [필요 환경](#필요-환경)
4. [설치](#설치)
5. [빠른 시작](#빠른-시작)
6. [전체 워크플로우 (단계별)](#전체-워크플로우-단계별)
7. [스크립트 레퍼런스](#스크립트-레퍼런스)
8. [최종 산출물 규칙](#최종-산출물-규칙)
9. [작성 기준 (문체·내용 선별)](#작성-기준-문체내용-선별)
10. [HWPX 서식 규칙](#hwpx-서식-규칙)
11. [폴더 구조](#폴더-구조)
12. [문제 해결 (Troubleshooting)](#문제-해결-troubleshooting)
13. [자주 묻는 질문](#자주-묻는-질문)
14. [개인정보·보안 주의](#개인정보보안-주의)

---

## 무엇을 하는 스킬인가요

연구실·공공기관에서 회의 녹음을 받아 **사람이 직접 회의록을 타이핑하던 작업**을 자동화합니다.

- ✅ 한국어 회의 녹음을 **로컬 Whisper**로 전사 (외부 API에 음성을 보내지 않음)
- ✅ `.eml` 회의공지 메일에서 **회의명·일시·참석자·안건** 맥락 추출
- ✅ 잡담·인사·반복 발언을 걷어내고 **안건별 요약 보고형식**으로 정리
- ✅ 기존 `회의록_양식.hwpx`의 **표 구조와 스타일을 그대로 유지**한 채 내용 채우기
- ✅ `260522 - 온보딩 프로그램 회의록.hwpx` 형식의 **공식 파일명** 자동 생성

> ⚠️ 회의록은 **녹취록 전문이 아니라 안건별 요약**입니다. 전사 원문을 그대로 붙여 넣지 않습니다.

---

## 동작 흐름 한눈에 보기

```
[ 녹음 .mp3/.m4a/... ]                 [ 회의공지 .eml ]
          │                                    │
          ▼                                    ▼
 transcribe_local_whisper.py          parse_eml_notice.py
          │                                    │
          ▼                                    ▼
   *_전사.md (임시)                   회의공지_참고정보.md
          │                                    │
          └──────────────┬─────────────────────┘
                         ▼
            회의록 Markdown 초안 작성
         (report-style / template-fields 기준)
                         │
                         ▼
          minutes_md_to_hwpx_template.py
        (회의록_양식.hwpx 스타일 유지하며 채움)
                         │
                         ▼
            official_hwpx_name.py
                         │
                         ▼
     260522 - 온보딩 프로그램 회의록.hwpx  ← 최종 산출물
```

---

## 필요 환경

| 항목 | 요구사항 | 비고 |
| --- | --- | --- |
| **OS** | Windows (PowerShell 기준 예시) | macOS/Linux도 경로만 바꾸면 동작 |
| **Python** | 3.10 이상 | 필수 |
| **Codex** | 설치 및 실행 | 스킬 호출 환경 |
| **로컬 Whisper 전사** | `torch`, `transformers`, `huggingface_hub`, `imageio-ffmpeg`, `requests` | 녹음 전사를 쓸 때만 필요 |
| **HWPX 검증·fallback 변환** | Node.js + `kordoc` | 선택 사항 |

전사용 패키지 설치:

```powershell
python -m pip install torch transformers huggingface_hub imageio-ffmpeg requests
```

> Whisper 모델은 로컬 Hugging Face 캐시에서 로드합니다. 캐시에 없으면 스크립트가 Hugging Face Hub에서 자동으로 내려받습니다(최초 1회 네트워크 필요). 기본 모델은 `openai/whisper-small`이며 `--model`로 변경할 수 있습니다.

---

## 설치

1. 이 저장소를 내려받거나 클론합니다.

   ```powershell
   git clone https://github.com/Chiwooroh/meeting-minutes-koti-skill.git
   ```

2. `meeting-minutes-koti` 폴더를 Codex skill 폴더로 복사합니다.

   ```powershell
   Copy-Item -LiteralPath ".\meeting-minutes-koti" `
     -Destination "$env:USERPROFILE\.codex\skills\meeting-minutes-koti" -Recurse -Force
   ```

3. Codex를 다시 시작합니다.

4. (선택) 설치 구조를 검증합니다.

   ```powershell
   $env:PYTHONUTF8="1"
   python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" `
     "$env:USERPROFILE\.codex\skills\meeting-minutes-koti"
   ```

---

## 빠른 시작

회의 녹음(과 선택적으로 `.eml`)이 들어 있는 폴더에서 Codex에 다음과 같이 요청합니다.

```text
$meeting-minutes-koti 이 폴더 녹음 파일들로 파일당 1개씩 회의록 작성해줘
```

그러면 스킬이 전사 → 초안 → HWPX 생성 → 공식 파일명 변경 → 임시파일 정리까지 진행합니다.
최종적으로 작업 폴더에는 원본 파일과 `회의공지_참고정보.md`, 그리고 `YYMMDD - 회의제목 회의록.hwpx`만 남습니다.

---

## 전체 워크플로우 (단계별)

> 아래 예시는 작업 폴더에서 직접 스크립트를 실행하는 방법입니다. 보통은 Codex가 자동으로 호출하지만, 수동 실행·디버깅에 참고하세요. 경로는 설치 위치(`$env:USERPROFILE\.codex\skills\meeting-minutes-koti`)에 맞춰 조정합니다.

### 1. 입력 파일 확인

- 녹음: `.mp3`, `.m4a`, `.wav`, `.aac`, `.flac`, `.ogg`, `.webm`
- 회의공지 메일: `.eml`
- 양식: 작업 폴더에 `회의록_양식.hwpx`가 있으면 그것을, 없으면 번들된 `assets/회의록_양식.hwpx`를 사용

### 2. 녹음 전사 (로컬 Whisper)

```powershell
python "$env:USERPROFILE\.codex\skills\meeting-minutes-koti\scripts\transcribe_local_whisper.py" `
  --out ".\recording_1_전사.md" `
  ".\recording_1.mp3"
```

> `torch`/`transformers`/`huggingface_hub`/`imageio-ffmpeg`가 없거나 모델을 내려받을 수 없으면 스크립트가 막힌 원인을 명확히 보고합니다. 전사 내용을 임의로 지어내지 않습니다.

### 3. 회의공지 메일 파싱 (.eml이 있을 때)

```powershell
python "$env:USERPROFILE\.codex\skills\meeting-minutes-koti\scripts\parse_eml_notice.py" `
  --out ".\회의공지_참고정보.md" `
  ".\notice.eml"
```

공지 메일은 **계획 정보(맥락)** 로만 사용하고, 실제 논의·결정은 전사 내용을 우선합니다. 충돌 시 초안의 `확인 필요 사항`에 표시합니다.

### 4. 회의록 Markdown 초안 작성

녹음 1개당 회의록 Markdown 1개를 작성합니다. 기준 문서:

- `references/report-style.md` — 문체·내용 선별 규칙
- `references/template-fields.md` — 목표 필드(과제명·회의명·개최일시·장소·참석인원·회의목적·회의내용)
- `references/email-notice.md` — `.eml` 반영 규칙

결정·요청·쟁점·일정·담당·후속조치는 남기고, 잡담·반복 인사는 제외합니다. 불확실한 이름/안 들리는 구간은 `[확인 필요: ...]`로 표시합니다.

### 5. HWPX 양식 채우기

```powershell
python "$env:USERPROFILE\.codex\skills\meeting-minutes-koti\scripts\minutes_md_to_hwpx_template.py" `
  --template ".\회의록_양식.hwpx" `
  --input ".\recording_1_회의록.md" `
  --output ".\recording_1_회의록_작업본.hwpx" `
  --style-reference ".\회의록_양식.hwpx"
```

### 6. 공식 파일명 생성·적용

```powershell
python "$env:USERPROFILE\.codex\skills\meeting-minutes-koti\scripts\official_hwpx_name.py" `
  --input ".\recording_1_회의록.md" `
  --directory "."
```

생성된 공식 파일명으로 검증된 HWPX의 이름을 바꿉니다.

### 7. 검증 및 정리

- 각 최종 `.hwpx`가 유효한 ZIP/HWPX 패키지인지 확인
- 전사 파일, Markdown 초안, DOCX, 검증 추출본, 비최종 HWPX 등 **임시파일 삭제**
- 원본 `.mp3`/`.eml`은 사용자가 명시적으로 요청하지 않는 한 삭제하지 않음

HWPX 구조 검증 예시:

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead(".\260522 - 온보딩 프로그램 회의록.hwpx")
$zip.Entries | Select-Object FullName
$zip.Dispose()
```

---

## 스크립트 레퍼런스

| 스크립트 | 역할 | 주요 인자 |
| --- | --- | --- |
| `transcribe_local_whisper.py` | 로컬 Whisper로 음성 전사 → Markdown | `audio...`(위치인자, 1개 이상) · `--out`(필수) · `--model`(기본 `openai/whisper-small`) · `--language`(기본 `korean`) |
| `parse_eml_notice.py` | `.eml`에서 제목·발신/수신·발송일·첨부·본문 추출 | `eml...`(위치인자, 1개 이상) · `--out`(필수) |
| `minutes_md_to_hwpx_template.py` | Markdown 초안을 `회의록_양식.hwpx`에 채움 | `--template`(필수) · `--input`(필수) · `--output`(필수) · `--style-reference`(선택) |
| `official_hwpx_name.py` | 초안 필드로 공식 파일명 산출 | `--input`(필수) · `--directory`(선택) · `--folder-hint`(선택) |
| `minutes_md_to_docx.py` | (레거시) Word DOCX 출력 | `--template`(필수) · `--input`(필수) · `--output`(필수) — 사용자가 DOCX를 명시 요청할 때만 |
| `markdown_to_hwpx.mjs` | (fallback) `kordoc` 기반 Markdown→HWPX 변환 | `node markdown_to_hwpx.mjs <input.md> <output.hwpx>` |

### kordoc로 HWPX 확인 (선택)

```powershell
npx --yes --package kordoc --package pdfjs-dist kordoc ".\final.hwpx"
```

> 공식 양식이 있을 때는 항상 양식-채우기 스크립트(`minutes_md_to_hwpx_template.py`)를 우선합니다. `markdown_to_hwpx.mjs`는 양식 없이 변환해야 하는 fallback 용도입니다.

---

## 최종 산출물 규칙

작업 폴더에는 원칙적으로 다음만 남깁니다.

```text
회의공지_참고정보.md            # .eml 공지가 있을 때
YYMMDD - 회의제목 회의록.hwpx   # 녹음 1개당 1개
```

**파일명 규칙**

- 날짜: 초안의 `개최일시`에서 `YYMMDD` 추출
- 제목: `회의명` 사용, 반복되는 프로그램 접두어는 적절히 축약
- 형식: `YYMMDD - 회의제목 회의록.hwpx`
- 예: `260522 - 온보딩 프로그램 회의록.hwpx`
- Windows 금지 문자 제거: `< > : " / \ | ? *`

---

## 작성 기준 (문체·내용 선별)

- 문체는 `~함`, `~예정`, `~필요`, `~검토` 중심의 **공무원 보고 문체**
- 발화자별 대화록이 아니라 **안건별 논의 결과** 중심
- 반드시 반영: 회의 목적·주요 안건·쟁점, 합의/결정 사항, 담당 기관·담당자, 후속 조치, 일정, 법령·지침·과제명·예산/계약/일정 언급
- 제외·축약: 반복 발언, 의례적 인사, 안건 무관 사담, 말투/감탄사
- 참석자·일시·장소가 불확실하면 **임의 작성 금지** → `확인 필요 사항`에 기록
- `회의내용`은 안건별로 큰 글머리표(`□`)와 하위 글머리표(`-`)로 구성, 안건/결과를 먼저 쓰고 근거 논의는 뒤에

`회의내용` 기본 골격:

```markdown
□ 주요 안건명
- 핵심 논의 결과
  - 세부 근거 또는 보완 의견
  - 필요한 후속 조치
```

---

## HWPX 서식 규칙

- 기존 `회의록_양식.hwpx`의 레이아웃·스타일·표 구조를 **그대로 유지**
- 표 셀 내용은 **상단 정렬**
- 모든 생성 문단 줄간격 **160%** 유지
- 회의내용 행/표 높이는 고정값이 아니라 **실제 내용 길이에 맞게** 조정
- 표 텍스트 줄바꿈 허용 (긴 내용이 자연스럽게 늘어나도록)
- 임의의 새 스타일 생성 금지, 기존 역할 스타일만 적용
  - `□`/`❑`로 시작하는 줄 → 네모 글머리표 스타일
  - `-`로 시작하는 줄 → 하이픈 글머리표 스타일
  - 일반 텍스트 → 본문 스타일
- KoPub Dotum 등 양식 타이포그래피 유지
- **자간 0**(음수 자간 금지), 문단 `condense` 0 (강제 한 줄 압축 금지)
- 긴 회의내용 셀을 하단 정렬하지 않음

---

## 폴더 구조

```text
meeting-minutes-koti-skill/
├─ README.md                  # 이 사용설명서
├─ README_INSTALL.md          # 배포·설치 요약
└─ meeting-minutes-koti/      # ← Codex skills 폴더로 복사하는 스킬 본체
   ├─ SKILL.md                # 스킬 정의·워크플로우 (Codex가 읽음)
   ├─ assets/
   │  └─ 회의록_양식.hwpx      # 기본 HWPX 양식
   ├─ references/
   │  ├─ report-style.md      # 보고형 작성 기준
   │  ├─ template-fields.md   # 양식 필드 매핑
   │  ├─ email-notice.md      # .eml 반영 기준
   │  └─ template-extracted.md
   └─ scripts/
      ├─ transcribe_local_whisper.py
      ├─ parse_eml_notice.py
      ├─ minutes_md_to_hwpx_template.py
      ├─ official_hwpx_name.py
      ├─ minutes_md_to_docx.py
      └─ markdown_to_hwpx.mjs
```

---

## 문제 해결 (Troubleshooting)

| 증상 | 원인 / 해결 |
| --- | --- |
| 전사 스크립트가 import 에러로 멈춤 | `torch transformers huggingface_hub imageio-ffmpeg requests` 미설치 → 위 설치 명령 실행 |
| 모델 다운로드 실패 | 최초 실행 시 네트워크 필요. 사내망/프록시 환경이면 Hugging Face 접근 가능 여부 확인 |
| 한글이 깨져 보임 | PowerShell에서 `$env:PYTHONUTF8="1"` 설정 후 재실행 |
| 파일명에 `날짜확인`이 들어감 | 초안의 `개최일시`에서 날짜를 못 찾음 → 초안에 `YYYY-MM-DD` 형태 날짜 명시 또는 `--folder-hint`로 날짜 포함 폴더명 전달 |
| HWPX가 한글에서 안 열림 | ZIP 구조 검증(위 PowerShell 예시)으로 패키지 유효성 확인, 양식 파일 손상 여부 점검 |
| 표/줄간격이 양식과 다름 | `--style-reference`에 원본 `회의록_양식.hwpx`를 지정했는지 확인 |

---

## 자주 묻는 질문

**Q. 음성이 외부로 전송되나요?**
A. 아니요. 전사는 로컬 Whisper로 수행합니다. 단, 모델이 캐시에 없으면 **모델 파일**만 Hugging Face Hub에서 내려받습니다(음성은 전송하지 않음).

**Q. 녹음 여러 개를 한 번에 처리할 수 있나요?**
A. 네. 녹음 1개당 회의록 1개를 생성하는 것이 기본 동작입니다.

**Q. DOCX(Word)로도 받을 수 있나요?**
A. 사용자가 명시적으로 요청하면 `minutes_md_to_docx.py`(레거시)로 DOCX를 생성할 수 있습니다. 기본 산출물은 HWPX입니다.

**Q. 다른 회의록 양식을 쓰고 싶어요.**
A. 작업 폴더에 직접 `회의록_양식.hwpx`를 두면 번들 양식 대신 그 양식을 사용합니다.

---

## 개인정보·보안 주의

- 회의 녹음·전사·회의록에는 **개인정보와 비공개 업무 내용**이 포함될 수 있습니다. 산출물 공유 범위에 유의하세요.
- `transcribe_local_whisper.py`는 일부 사내망 환경을 고려해 모델 다운로드 시 **SSL 인증서 검증을 비활성화**(`session.verify = False`)합니다. 보안 정책에 민감한 환경이라면 이 동작을 검토·수정 후 사용하세요.
- 스크립트 예시 경로의 `KOTI`(사용자 폴더명)는 환경에 맞게 바꾸세요. 설치 안내는 `$env:USERPROFILE` 기준 일반 경로를 사용합니다.

---

> 이 저장소는 회의록 자동화 **Codex 스킬**과 그 사용설명서를 담고 있습니다. 스킬 본체는 `meeting-minutes-koti/` 폴더입니다.
