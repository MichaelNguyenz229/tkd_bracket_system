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

The app accepts a JSON file with this shape:

```json
{
  "division": "World Class Seniors - Male",
  "competitors": [
    { "id": "1", "name": "Alice Kim",    "seed": 1, "school": "Tigers ATA", "photoUrl": "" },
    { "id": "2", "name": "Bob Lee",      "seed": 2, "school": "Dragon TKD", "photoUrl": "" },
    { "id": "3", "name": "Carol Park",   "seed": 3, "school": "Elite TKD",  "photoUrl": "" },
    { "id": "4", "name": "Dan Nguyen",   "seed": 4, "school": "AAU Club",   "photoUrl": "" }
  ]
}
