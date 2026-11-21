---
title: The Hertzsprung–Russell diagram
subtitle: One chart of brightness against temperature tells a star's whole life
byline: Northern Observatory, Thursday night lectures
orientation: landscape
paper: a1
columns: 4
---

## Key figures {.stats}

| Value | Label |
|---|---|
| 90 % | Of stars are on the main sequence |
| 2,500–40,000 K | Surface temperatures of stars |
| 1/10,000 – 1,000,000 | Luminosity, in Suns |
| 1911–13 | Hertzsprung and Russell draw it |

## Introduction {.abstract}

Plot each star's luminosity against its surface temperature, hottest on the left, and the stars do not scatter at random. Nine in ten fall on one diagonal band, the main sequence; the rest gather in a few small groups: giants, supergiants and white dwarfs. Where a star sits tells its size, its mass, its age and its fate. No other single chart explains so much of astronomy, and this poster shows how to read it.

## 1. The diagram: tonight's stars {.wide}

```vega-lite width=50%
{
 "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
 "width": 1900,
 "height": 900,
 "background": "#0b1224",
 "config": {
  "view": {
   "stroke": "#1d2a4a"
  },
  "font": "Lato, Arial, sans-serif",
  "axis": {
   "labelColor": "#c9d4ea",
   "titleColor": "#e8edf7",
   "gridColor": "#16213f",
   "domainColor": "#3a4a74",
   "tickColor": "#3a4a74",
   "labelFontSize": 15,
   "titleFontSize": 17,
   "titlePadding": 14
  }
 },
 "layer": [
  {
   "data": {
    "values": [
     {
      "region": "Main sequence",
      "T": 42000,
      "L": 75000.0,
      "L2": 1200000.0
     },
     {
      "region": "Main sequence",
      "T": 30000,
      "L": 12500.0,
      "L2": 200000.0
     },
     {
      "region": "Main sequence",
      "T": 20000,
      "L": 750.0,
      "L2": 12000.0
     },
     {
      "region": "Main sequence",
      "T": 15000,
      "L": 175.0,
      "L2": 2800
     },
     {
      "region": "Main sequence",
      "T": 10000,
      "L": 12.5,
      "L2": 200
     },
     {
      "region": "Main sequence",
      "T": 8000,
      "L": 2.75,
      "L2": 44
     },
     {
      "region": "Main sequence",
      "T": 7000,
      "L": 1.125,
      "L2": 18.0
     },
     {
      "region": "Main sequence",
      "T": 6000,
      "L": 0.325,
      "L2": 5.2
     },
     {
      "region": "Main sequence",
      "T": 5000,
      "L": 0.105,
      "L2": 1.68
     },
     {
      "region": "Main sequence",
      "T": 4000,
      "L": 0.0225,
      "L2": 0.36
     },
     {
      "region": "Main sequence",
      "T": 3500,
      "L": 0.0075,
      "L2": 0.12
     },
     {
      "region": "Main sequence",
      "T": 3000,
      "L": 0.00125,
      "L2": 0.02
     },
     {
      "region": "Main sequence",
      "T": 2500,
      "L": 0.00015,
      "L2": 0.0024
     },
     {
      "region": "Giants",
      "T": 5800,
      "L": 18,
      "L2": 120
     },
     {
      "region": "Giants",
      "T": 5000,
      "L": 25,
      "L2": 260
     },
     {
      "region": "Giants",
      "T": 4500,
      "L": 35,
      "L2": 500
     },
     {
      "region": "Giants",
      "T": 4000,
      "L": 60,
      "L2": 1200
     },
     {
      "region": "Giants",
      "T": 3500,
      "L": 140,
      "L2": 2600
     },
     {
      "region": "Giants",
      "T": 3100,
      "L": 300,
      "L2": 3500
     },
     {
      "region": "Supergiants",
      "T": 35000,
      "L": 30000.0,
      "L2": 1200000.0
     },
     {
      "region": "Supergiants",
      "T": 20000,
      "L": 20000.0,
      "L2": 900000.0
     },
     {
      "region": "Supergiants",
      "T": 10000,
      "L": 12000.0,
      "L2": 700000.0
     },
     {
      "region": "Supergiants",
      "T": 6000,
      "L": 10000.0,
      "L2": 600000.0
     },
     {
      "region": "Supergiants",
      "T": 3000,
      "L": 15000.0,
      "L2": 600000.0
     },
     {
      "region": "White dwarfs",
      "T": 35000,
      "L": 0.03,
      "L2": 0.4
     },
     {
      "region": "White dwarfs",
      "T": 25000,
      "L": 0.01,
      "L2": 0.12
     },
     {
      "region": "White dwarfs",
      "T": 15000,
      "L": 0.0015,
      "L2": 0.02
     },
     {
      "region": "White dwarfs",
      "T": 10000,
      "L": 0.0004,
      "L2": 0.005
     },
     {
      "region": "White dwarfs",
      "T": 7000,
      "L": 8e-05,
      "L2": 0.0012
     },
     {
      "region": "White dwarfs",
      "T": 5000,
      "L": 2e-05,
      "L2": 0.0003
     }
    ]
   },
   "mark": {
    "type": "area",
    "interpolate": "monotone",
    "opacity": 0.22
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "y2": {
     "field": "L2"
    },
    "detail": {
     "field": "region"
    },
    "color": {
     "field": "region",
     "type": "nominal",
     "legend": null,
     "scale": {
      "domain": [
       "Main sequence",
       "Giants",
       "Supergiants",
       "White dwarfs"
      ],
      "range": [
       "#8fb3ff",
       "#ffb25e",
       "#ff7a6b",
       "#cfd8ea"
      ]
     }
    }
   }
  },
  {
   "data": {
    "values": [
     {
      "t": "O",
      "T": 37000,
      "L": 2.4e-05
     },
     {
      "t": "B",
      "T": 18000,
      "L": 2.4e-05
     },
     {
      "t": "A",
      "T": 8800,
      "L": 2.4e-05
     },
     {
      "t": "F",
      "T": 6700,
      "L": 2.4e-05
     },
     {
      "t": "G",
      "T": 5500,
      "L": 2.4e-05
     },
     {
      "t": "K",
      "T": 4400,
      "L": 2.4e-05
     },
     {
      "t": "M",
      "T": 3100,
      "L": 2.4e-05
     }
    ]
   },
   "mark": {
    "type": "text",
    "fontSize": 26,
    "fontWeight": "bold",
    "baseline": "middle"
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "text": {
     "field": "t"
    },
    "color": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "domain": [
       2500,
       3500,
       4500,
       5500,
       6500,
       8000,
       11000,
       20000,
       40000
      ],
      "range": [
       "#ff4a2e",
       "#ff7f3f",
       "#ffad5c",
       "#ffd98a",
       "#fff4d6",
       "#f4f6ff",
       "#c9d9ff",
       "#9bbcff",
       "#7ba5ff"
      ]
     },
     "legend": null
    }
   }
  },
  {
   "data": {
    "values": [
     {
      "t": "SUPERGIANTS",
      "T": 9000,
      "L": 1300000.0,
      "s": 30,
      "a": 0
     },
     {
      "t": "GIANTS",
      "T": 4300,
      "L": 9,
      "s": 30,
      "a": 0
     },
     {
      "t": "MAIN SEQUENCE",
      "T": 17000,
      "L": 15,
      "s": 30,
      "a": -27
     },
     {
      "t": "WHITE DWARFS",
      "T": 26000,
      "L": 0.0012,
      "s": 30,
      "a": -16
     }
    ]
   },
   "mark": {
    "type": "text",
    "fontWeight": "bold",
    "opacity": 0.9,
    "color": "#ffffff",
    "letterSpacing": 2
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "text": {
     "field": "t"
    },
    "size": {
     "field": "s",
     "type": "quantitative",
     "scale": null
    },
    "angle": {
     "field": "a",
     "type": "quantitative",
     "scale": null
    }
   }
  },
  {
   "data": {
    "values": [
     {
      "t": "hot and bright",
      "T": 40000,
      "L": 1600000.0,
      "align": "left"
     },
     {
      "t": "cool but bright: large",
      "T": 2300,
      "L": 1600000.0,
      "align": "right"
     },
     {
      "t": "hot but dim: small",
      "T": 40000,
      "L": 0.00013,
      "align": "left"
     },
     {
      "t": "cool and dim",
      "T": 2300,
      "L": 0.00013,
      "align": "right"
     }
    ]
   },
   "transform": [
    {
     "filter": "datum.align == 'left'"
    }
   ],
   "mark": {
    "type": "text",
    "fontSize": 16,
    "fontStyle": "italic",
    "color": "#8ea0c4",
    "align": "left",
    "baseline": "middle"
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "text": {
     "field": "t"
    }
   }
  },
  {
   "data": {
    "values": [
     {
      "t": "hot and bright",
      "T": 40000,
      "L": 1600000.0,
      "align": "left"
     },
     {
      "t": "cool but bright: large",
      "T": 2300,
      "L": 1600000.0,
      "align": "right"
     },
     {
      "t": "hot but dim: small",
      "T": 40000,
      "L": 0.00013,
      "align": "left"
     },
     {
      "t": "cool and dim",
      "T": 2300,
      "L": 0.00013,
      "align": "right"
     }
    ]
   },
   "transform": [
    {
     "filter": "datum.align == 'right'"
    }
   ],
   "mark": {
    "type": "text",
    "fontSize": 16,
    "fontStyle": "italic",
    "color": "#8ea0c4",
    "align": "right",
    "baseline": "middle"
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "text": {
     "field": "t"
    }
   }
  },
  {
   "data": {
    "name": "stars"
   },
   "transform": [
    {
     "calculate": "36 + 34 * (log(datum.L) / LN10 + 4)",
     "as": "size"
    }
   ],
   "mark": {
    "type": "circle",
    "opacity": 0.28
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "size": {
     "field": "size",
     "type": "quantitative",
     "scale": {
      "type": "linear",
      "range": [
       140,
       900
      ]
     },
     "legend": null
    },
    "color": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "domain": [
       2500,
       3500,
       4500,
       5500,
       6500,
       8000,
       11000,
       20000,
       40000
      ],
      "range": [
       "#ff4a2e",
       "#ff7f3f",
       "#ffad5c",
       "#ffd98a",
       "#fff4d6",
       "#f4f6ff",
       "#c9d9ff",
       "#9bbcff",
       "#7ba5ff"
      ]
     },
     "legend": null
    }
   }
  },
  {
   "data": {
    "name": "stars"
   },
   "transform": [
    {
     "calculate": "36 + 34 * (log(datum.L) / LN10 + 4)",
     "as": "size"
    }
   ],
   "mark": {
    "type": "circle",
    "opacity": 1,
    "stroke": "#ffffff",
    "strokeWidth": 0.6
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "size": {
     "field": "size",
     "type": "quantitative",
     "scale": {
      "type": "linear",
      "range": [
       30,
       190
      ]
     },
     "legend": null
    },
    "color": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "domain": [
       2500,
       3500,
       4500,
       5500,
       6500,
       8000,
       11000,
       20000,
       40000
      ],
      "range": [
       "#ff4a2e",
       "#ff7f3f",
       "#ffad5c",
       "#ffd98a",
       "#fff4d6",
       "#f4f6ff",
       "#c9d9ff",
       "#9bbcff",
       "#7ba5ff"
      ]
     },
     "legend": null
    }
   }
  },
  {
   "data": {
    "name": "stars"
   },
   "transform": [
    {
     "filter": "datum.side > 0"
    }
   ],
   "mark": {
    "type": "text",
    "align": "left",
    "dx": 13,
    "fontSize": 15,
    "color": "#e8edf7",
    "fontStyle": "italic"
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "text": {
     "field": "name"
    }
   }
  },
  {
   "data": {
    "name": "stars"
   },
   "transform": [
    {
     "filter": "datum.side < 0"
    }
   ],
   "mark": {
    "type": "text",
    "align": "right",
    "dx": -13,
    "fontSize": 15,
    "color": "#e8edf7",
    "fontStyle": "italic"
   },
   "encoding": {
    "x": {
     "field": "T",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       45000,
       2000
      ],
      "nice": false
     },
     "axis": {
      "values": [
       40000,
       20000,
       10000,
       6000,
       4000,
       3000,
       2000
      ],
      "format": ",",
      "title": "Surface temperature (K), hottest on the left"
     }
    },
    "y": {
     "field": "L",
     "type": "quantitative",
     "scale": {
      "type": "log",
      "domain": [
       1e-05,
       3000000.0
      ],
      "nice": false
     },
     "axis": {
      "values": [
       0.0001,
       0.01,
       1,
       100,
       10000.0,
       1000000.0
      ],
      "title": "Luminosity (Sun = 1)",
      "labelExpr": "datum.value >= 1 ? format(datum.value, ',') : '1/' + format(1 / datum.value, ',')"
     }
    },
    "text": {
     "field": "name"
    }
   }
  }
 ],
 "datasets": {
  "stars": [
   {
    "name": "Rigel",
    "T": 12100,
    "L": 120000,
    "side": 1
   },
   {
    "name": "Deneb",
    "T": 8500,
    "L": 200000,
    "side": 1
   },
   {
    "name": "Polaris",
    "T": 6000,
    "L": 2500,
    "side": 1
   },
   {
    "name": "Betelgeuse",
    "T": 3600,
    "L": 120000,
    "side": -1
   },
   {
    "name": "Antares",
    "T": 3500,
    "L": 75000,
    "side": 1
   },
   {
    "name": "Spica",
    "T": 22400,
    "L": 20500,
    "side": 1
   },
   {
    "name": "Aldebaran",
    "T": 3900,
    "L": 440,
    "side": 1
   },
   {
    "name": "Arcturus",
    "T": 4300,
    "L": 170,
    "side": -1
   },
   {
    "name": "Capella",
    "T": 4970,
    "L": 79,
    "side": -1
   },
   {
    "name": "Pollux",
    "T": 4600,
    "L": 33,
    "side": 1
   },
   {
    "name": "Regulus",
    "T": 12500,
    "L": 290,
    "side": 1
   },
   {
    "name": "Vega",
    "T": 9600,
    "L": 40,
    "side": 1
   },
   {
    "name": "Sirius A",
    "T": 9940,
    "L": 25,
    "side": -1
   },
   {
    "name": "Altair",
    "T": 7700,
    "L": 10.6,
    "side": 1
   },
   {
    "name": "Procyon A",
    "T": 6530,
    "L": 6.9,
    "side": 1
   },
   {
    "name": "Sun",
    "T": 5772,
    "L": 1,
    "side": 1
   },
   {
    "name": "Alpha Centauri B",
    "T": 5260,
    "L": 0.5,
    "side": 1
   },
   {
    "name": "61 Cygni A",
    "T": 4400,
    "L": 0.15,
    "side": 1
   },
   {
    "name": "Barnard's Star",
    "T": 3130,
    "L": 0.0035,
    "side": 1
   },
   {
    "name": "Proxima Centauri",
    "T": 3040,
    "L": 0.0017,
    "side": 1
   },
   {
    "name": "Sirius B",
    "T": 25000,
    "L": 0.056,
    "side": 1
   },
   {
    "name": "40 Eridani B",
    "T": 16500,
    "L": 0.013,
    "side": 1
   },
   {
    "name": "Procyon B",
    "T": 7740,
    "L": 0.00049,
    "side": 1
   }
  ]
 }
}
```

