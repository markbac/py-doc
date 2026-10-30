"""The periodic table: number, symbol, name, standard atomic weight and category of each element.

From the PubChem periodic table (public domain, US Government work). Weights are rounded to two decimals; an
element with no stable isotope has the mass number of its longest-lived isotope in brackets, as the table gives it.
"""

from __future__ import annotations

CATEGORIES = {  # category: colour of its tile
    "alkali metal": "#c0392b", "alkaline earth metal": "#e67e22", "transition metal": "#b9770e",
    "post-transition metal": "#7f8c8d", "metalloid": "#16a085", "nonmetal": "#27ae60", "halogen": "#2980b9",
    "noble gas": "#8e44ad", "lanthanide": "#d35400", "actinide": "#a04000",
}  # fmt: skip

# number symbol name weight category, one element a line
_TABLE = """
1 H Hydrogen 1.01 nonmetal
2 He Helium 4.00 noble gas
3 Li Lithium 6.94 alkali metal
4 Be Beryllium 9.01 alkaline earth metal
5 B Boron 10.81 metalloid
6 C Carbon 12.01 nonmetal
7 N Nitrogen 14.01 nonmetal
8 O Oxygen 16.00 nonmetal
9 F Fluorine 19.00 halogen
10 Ne Neon 20.18 noble gas
11 Na Sodium 22.99 alkali metal
12 Mg Magnesium 24.31 alkaline earth metal
13 Al Aluminium 26.98 post-transition metal
14 Si Silicon 28.09 metalloid
15 P Phosphorus 30.97 nonmetal
16 S Sulfur 32.06 nonmetal
17 Cl Chlorine 35.45 halogen
18 Ar Argon 39.95 noble gas
19 K Potassium 39.10 alkali metal
20 Ca Calcium 40.08 alkaline earth metal
21 Sc Scandium 44.96 transition metal
22 Ti Titanium 47.87 transition metal
23 V Vanadium 50.94 transition metal
24 Cr Chromium 52.00 transition metal
25 Mn Manganese 54.94 transition metal
26 Fe Iron 55.85 transition metal
27 Co Cobalt 58.93 transition metal
28 Ni Nickel 58.69 transition metal
29 Cu Copper 63.55 transition metal
30 Zn Zinc 65.38 transition metal
31 Ga Gallium 69.72 post-transition metal
32 Ge Germanium 72.63 metalloid
33 As Arsenic 74.92 metalloid
34 Se Selenium 78.97 nonmetal
35 Br Bromine 79.90 halogen
36 Kr Krypton 83.80 noble gas
37 Rb Rubidium 85.47 alkali metal
38 Sr Strontium 87.62 alkaline earth metal
39 Y Yttrium 88.91 transition metal
40 Zr Zirconium 91.22 transition metal
41 Nb Niobium 92.91 transition metal
42 Mo Molybdenum 95.95 transition metal
43 Tc Technetium [98] transition metal
44 Ru Ruthenium 101.07 transition metal
45 Rh Rhodium 102.91 transition metal
46 Pd Palladium 106.42 transition metal
47 Ag Silver 107.87 transition metal
48 Cd Cadmium 112.41 transition metal
49 In Indium 114.82 post-transition metal
50 Sn Tin 118.71 post-transition metal
51 Sb Antimony 121.76 metalloid
52 Te Tellurium 127.60 metalloid
53 I Iodine 126.90 halogen
54 Xe Xenon 131.29 noble gas
55 Cs Caesium 132.91 alkali metal
56 Ba Barium 137.33 alkaline earth metal
57 La Lanthanum 138.91 lanthanide
58 Ce Cerium 140.12 lanthanide
59 Pr Praseodymium 140.91 lanthanide
60 Nd Neodymium 144.24 lanthanide
61 Pm Promethium [145] lanthanide
62 Sm Samarium 150.36 lanthanide
63 Eu Europium 151.96 lanthanide
64 Gd Gadolinium 157.25 lanthanide
65 Tb Terbium 158.93 lanthanide
66 Dy Dysprosium 162.50 lanthanide
67 Ho Holmium 164.93 lanthanide
68 Er Erbium 167.26 lanthanide
69 Tm Thulium 168.93 lanthanide
70 Yb Ytterbium 173.05 lanthanide
71 Lu Lutetium 174.97 lanthanide
72 Hf Hafnium 178.49 transition metal
73 Ta Tantalum 180.95 transition metal
74 W Tungsten 183.84 transition metal
75 Re Rhenium 186.21 transition metal
76 Os Osmium 190.23 transition metal
77 Ir Iridium 192.22 transition metal
78 Pt Platinum 195.08 transition metal
79 Au Gold 196.97 transition metal
80 Hg Mercury 200.59 transition metal
81 Tl Thallium 204.38 post-transition metal
82 Pb Lead 207.2 post-transition metal
83 Bi Bismuth 208.98 post-transition metal
84 Po Polonium [209] post-transition metal
85 At Astatine [210] halogen
86 Rn Radon [222] noble gas
87 Fr Francium [223] alkali metal
88 Ra Radium [226] alkaline earth metal
89 Ac Actinium [227] actinide
90 Th Thorium 232.04 actinide
91 Pa Protactinium 231.04 actinide
92 U Uranium 238.03 actinide
93 Np Neptunium [237] actinide
94 Pu Plutonium [244] actinide
95 Am Americium [243] actinide
96 Cm Curium [247] actinide
97 Bk Berkelium [247] actinide
98 Cf Californium [251] actinide
99 Es Einsteinium [252] actinide
100 Fm Fermium [257] actinide
101 Md Mendelevium [258] actinide
102 No Nobelium [259] actinide
103 Lr Lawrencium [266] actinide
104 Rf Rutherfordium [267] transition metal
105 Db Dubnium [268] transition metal
106 Sg Seaborgium [269] transition metal
107 Bh Bohrium [270] transition metal
108 Hs Hassium [269] transition metal
109 Mt Meitnerium [278] transition metal
110 Ds Darmstadtium [281] transition metal
111 Rg Roentgenium [282] transition metal
112 Cn Copernicium [285] transition metal
113 Nh Nihonium [286] post-transition metal
114 Fl Flerovium [289] post-transition metal
115 Mc Moscovium [290] post-transition metal
116 Lv Livermorium [293] post-transition metal
117 Ts Tennessine [294] halogen
118 Og Oganesson [294] noble gas
"""


