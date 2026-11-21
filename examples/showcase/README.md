# Poster showcase

Nine posters, each for a made-up organisation with its own theme, colours, fonts and logo. They show what py-doc's poster blocks look like on a real subject, and how a brand is set up.

| Poster | Organisation | What it shows |
|---|---|---|
| `iot-device.md` | Nimbus Sensors | A pinout, a packet taken apart byte by byte, a power budget, a flash map, a sequence diagram |
| `weather-station.md` | Skyward Instruments | A wind rose, a gauge, pressure bands, the layers of the sky, a day of solar power |
| `quantum.md` | Quanta Institute (dark) | Equations with their symbols, a particle in a box, energy levels, an interferometer, the standard model |
| `hr-diagram.md` | Northern Observatory (dark) | The Hertzsprung–Russell diagram as a log–log scatter, star colours, sizes, the inside of a star, distances |
| `calculus.md` | Euler Academy | Derivatives and integrals: curves with tangents, a shaded area, rules as tables and equations |
| `glaciation.md` | Highland Geography Society | A glacier's budget, ice ages over time, erosion and deposition landforms, a field checklist |
| `solar-farm.md` | Sunfield Energy | A year of generation, a waterfall of the money, a day on a 24-hour dial, the site as a stack |
| `incident-response.md` | Sentinel Cyber | A bow-tie of a ransomware attack, a fault tree, the first hour as steps, a terminal |
| `genetics.md` | Helix Biolabs | Codons on a tape, the steps from gene to protein, mutation types as a Pareto chart |

```bash
py-doc poster                      # every poster, into build/posters
py-doc poster quantum --pdf        # one, and its one-page PDF
```

## How a brand is set up

Each organisation has a folder under `brands/` with a `theme.yml` and a `logo.svg`. The theme starts from a built-in one (`extends: default`, `dark` or `print`) and sets the colours, a palette for blocks (`brand`, `second`, `spark`), the fonts and the logo. `py-doc.yml` gives each poster its theme, header and footer, so the Markdown files hold only the words and the layout. Copy a brand folder to start your own.

## Filling the page

`poster: {fill: spread}` in `py-doc.yml` makes every column end level. Even so, a poster fills its page best when:

- **Each section is one idea with one picture.** The page shares whole sections between the columns, so two big pictures in one section leave a gap.
- **A busy landscape poster has four columns** (`columns: 4`), so pictures that grow with their column stay small.
- **The sections are in an order that adds up evenly.** The columns take the sections in order, so a long section beside two short ones balances best.