Each dot is a star you can see from the observatory, coloured as it shines and larger the brighter it is. The bands show where stars of each kind fall; the letters along the bottom are the spectral classes, from hot blue O stars to cool red M dwarfs.

## 2. How to read it

The diagram has two axes and no time: every star is plotted as it is now.

```cards cols=1 style=label
Across | Surface temperature, from 40,000 K on the left to 2,500 K on the right. Astronomers also read it as colour or spectral class, O B A F G K M
Up | Luminosity: the light a star gives out in all, compared with the Sun. Each line of the grid is a hundred times brighter than the one below
Corners | Hot and bright stars are top left, cool and dim bottom right. A cool star can only be bright if it is huge, and a hot star dim if it is tiny
```

```equation
title: Stefan–Boltzmann: brightness, size and temperature
L = 4 \pi R^2 \sigma T^4
L | Luminosity | W
R | Radius of the star | m
\sigma | Stefan–Boltzmann constant | W m^{-2} K^{-4}
T | Surface temperature | K
So every point on the diagram also gives the star's size: the giants are large, the white dwarfs small.
```

## 3. The main sequence: why stars line up

A star spends 90 % of its life burning hydrogen into helium in its core. While it does, its mass alone sets how hot and how bright it is, so every hydrogen-burning star lies on one line: the main sequence.

