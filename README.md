# HierarchicalPcb

This provides a true hierarchical PCB layout engine in KiCad, mirroring its hierarchical schematic capabilities.

Instead of laying out everything in your final file, you can define a sub-PCB next to your sub-schematic file, and HierarchicalPCB will automatically force the sub-PCB to be laid out exactly like that in the final PCB. There's no depth limitation to the nesting -- in fact, we encourage organizing your PCB layouts for maximum reusability.

This is inspired by the venerable [`ReplicateLayout`](https://github.com/MitjaNemec/ReplicateLayout) plugin, and is intended to be a more modular, powerful, and flexible replacement.

## How To Use

In summary:

1. Organize your schematic into hierarchical sheets, as you would normally do.
2. Create a `.kicad_pcb` file next to a hierarchical sheet and set up the placement of the sub-PCB there.
   a. You should create a project file to help with the placement.
   b. Any footprints missing from the sub-PCB (but present in the schematic) will be ignored during automatic placement.
   c. Any footprints present in the sub-PCB but missing from the main PCB will be reported as errors.
   d. Any footprints placed off to the left or above the origin will be ignored during automatic placement.
3. Open the main PCB and run the plugin.
4. Select which hierarchical sheets you want to enforce the layout of, and configure which footprint to use as the anchor for each sub-PCB.
5. Click OK and watch the magic happen.

If you wish to see a project that uses this, check out [AngloDox, my keyboard project](https://github.com/gauravmm/AngloDox/).

### Details of the placement algorithm

The algorithm works as follows:

1. For each selected hierarchical sheet, find the sub-PCB file and load it.
2. Match the anchor footprint in the sub-PCB to the anchor footprint in the main PCB.
   a. Copy the _copied properties_ of the anchor footprint from the sub-PCB to the main PCB:
   b. Move the anchor footprint in the main PCB into an automatically-named group (or create it if it doesn't exist).
3. For each footprint in the sub-PCB, find the corresponding footprint in the main PCB.
   a. Match the footprint by internal ID, not the reference designator.
   b. Copy the _copied properties_.
   c. Place and rotate the main footprint w.r.t. the main anchor so that it matches the sub-PCB.
4. For all traces in the sub-PCB:
   a. Clear the traces in the main PCB in the same group as the anchor.
   b. Recreate all traces, arcs, and vias.

### Notes

1. Each footprint may only be positioned following one sub-PCB. If you have a sub-PCB with its own sub-sub-PCBs, you can only enforce the layout of one of them. This is enforced during the selection process.
2. If you want multiple variations of the same schematic, you can nest them (i.e. LayoutVariant includes LayoutCommon and nothing else, each has a different sub-PCB, and you can enforce the layout of either one).
3. Currently, it does not support Zones, but I'll happily add that if someone needs it. Open an issue if you're interested and have some time to help me test it.
