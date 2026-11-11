# SKIXG Hardware Integration and Enclosure Selection Report

**Date:** 2026-10-06  
**Scope:** Raspberry Pi 5, Raspberry Pi Codec Zero, Waveshare 7-inch touchscreen, tube-amplifier hardware, enclosure, and procurement

## Executive decision

Use the **Hammond 1456RL1BKBK sloped aluminum console** as the purchase candidate, subject to the mechanical gate below.

- Manufacturer part: `1456RL1BKBK`
- Newark part: `79AC5358`
- External size: 17.1 × 11.61 × 3.62 in on Newark; Hammond's nominal table is 17.00 in wide × 11.30 in deep × 3.50 in rear height × 1.50 in front height
- Material: 0.081 in (2 mm) aluminum for the case and the top panel at this size
- Construction: preassembled console with screw-fastened removable top, included hardware and rubber feet
- Cooling: factory vents on the rear and bottom
- Finish: black top and black case
- Rating: IP31
- Observed price and stock: **$61.77 each, 4 in stock at Newark on 2026-10-06**
- Project enclosure allowance: $85; nominal remaining allowance before tax/shipping is **$23.23**

The enclosure is a better match than a plain rectangular box because the sloped 17-inch panel provides a usable viewing angle and enough width for the 7-inch touchscreen plus six physical controls. The removable top also meets the service-access requirement.

**Do not release the purchase order until the final PCB, power-supply/transformer, large-resistor, and tube/socket envelopes pass the mechanical gate.** The current project package does not contain a final PCB outline or a dimensioned enclosure assembly drawing.

## Status of the enclosure drawings

No updated, dimensioned enclosure drawing was found in the supplied SKIXG records. The newest enclosure material is still planning-level:

- the WBS assigns “Design enclosure with mounting points” to Sudharshan;
- the consultation slides list Fusion 360, SolidWorks, KiCad StepUp, and local fabrication options but do not contain a final enclosure CAD model;
- the formal proposal reserves $85 for the enclosure and requires a metal, ventilated, accessible housing;
- the current BOM does not identify a manufacturer part number;
- the final PCB width, length, mounting holes, tallest component, power-supply/transformer dimensions, and large-resistor envelope are absent.

The Hammond manufacturer page provides 2D/3D CAD for the stock enclosure. Use that model as the base for the final assembly drawing after the purchase gate is passed.

## Why this enclosure fits the known hardware

| Assembly | Known envelope or interface | Fit conclusion |
| --- | --- | --- |
| Waveshare 70H-1024600-IPS-CT-B | Touch panel 173 × 103 × 4.2 mm; active area 154.2144 × 85.92 mm | Fits easily on the 17 × 11.3 in sloped panel with room on both sides for controls. |
| Raspberry Pi 5 | 85 × 56 mm PCB | Fits at the high/rear end of the console. |
| Codec Zero | pHAT mounted directly on Pi 40-pin header | Fits as a Pi/codec stack; reserve rear-height region and cable bend room. |
| Two 12AX7 tubes and sockets | Approximately 22 mm tube diameter and about 50 mm glass height, plus socket and lead clearance | Mechanically plausible only at the high/rear end. Confirm the actual socket-to-tube assembly height; use horizontal tube mounting or a taller enclosure if the vertical stack cannot maintain safe clearance. |
| Large power resistors | Final quantity, wattage, case size, and surface temperature not documented | Put near rear/bottom vents on nonflammable standoffs or a rated heatsink; purchase is gated on the final envelope and thermal plan. |
| Amplifier PCB / power supply | Final outline and tallest component not documented | Cannot be declared a guaranteed fit yet. The 17 × 11.3 in footprint is deliberately conservative, but must be checked in CAD. |

## Recommended panel layout

Use the removable sloped top as the user panel. A workable arrangement is:

```text
17-inch width
┌────────────────────────────────────────────────────────────┐
│  3 controls   [ 173 × 103 mm touch glass ]   3 controls  │
│                                                            │
│       Tube/analog zone       barrier       Pi/digital zone │
│       (rear/vent area)                     (rear/high area) │
└────────────────────────────────────────────────────────────┘
front: 1.5 in high                              rear: 3.5 in high
```

Screen fabrication guidance:

- Center the display on the sloped panel, not on a horizontal surface. Waveshare specifically warns against mounting this panel parallel to the ground without adequate retention.
- Start from the manufacturer's display CAD, not only the active-area dimensions.
- A nominal viewing window of about **155.0 × 86.7 mm** covers the active area while retaining bezel overlap, but this is a starting dimension—not a release dimension.
- The full 173 × 103 mm touch glass must be supported. Use a rear retaining frame plus thin closed-cell foam/VHB only on the non-active bezel; do not clamp the glass against a raw metal edge.
- Deburr the cutout and add edge protection. Dry-fit the actual display before final drilling.
- Place the six potentiometers in two vertical groups of three beside the screen, with final spacing based on knob diameter and wiring clearance.