| Class | Mass (Suns) | Temperature | Luminosity | Life on the sequence |
|---|---|---|---|---|
| O | 40 | 40,000 K | 300,000 | 4 million years |
| B | 6 | 18,000 K | 800 | 100 million years |
| A | 2 | 9,000 K | 20 | 1 billion years |
| G (Sun) | 1 | 5,800 K | 1 | 10 billion years |
| M | 0.2 | 3,200 K | 0.005 | Over a trillion years |

Brightness rises steeply with mass, about as $L \propto M^{3.5}$, so heavy stars burn their fuel thousands of times faster and die young. The red dwarfs at the bottom right will outlive the universe as it is today. Throughout, the core's fusion pushes out as hard as gravity pulls in; when the hydrogen runs out, the balance fails and the star leaves the sequence.

## 4. Giants and supergiants: old and swollen

When the hydrogen in its core runs out, a star swells and cools. It moves up and to the right, off the main sequence, into the giants. The heaviest stars become supergiants, hundreds of times the Sun's size.

```sizes shape=circle nested=yes unit=" R☉"
Betelgeuse | 760 | Red supergiant | red
Aldebaran | 45 | Red giant | amber
Sirius A | 1.7 | Main sequence | blue
Sun | 1 | Main sequence | spark
```

Betelgeuse in place of the Sun would swallow the orbit of Jupiter.

