# HierarchicalPcb

This provides a true hierarchical PCB layout engine in KiCad, mirroring its hierarchical schematic capabilities.

Instead of laying out everything in your final file, you can define a sub-PCB next to your sub-schematic file, and HierarchicalPCB will automatically force the sub-PCB to be laid out exactly like that in the final PCB. There's no depth limitation to the nesting.

## How To Use

### Notes

Note that HierarchicalPCB will explore the entire tree and, along each path, enforce only the topmost sub-PCB level. For example, if sheet `T` contains `A` and `B`, and `B` contains `A` as a sub-sheet (and sub-sheets `A` and `B` both have associated sub-PCBs), then HierarchicalPCB will enforce the layout of `B` on components inside `B`, even if the components included from `A` by `B` have a different layout from `A`.

This is an important design decision as it allows you to include variant layouts. If you wish to enforce the layout of `A` everywhere, you need to open the sub-PCB of `B` and run HierarchicalPCB on it.
