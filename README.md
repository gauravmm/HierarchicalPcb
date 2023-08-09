# HierarchicalPcb

This provides a true hierarchical PCB layout engine in KiCad, mirroring its hierarchical schematic capabilities.

Instead of laying out everything in your final file, you can define a sub-PCB next to your sub-schematic file, and HierarchicalPCB will automatically force the sub-PCB to be laid out exactly like that in the final PCB. There's no depth limitation to the nesting.

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
   b. Recreate all traces.

The _copied properties_ are:

- Layer assignment (i.e. is it "flipped")

### Notes

Note that HierarchicalPCB will explore the entire tree and, along each path, enforce only the topmost sub-PCB level. For example, if sheet `T` contains `A` and `B`, and `B` contains `A` as a sub-sheet (and sub-sheets `A` and `B` both have associated sub-PCBs), then HierarchicalPCB will enforce the layout of `B` on components inside `B`, even if the components included from `A` by `B` have a different layout from `A`.

This is an important design decision as it allows you to include variant layouts. If you wish to enforce the layout of `A` everywhere, you need to open the sub-PCB of `B` and run HierarchicalPCB on it.