## 5. White dwarfs: the embers

Bottom left are stars as hot as the main sequence's blue stars but ten thousand times dimmer, because they are tiny.

```highlight
Earth-sized | Sirius B, the nearest white dwarf | Its mass is the Sun's, squeezed into the Earth's size | second
1 tonne | A teaspoon of white dwarf | No fusion left: it only cools, slowly, for billions of years | brand
```

A white dwarf is the bare core of a star like the Sun, left when the giant puffed its outer layers away. It slides down the diagram to the right as it cools. No white dwarf can be heavier than 1.4 Suns, the Chandrasekhar limit: above it, gravity crushes even the electrons, and the core collapses to a neutron star.

## 6. A star's life: a journey across the diagram

```flow
[Nebula|grey] -collapse-> [Main sequence|brand] -hydrogen gone-> [Red giant|amber] -outer layers drift off-> [White dwarf|second]
[Red giant|amber] -above 8 Suns-> [Supergiant|red] -core collapses-> [Supernova|spark]
[Supernova|spark] -> [Neutron star or black hole]
```

The diagram shows where a star is now, but every star moves across it. The Sun has been on the main sequence for 4.6 billion years and has about 5 billion to go; then it will climb to the giants and end as a white dwarf.

When a star like the Sun leaves the giants, its outer layers drift away as a glowing shell, a planetary nebula such as the Ring Nebula in Lyra, and the bare core is left as a white dwarf.