Interior zoning:

- Keep the tube/high-voltage and hot-resistor zone separate from the Pi, Codec Zero, display adapter, HDMI, and USB cabling.
- Put the Pi/Codec Zero stack at the rear/high end so the stack and cable bends do not collide with the low front wall.
- Keep low-level audio wiring away from HDMI, USB, switched power, heater wiring, and the power-supply section.
- Keep the factory rear and bottom vents unobstructed; raise hot resistors above the base using rated standoffs and follow the resistor manufacturer's clearance/derating requirements.
- Do not use the display or Pi as an airflow baffle over the hot section.

## Exact Pi, codec, and touchscreen connections

### Codec Zero to Raspberry Pi 5

The Codec Zero plugs directly onto the Pi 5's 40-pin header. **Do not run separate loose I2S wires.** Use standoffs and install it only with power removed.

| Pi physical pin | BCM signal | Codec Zero use | Rule |
| ---: | --- | --- | --- |
| 1 and 17 | 3.3 V | Logic power | Reserved by the HAT. |
| 2 and 4 | 5 V | Board power rail | Reserved by the HAT; do not feed an unrelated supply into these pins. |
| 3 | GPIO2 / SDA1 | I2C control/data | Reserved. |
| 5 | GPIO3 / SCL1 | I2C clock | Reserved. |
| 6, 9, 14, 20, 25, 30, 34, 39 | Ground | Common digital/codec ground | Ground only; chassis bonding is handled separately. |
| 12 | GPIO18 / PCM_CLK | I2S bit clock | Reserved. |
| 35 | GPIO19 / PCM_FS | I2S frame/word select | Reserved. |
| 38 | GPIO20 / PCM_DIN | Codec-to-Pi audio data | Reserved. |
| 40 | GPIO21 / PCM_DOUT | Pi-to-codec audio data | Reserved. |
| 13 | GPIO27 | Codec Zero button | Do not reuse. |
| 16 | GPIO23 | Codec Zero LED | Do not reuse. |
| 18 | GPIO24 | Codec Zero LED | Do not reuse. |

Before wiring AUX IN or AUX OUT, verify the `L`, `R`, and `GND` order against the actual Codec Zero silkscreen/product drawing. Do not infer the order from connector position. Codec Zero's stereo auxiliary input is specified at up to 1 V RMS, so the tube-to-codec interface must enforce that limit under worst-case conditions.

### Touchscreen to Raspberry Pi 5

The Waveshare display does **not** connect to the Pi GPIO header for normal video/touch operation.

1. Connect the touch panel to the supplied Waveshare adapter with the supplied 40-pin FPC, pin 1 to pin 1.
2. Connect adapter `Display` (full-size HDMI) to either Pi 5 micro-HDMI port using a short micro-HDMI-to-HDMI cable.
3. Connect adapter `Touch` (USB) to one Pi USB port. This carries touch data and normally powers the adapter/display.
4. If separate display power is used during bring-up, it must be a regulated 5 V source within the Waveshare limits; do not connect it to the tube B+, heater, bias, or 50 V rail.
5. Do not hot-plug the display FPC.

The panel itself is specified for 5.00 V nominal, about 450–500 mA with the backlight on. The final 5 V supply must be sized for the Pi 5, Codec Zero, display, cooling, and USB loads with startup margin.

### Audio signal path

```text
Instrument input jack
  -> high-impedance input buffer
  -> tube stages
  -> AC-coupled, attenuated, protected line-level interface
  -> Codec Zero AUX IN
  -> Pi DSP
  -> Codec Zero AUX OUT
  -> reviewed output/interface stage
  -> line-output jack
```

Never connect tube B+, plate, grid-bias, heater, speaker-level, or an unverified tube-stage output directly to Codec Zero, GPIO, the display, or the Pi. AUX IN must be protected and demonstrated to remain within the codec input limits at worst-case signal level.

## Chassis safety requirements

- Bond protective earth to the metal chassis at a dedicated stud close to the AC inlet using a ring terminal and toothed/star washer on bare metal. Do not rely on paint, a removable cover, or PCB mounting screws for the safety bond.
- Use the approved fused/filtered inlet, strain relief, insulated mains terminals, and finger-safe covers required by the final power design.
- Keep mains/high-voltage wiring physically segregated from low-voltage digital and audio wiring.
- Bond removable metal panels as required by the safety review; verify continuity after painting and assembly.
- Add warning labels and prevent tool-less access to hazardous voltage.
- Perform protective-earth continuity, insulation, leakage, thermal, and enclosure-access tests before demonstration.

