---
title: Quality requirements
---

# Quality requirements

## Reliability

| ID | Requirement | Priority | Status |
|---|---|---|---|
| QR-001 | py-doc shall never drop text, a picture or a setting quietly. What it cannot carry over is named in a warning, and what it cannot do is an error. | Must | Met |
| QR-002 | A failing tool shall stop the step with a non-zero exit status and the tool's whole output. Nothing shall be written as a stand-in for a picture or document that failed. | Must | Met |
| QR-003 | One failing document or file shall not stop the others in a batch: every failure is listed, then a summary, then exit status 1. | Must | Met |
| QR-004 | Exit statuses shall separate the environment (2) from a failed build or check (1). | Must | Met |

## Safety of the user's files

| ID | Requirement | Priority | Status |
|---|---|---|---|
| QR-020 | A build, export or site build shall change no source file. Only commands that exist to change project files (`init`, `import`, `migrate`, `site init`, `c4 up`) write into the project, and only what they say. | Must | Met |
| QR-021 | An existing file shall not be replaced unless the command is told to (`--force`, `--backup`), or the file is one py-doc wrote itself. | Must | Met |
| QR-022 | The input shall be checked before anything is created, so a typo leaves nothing behind. | Should | Met |

## Security

| ID | Requirement | Priority | Status |
|---|---|---|---|
| QR-040 | A tool shall run in a fresh container as the calling user, with no capabilities, no privilege escalation, no network unless the step needs it, and only the folders it needs, read-only unless it writes there. | Must | Met |
| QR-041 | Commands shall be argument lists, never shell strings built from user input. | Must | Met |
| QR-042 | Downloaded tools shall be checked against recorded SHA-256 checksums when the image is built. | Must | Met |
| QR-043 | Steps that change the machine (`py-doc setup`) shall show what they will run and ask first. | Must | Met |

## Reproducibility

| ID | Requirement | Priority | Status |
|---|---|---|---|
| QR-060 | The same sources and the same image shall give the same documents on Linux, Windows and CI. Tool versions are pinned, and the image tag follows its definition. | Must | Met |
| QR-061 | Generated text (C4 chapters, reports) shall be sorted and carry no times unless asked. | Should | Met |
| QR-062 | The Structurizr Local image can be pinned by digest. | Could | Met |

## Performance

| ID | Requirement | Priority | Status |
|---|---|---|---|
| QR-080 | Unchanged diagrams shall not be drawn again: pictures are cached by their text, format and tool image. | Should | Met |
| QR-081 | Unchanged Structurizr workspaces shall not be exported or drawn again. | Should | Met |
| QR-082 | The pages of a site shall be converted in one container run. | Could | Met |
| QR-083 | The full test suite shall finish without hanging on any supported platform. Tools that can block (such as a TeX package manager waiting for an answer) are given a time limit. | Must | Met |

## Usability

| ID | Requirement | Priority | Status |
|---|---|---|---|
| QR-100 | Every error shall say what is wrong, where (file, line, configuration key or view) and, where it can, what to do. | Must | Met |
| QR-101 | Long steps (building the image, starting Structurizr) shall show progress. | Should | Met |
| QR-102 | Old command and import names shall keep working, with a one-line note naming the replacement. | Should | Met |
| QR-103 | py-doc's own documentation shall be written, checked and built with py-doc. | Should | Met |

## Portability and maintainability

| ID | Requirement | Priority | Status |
|---|---|---|---|
| QR-120 | py-doc shall run on Linux and Windows with Python 3.10 to 3.14. | Must | Met |
| QR-121 | Each module shall have one job, and engine-specific code (MkDocs, Starlight, Structurizr) shall stay in its own module. | Should | Met |
| QR-122 | Every feature shall have tests, and the tests shall run without Docker by running the tools on the host or faking the engine. | Must | Met |
| QR-123 | The library shall use the standard `logging` module and never configure it. | Should | Met |