> [!NOTE]
> As the Sun swells into a red giant it will grow past the orbit of Venus. The Earth may escape being swallowed, but its oceans will have boiled away long before.

## 7. Colour is temperature

```spectrum mode=stellar
```

A star's colour is set by its surface temperature, as with a heated poker: red at 3,000 K, yellow-white at 6,000 K, blue above 20,000 K. The spectral classes O B A F G K M were first sorted by the lines in starlight, and only later found to be a temperature scale.

See it for yourself tonight in Orion: Betelgeuse, at the top left of the constellation, is a red supergiant at 3,600 K; Rigel, bottom right, is a blue supergiant at 12,000 K. Astronomers measure the colour as the difference in a star's brightness through a blue and a yellow filter, its colour index. They are about as bright as each other, so they sit at the same height at opposite ends of the diagram.

## 8. Why it matters

```cards cols=2 style=top
Weighs stars | A main-sequence star's place gives its mass, for stars too far away to see an orbit | brand
Measures distance | Its class gives how bright it really is; how faint it looks then gives its distance | second
Dates clusters | All stars of a cluster are born together. The heaviest leave the sequence first, so the turn-off point gives the cluster's age | spark
Tests physics | The shape of the sequence matched the theory of fusion in the 1930s, and still checks models of stars | green
```