def _load():
    out = {}
    for line in _TABLE.strip().splitlines():
        number, symbol, name, weight, *category = line.split()
        out[symbol] = (int(number), symbol, name, weight, " ".join(category))
    return out


ELEMENTS = _load()
BY_NUMBER = {e[0]: e for e in ELEMENTS.values()}


# The ground-state electron configuration of each element: the subshells filled in Madelung's order (by n + l,
# then n), except for these, whose measured configurations differ (PubChem). Each is {"nl": electrons}.
_ORDER = sorted(((n, l) for n in range(1, 8) for l in range(4) if l < n), key=lambda s: (s[0] + s[1], s[0]))  # noqa: E741
_LETTERS = "spdf"
_EXCEPTIONS = {
    24: {"3d": 5, "4s": 1}, 29: {"3d": 10, "4s": 1}, 41: {"4d": 4, "5s": 1}, 42: {"4d": 5, "5s": 1},
    44: {"4d": 7, "5s": 1}, 45: {"4d": 8, "5s": 1}, 46: {"4d": 10, "5s": 0}, 47: {"4d": 10, "5s": 1},
    57: {"4f": 0, "5d": 1}, 58: {"4f": 1, "5d": 1}, 64: {"4f": 7, "5d": 1}, 78: {"5d": 9, "6s": 1},
    79: {"5d": 10, "6s": 1}, 89: {"5f": 0, "6d": 1}, 90: {"5f": 0, "6d": 2}, 91: {"5f": 2, "6d": 1},
    92: {"5f": 3, "6d": 1}, 93: {"5f": 4, "6d": 1}, 96: {"5f": 7, "6d": 1}, 103: {"6d": 0, "7p": 1},
}  # fmt: skip
_NOBLE = {2: "He", 10: "Ne", 18: "Ar", 36: "Kr", 54: "Xe", 86: "Rn"}


def configuration(z: int) -> dict[str, int]:
    """The electrons in each subshell of element ``z``, such as {"1s": 2, "2s": 2, "2p": 2} for carbon, in
    the order the subshells fill."""
    out, left = {}, z
    for n, l in _ORDER:  # noqa: E741
        if left <= 0:
            break
        take = min(left, 4 * l + 2)
        out[f"{n}{_LETTERS[l]}"] = take
        left -= take
    for subshell, count in _EXCEPTIONS.get(z, {}).items():
        out[subshell] = count
    return {name: count for name, count in out.items() if count}


def shells(z: int) -> list[int]:
    """The electrons in each shell of element ``z``, from the innermost: [2, 8, 4] for silicon."""
    counts = [0] * 7
    for subshell, count in configuration(z).items():
        counts[int(subshell[0]) - 1] += count
    return [count for count in counts if count] if z else []


def _superscript(number: int) -> str:
    return str(number).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))


def configuration_text(z: int) -> str:
    """The configuration of element ``z`` after the noble gas before it, as written: "[Ne] 3s² 3p²" for silicon,
    its subshells in order of n then l."""
    core = max((n for n in _NOBLE if n < z), default=0)
    inner = configuration(core) if core else {}
    rest = {name: count for name, count in configuration(z).items() if count != inner.get(name, 0)}
    parts = [
        f"{name}{_superscript(count)}"
        for name, count in sorted(rest.items(), key=lambda s: (s[0][0], _LETTERS.index(s[0][1])))
    ]
    return " ".join(([f"[{_NOBLE[core]}]"] if core else []) + parts)