## Procurement and BOM decision

The capstone records require U.S.-based suppliers and the course purchase process requires a typed purchase order, an updated expenditure sheet, and advisor approval before purchase. They do not contain an authoritative vendor whitelist. Newark, Mouser, and DigiKey are U.S. distributors, but the advisor must still approve the selected supplier and PO.

Recommended BOM line:

| Category | Item | Manufacturer | MPN | Supplier / supplier PN | Qty | Unit cost | Extended | Status |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| Materials (BOM) | Sloped aluminum instrument enclosure | Hammond Manufacturing | `1456RL1BKBK` | Newark / `79AC5358` | 1 | $61.77 | $61.77 | Recommended; mechanical gate required before PO |

The prior placeholder was $85, so replacing it with the observed $61.77 price reduces the projected BOM from $525.00 to **$501.77** before tax and shipping.

The same row is recorded in `docs/BOM_ADDITIONS.csv`. The original editable `Budget.xlsx` was not present in the available workspace, so the source workbook itself could not be modified.

## Mechanical purchase gate

The enclosure may be ordered only after one person signs off each item:

- [ ] Final PCB outline, mounting-hole coordinates, connector keep-outs, and tallest component entered in CAD.
- [ ] Actual power-supply/transformer envelope and mounting method entered in CAD.
- [ ] Large resistor part numbers, case dimensions, dissipation, derating, and required clearances entered in CAD.
- [ ] Tube plus socket installed height/orientation and service-removal clearance entered in CAD.
- [ ] Pi + Codec Zero + cooler + standoff stack and HDMI/USB bend radii entered in CAD.
- [ ] Waveshare display CAD imported; window, retaining frame, and cable path checked.
- [ ] Six potentiometers/knobs, input/output jacks, power inlet, fuse, switch, and ventilation keep-outs placed.
- [ ] At least 10 mm general assembly clearance is maintained around removable modules, with larger safety/thermal spacing where required.
- [ ] Cover can be removed without disconnecting protective earth or placing cable tension on the display.
- [ ] Advisor confirms Newark is acceptable and approves the PO.

If the assembly fails because of tube/socket height, transformer height, or thermal clearance, move to a taller 5–6 inch metal enclosure rather than crowding high-voltage/hot parts into this console.

## Alternatives considered

| Candidate | Advantage | Reason not selected |
| --- | --- | --- |
| Hammond `1444-17134`, 17 × 13 × 4 in aluminum chassis | Large flat internal footprint and easy machining | Chassis is not as presentation-ready; a compatible secured cover/face solution must be specified separately, weakening the cost and access advantage. |
| Hammond 1458 vented steel instrument cases | Strong, vented, screw-assembled steel construction | Common stocked 5-inch-tall variants are only about 8 × 10 or 10 × 8 in, leaving inadequate panel space for the display plus six controls. |
| Custom local fabrication | Exact fit and local support | No final mechanical drawing exists; custom fabrication now would lock in unknown PCB and power-component dimensions and is likely to exceed the $85 allowance. |

## Sources

- [Hammond 1456 series manufacturer page](https://www.hammfg.com/electronics/small-case/general-purpose/1456)
- [Newark 1456RL1BKBK listing](https://www.newark.com/hammond/1456rl1bkbk/enclosure-instrument-alum-black/dp/79AC5358)
- [DigiKey 1456RL1BKBK listing](https://www.digikey.com/en/products/detail/hammond-manufacturing/1456RL1BKBK/9991586)
- [Mouser 1456RL1BKBK listing](https://www.mouser.com/ProductDetail/Hammond-Manufacturing/1456RL1BKBK)
- [Waveshare 70H-1024600 technical wiki](https://www.waveshare.com/wiki/70H-1024600)
- [Raspberry Pi 5 mechanical drawing](https://pip.raspberrypi.com/documents/RP-008347-DS-1-raspberry-pi-5-mechanical-drawing.pdf)
- [Raspberry Pi Codec Zero product brief](https://datasheets.raspberrypi.com/audio/codec-zero-phat-product-brief.pdf)
- [Codec Zero GPIO allocation reference](https://pinout.xyz/pinout/codec_zero)
- SKIXG formal proposal, WBS, risk register, consultation slides, project scope, budget extract, and course purchasing instructions in the reviewed capstone package