Plot a cluster such as the Pleiades and its main sequence stops at blue stars a few times the Sun's mass: it is about 100 million years old. An old globular cluster turns off near the Sun: 12 billion years.

Distances work the same way. Sirius's spectrum says it is an A star on the main sequence, so it gives out about 25 Suns of light. How faint it looks from here then puts it at 8.6 light years, which the shift of its position over a year confirms.

> [!TIP]
> Try it with binoculars: the Pleiades, high in the east on winter evenings, show a dozen blue-white stars. Their bright blue colour alone says the cluster is young.

## 9. History: how the diagram was found

```timeline
1890s | Harvard | Fleming, Maury and Cannon sort 225,000 spectra | brand
1905 | Hertzsprung | Finds giant and dwarf stars of one colour | second
1913 | Russell | Plots the diagram for nearby stars | spark
1925 | Payne | Stars are mostly hydrogen | spark
1926 | Eddington | Explains the sequence by mass | brand
1939 | Bethe | Fusion powers the main sequence | second
```

Ejnar Hertzsprung, a Danish chemist turned astronomer, and Henry Norris Russell at Princeton drew the same diagram independently. It rested on the spectra classified at Harvard by Annie Jump Cannon and her colleagues, whose O B A F G K M order is still used.

In 1925 Cecilia Payne showed from the same spectra that stars are made almost entirely of hydrogen and helium, the fuel that the main sequence burns. Astronomers still remember the class order with "Oh Be A Fine Girl, Kiss Me", or any sentence of their own.

Today the Gaia spacecraft has measured the distance of over a billion stars, and its diagram of millions of them shows the main sequence, the giants and the white dwarfs as sharp as Russell could only have hoped.

## In short {.summary}

Where a star sits on the diagram says what it is now, and where it is going.

### The main sequence

Stars burning hydrogen, from hot heavy blue stars to cool light red dwarfs. Mass sets the place.

### Giants and supergiants

Old stars, cool but huge, in the top right.

### White dwarfs

The hot, faint embers of stars like the Sun, bottom left.
