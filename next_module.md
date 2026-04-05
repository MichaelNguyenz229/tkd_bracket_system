## PROJECT

Standalone bracket visualization web app for Taekwondo tournaments.
Separate from the pipeline system — this is purely a display + interaction product.

**Stack:** React + TypeScript, Vite, Tailwind CSS, @dnd-kit/core
**Runtime:** Node / npm (or bun)

---

## WHAT THIS DOES

Ingests bracket data (JSON) and renders a double-sided single-elimination bracket
(competitors enter from both the left and right sides, converging toward a champion
slot in the center). Supports drag-and-drop seat swapping, custom athlete photos,
and a custom background image.

---

## INPUT DATA FORMAT

The app accepts JSON exported from the AAU tournament pipeline (`tkd_bracket_system`).

### Single division file (exported via "Export This Division")

```json
{
  "division": "World Class Cadets - Female Under 33 (Over 29 kg & not exceeding 33 kg) Black Belt",
  "competitors": [
    { "id": "1", "name": "Alice Kim",   "school": "Tigers ATA", "photoUrl": "" },
    { "id": "2", "name": "Bob Lee",     "school": "Dragon TKD", "photoUrl": "" },
    { "id": "3", "name": "Carol Park",  "school": "Elite TKD",  "photoUrl": "" }
  ]
}
```

### Multi-division file (exported via "Export All Divisions")

A JSON array of division objects, same shape as above:

```json
[
  { "division": "...", "competitors": [ ... ] },
  { "division": "...", "competitors": [ ... ] }
]
```

### Field descriptions

| Field | Type | Description |
|-------|------|-------------|
| `division` | string | Full division name including weight class and belt rank. Always ends with "Black Belt". |
| `competitors` | array | Ordered list of competitors in the division. Order is by weight ascending (lightest first). |
| `competitors[].id` | string | Sequential ID within the division (starting at "1"). Only unique within a single division, not globally. |
| `competitors[].name` | string | Athlete's full name. |
| `competitors[].school` | string | School/gym name. May be empty if not provided in registration. |
| `competitors[].photoUrl` | string | Always empty from the pipeline — the bracket app should let users upload/assign photos. |

### Notes
- There is **no seeding** — competitor order is by weight but has no competitive seeding meaning. The bracket app should support drag-and-drop reordering.
- Only **black belt divisions** are exported. Color belt divisions are excluded.
- A division can have any number of competitors (including 1). The bracket app should handle odd numbers with BYEs.
